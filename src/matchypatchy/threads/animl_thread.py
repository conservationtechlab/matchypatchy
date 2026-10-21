"""
QThread Class for Processing BBox, Frames, BuildFileManifest with ANIML

"""
import logging
from pathlib import Path
import animl
import pandas as pd

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.database.thumbnails import save_roi_thumbnail
from matchypatchy.database.media import fetch_roi_media, get_sha256
from matchypatchy.threads.model_download_thread import get_path


MEGADETECTORv1000_SIZE = 960

logger = logging.getLogger(__name__)


class BuildManifestThread(QThread):
    """
    Thread for launching buildfilemanifest
    """
    manifest = pyqtSignal(pd.DataFrame)

    def __init__(self, directory, timezone):
        super().__init__()
        self.directory = directory
        self.timezone = timezone

    def run(self):
        self.data = animl.build_file_manifest(self.directory, exif=True, data_timezone=self.timezone)
        self.manifest.emit(self.data)


class VerifyNewBaseDirsThread(QThread):
    """
    Thread for launching buildfilemanifest
    """
    not_in_db = pyqtSignal(list)
    not_in_new_directory = pyqtSignal(list)
    finished = pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.mpDB = parent.mpDB
        self.base_dirs = parent.base_dirs
        self.updates = parent.updates
        self.not_found_in_db = []
        self.not_found_in_new_directory = []

    def run(self):
        for update in self.updates:
            if not self.isInterruptionRequested():
                base_dir_id = update[0]
                directory = update[1]
                media = self.mpDB.select("media", columns="relative_path, sha256", row_cond=f"base_dir_id = {base_dir_id}")
                # Saving only swaps base_dir, so each file must sit at its relative path under the new directory
                expected = set()
                hash_not_found_in_new_directory = []
                for relative_path, sha256 in media:
                    filepath = Path(directory, relative_path)
                    expected.add(filepath)
                    if get_sha256(filepath) != sha256:
                        hash_not_found_in_new_directory.append(relative_path)
                self.not_found_in_new_directory.append(hash_not_found_in_new_directory)

                # Files in the new directory that no media of this upload would point to
                new_data = animl.build_file_manifest(directory, exif=False)
                hash_not_found_in_db = [f for f in new_data.get('filepath', []) if Path(f) not in expected]
                self.not_found_in_db.append(hash_not_found_in_db)

        # Emit signals if the thread was not interrupted
        if not self.isInterruptionRequested():
            self.not_in_db.emit(self.not_found_in_db)
            self.not_in_new_directory.emit(self.not_found_in_new_directory)
            self.finished.emit()


class AnimlThread(QThread):
    prompt_update = pyqtSignal(str)  # Signal to update the alert prompt
    progress_update = pyqtSignal(int)  # Signal to update the progress bar

    def __init__(self, mpDB, cfg, DETECTOR_KEY):
        super().__init__()
        self.mpDB = mpDB
        self.ml_dir = Path(cfg.ML_DIR)
        self.smart_frames = cfg.SMART_FRAMES
        self.fps = cfg.VIDEO_FPS
        self.n_frames = cfg.N_FRAMES
        self.thumbnail_dir = cfg.THUMBNAIL_DIR
        self.device = cfg.DEVICE
        self.batch_size = 1  # Set a default batch size for processing images
        self.confidence_threshold = 0.1
        self.DETECTOR_KEY = DETECTOR_KEY
        self.md_filepath = get_path(self.ml_dir, DETECTOR_KEY)

        # select media that haven't been through detection and have no rois
        media, column_names = self.mpDB.get_media_with_filepath(
            row_cond="m.detection_done = 0 AND NOT EXISTS (SELECT 1 FROM roi WHERE roi.media_id = m.id)")
        self.media = pd.DataFrame(media, columns=column_names)

        # select rois imported without a bbox whose media hasn't been through detection
        pending = {row[0] for row in self.mpDB.select("media", columns="id", row_cond="detection_done = 0") or []}
        rois = fetch_roi_media(mpDB, reset_index=False)
        self.rois = rois[(rois['bbox_x'] == -1) & rois['media_id'].isin(pending)]
        self.rois = self.rois.drop(columns=['bbox_x', 'bbox_y', 'bbox_w', 'bbox_h'])

        self.images = None
        self.video = None
        self.to_process = 0
        self.progress_count = 0
        self.failed = set()  # files that couldn't be read
        self.detector = None  # loaded in run(), off the GUI thread

    def run(self):
        if self.DETECTOR_KEY is not None:
            self.prompt_update.emit("Loading detector...")
            self.detector = animl.load_detector(self.md_filepath, device=self.device)
        # imported ROIs without a box stay as they are when there's no detector to find one
        if self.detector is None:
            self.rois = self.rois.iloc[0:0]
        # pull out images and videos from media
        self.prompt_update.emit("Extracting frames...")
        self.images = animl.get_images(self.media)
        self.videos = animl.get_videos(self.media)
        # total to process for progress bar
        self.to_process = len(self.images) + len(self.rois) + len(self.videos)
        # extract frames from videos at specified fps
        if self.smart_frames:
            self.videos = animl.extract_frames(self.videos, fps=self.fps)
        # smart frames is off, extract n_frames from each video
        else:
            # extract at least 1 frame
            if self.n_frames < 1:
                self.n_frames = 1
            self.videos = animl.extract_frames(self.videos, frames=self.n_frames)

        if self.to_process > 0:
            self.prompt_update.emit("Detecting animals...")
            self.detect_images()
            self.prompt_update.emit("Selecting best video frames...")
            self.detect_videos()

    def detect_images(self):
        """Extract bboxes for images using ANIML"""

        # detect new images
        for batch_start in range(0, len(self.images), self.batch_size):
            if self.isInterruptionRequested():
                break

            batch_end = min(batch_start + self.batch_size, len(self.images))
            image_batch = self.images.iloc[batch_start:batch_end]

            # if no detector is selected, use the full image as the ROI
            if self.detector is None:
                detections = pd.DataFrame([{
                    'id': img['id'],
                    'frame': 0,
                    'bbox_x': 0,
                    'bbox_y': 0,
                    'bbox_w': 1,
                    'bbox_h': 1,
                    'filepath': img['filepath'],
                    'ext': img['ext']
                } for _, img in image_batch.iterrows()])

            # run detector
            else:
                detections = self._detect(image_batch, batch_size=self.batch_size)
                if detections is None:
                    self.progress_count += len(image_batch)
                    self.progress_update.emit(round(100 * (self.progress_count / self.to_process)))
                    continue
                detections = animl.parse_detections(detections, manifest=image_batch)
                detections = animl.get_animals(detections)

            for _, roi in detections.iterrows():
                frame = roi['frame'] if 'frame' in roi.index else 0

                bbox_x = roi['bbox_x']
                bbox_y = roi['bbox_y']
                bbox_w = roi['bbox_w']
                bbox_h = roi['bbox_h']

                # do not add emb_id, to be determined later
                roi_id = self.mpDB.add_roi(roi['id'],  #media id
                                           frame,
                                           bbox_x, bbox_y, bbox_w, bbox_h,
                                           viewpoint=None,
                                           individual_id=None,
                                           emb=0)
                # save thumbnails
                roi_thumbnail = save_roi_thumbnail(self.thumbnail_dir,
                                                   roi['filepath'],
                                                   roi['ext'],
                                                   frame,
                                                   bbox_x, bbox_y, bbox_w, bbox_h)
                self.mpDB.add_thumbnail("roi", roi_id, roi_thumbnail)

            self._mark_done(image_batch, 'id')
            self.progress_count += len(image_batch)
            self.progress_update.emit(round(100 * (self.progress_count / self.to_process)))

        # Process existing rois without bbox
        for batch_start in range(0, len(self.rois), self.batch_size):
            if self.isInterruptionRequested():
                break
                
            batch_end = min(batch_start + self.batch_size, len(self.rois))
            roi_batch = self.rois.iloc[batch_start:batch_end]

            detections = self._detect(roi_batch, batch_size=self.batch_size)
            if detections is None:
                self.progress_count += len(roi_batch)
                self.progress_update.emit(round(100 * (self.progress_count / self.to_process)))
                continue
            detections = animl.parse_detections(detections, manifest=roi_batch)
            detections = animl.get_animals(detections)
            # each ROI takes its most confident detection (writing them all left the last one)
            detections = detections.sort_values('conf', ascending=False).drop_duplicates('id')

            for _, roi in detections.iterrows():
                frame = roi['frame'] if 'frame' in roi.index else 0

                bbox_x = roi['bbox_x']
                bbox_y = roi['bbox_y']
                bbox_w = roi['bbox_w']
                bbox_h = roi['bbox_h']

                # do not add emb_id, to be determined later
                self.mpDB.edit_row('roi',
                                    roi['id'],
                                    {"bbox_x": bbox_x, "bbox_y": bbox_y,
                                     "bbox_w": bbox_w, "bbox_h": bbox_h})

            self._mark_done(roi_batch, 'media_id')
            self.progress_count += len(roi_batch)
            self.progress_update.emit(round(100 * (self.progress_count / self.to_process)))

    def detect_videos(self):
        """Get bounding boxes for media and rois without bbox using ANIML detector"""

        # 2 GET BOXES
        for media_id, video in self.videos.groupby('id'):
            if not self.isInterruptionRequested():

                # if no detector is selected, use the whole first frame as the ROI, as for images
                if self.detector is None:
                    top_frames = video.iloc[[0]].assign(bbox_x=0, bbox_y=0, bbox_w=1, bbox_h=1)
                else:
                    # one frame at a time: MegaDetector v1000 only returns detections
                    # for the first image of a batch
                    results = self._detect(video, batch_size=self.batch_size, calculate_clarity=True)
                    if results is None:
                        self.progress_count += 1
                        self.progress_update.emit(round(100 * (self.progress_count / self.to_process)))
                        continue
                    results = animl.parse_detections(results, manifest=video, score=True)
                    detections = animl.get_animals(results)

                    # get best frames based on score, if there are fewer than n_frames, take all
                    top_frames = detections.nlargest(self.n_frames, 'score')

                for _, roi in top_frames.iterrows():
                    frame = roi['frame'] if 'frame' in roi.index else 0
                    bbox_x = roi['bbox_x']
                    bbox_y = roi['bbox_y']
                    bbox_w = roi['bbox_w']
                    bbox_h = roi['bbox_h']

                    # do not add emb_id, to be determined later
                    roi_id = self.mpDB.add_roi(media_id, int(frame),
                                               bbox_x, bbox_y, bbox_w, bbox_h,
                                               viewpoint=None,
                                               individual_id=None,
                                               emb=0)
                    # save thumbnails
                    roi_thumbnail = save_roi_thumbnail(self.thumbnail_dir,
                                                       roi['filepath'], roi['ext'], frame,
                                                       bbox_x, bbox_y, bbox_w, bbox_h)
                    self.mpDB.add_thumbnail("roi", roi_id, roi_thumbnail)
                self._mark_done(video.iloc[[0]], 'id')
            self.progress_count += 1
            self.progress_update.emit(round(100 * (self.progress_count / self.to_process)))

    def _mark_done(self, manifest, media_column):
        """Mark the manifest's media as through detection, except files that couldn't be read"""
        read = manifest[~manifest['filepath'].isin(self.failed)]
        self.mpDB.mark_detection_done(read[media_column].unique())

    def _detect(self, manifest, **kwargs):
        """Run the detector on the manifest's files, None if none of them could be read"""
        results = animl.detect(self.detector,
                               manifest,
                               MEGADETECTORv1000_SIZE,
                               MEGADETECTORv1000_SIZE,
                               confidence_threshold=self.confidence_threshold,
                               use_progress_bar=False,
                               **kwargs)
        # animl.detect silently leaves out files it can't load
        read = {result['filepath'] for result in results}
        for filepath in set(manifest['filepath']) - read:
            logger.warning("Could not read %s, skipping it", filepath)
            self.failed.add(filepath)
        return results if results else None
