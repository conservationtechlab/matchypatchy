"""
QThread Class for Processing BBox, Frames, BuildFileManifest with ANIML

"""
import animl
import pandas as pd
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.database.thumbnails import save_roi_thumbnail
from matchypatchy.database.media import fetch_roi_media
from matchypatchy.threads.model_download_thread import get_path
from matchypatchy import config


MEGADETECTORv1000_SIZE = 960


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


class AnimlThread(QThread):
    prompt_update = pyqtSignal(str)  # Signal to update the alert prompt
    progress_update = pyqtSignal(int)  # Signal to update the progress bar

    def __init__(self, mpDB, DETECTOR_KEY):
        super().__init__()
        self.mpDB = mpDB
        self.ml_dir = Path(config.load_cfg('ML_DIR'))
        self.smart_frames = config.load_cfg('SMART_FRAMES')
        self.fps = config.load_cfg('VIDEO_FPS')
        self.n_frames = config.load_cfg('N_FRAMES')
        self.thumbnail_dir = config.load_cfg('THUMBNAIL_DIR')
        self.confidence_threshold = 0.1
        self.DETECTOR_KEY = DETECTOR_KEY
        self.md_filepath = get_path(self.ml_dir, DETECTOR_KEY)

        # select media that do not have rois
        media = self.mpDB._command("""SELECT * FROM media WHERE NOT EXISTS
                                 (SELECT 1 FROM roi WHERE roi.media_id = media.id);""")
        self.media = pd.DataFrame(media, columns=["id", "filepath", "sha256", "ext", "timestamp", "station_id", "camera_id",
                                                  "sequence_id", "external_id", "comment"])
        # select rois that do not have bbox
        rois = fetch_roi_media(mpDB, reset_index=False)
        self.rois = rois[rois['bbox_x'] == -1]  # imported without bbox
        self.rois = self.rois.drop(columns=['bbox_x', 'bbox_y', 'bbox_w', 'bbox_h'])

        self.images = None
        self.video = None
        self.to_process = 0
        self.progress_count = 0

        if self.DETECTOR_KEY is None:
            self.detector = None
        else:
            self.detector = animl.load_detector(self.md_filepath)

    def run(self):
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
            self.prompt_update.emit("Detecting images...")
            self.detect_images()
            self.prompt_update.emit("Selecting best video frames...")
            self.detect_videos()

    def detect_images(self):
        """Extract bboxes for images using ANIML"""

        # SKIP if no detector selected
        if self.detector is None:
            self.prompt_update.emit("No detector selected, skipping detection...")
            return

        # detect new images
        for i, image in self.images.iterrows():
            if not self.isInterruptionRequested():
                media_id = image['id']
                row = image.to_frame().T

                detections = animl.detect(self.detector,
                                          row,
                                          MEGADETECTORv1000_SIZE,
                                          MEGADETECTORv1000_SIZE,
                                          confidence_threshold=self.confidence_threshold)

                detections = animl.parse_detections(detections, manifest=row)
                detections = animl.get_animals(detections)

                for _, roi in detections.iterrows():
                    frame = roi['frame'] if 'frame' in roi.index else 0

                    bbox_x = roi['bbox_x']
                    bbox_y = roi['bbox_y']
                    bbox_w = roi['bbox_w']
                    bbox_h = roi['bbox_h']

                    # do not add emb_id, to be determined later
                    roi_id = self.mpDB.add_roi(media_id,
                                               frame,
                                               bbox_x, bbox_y, bbox_w, bbox_h,
                                               viewpoint=None,
                                               individual_id=None,
                                               emb=0)
                    # save thumbnails
                    roi_thumbnail = save_roi_thumbnail(self.thumbnail_dir,
                                                       image['filepath'],
                                                       image['ext'],
                                                       frame,
                                                       bbox_x, bbox_y, bbox_w, bbox_h)
                    self.mpDB.add_thumbnail("roi", roi_id, roi_thumbnail)

            self.progress_count += 1
            self.progress_update.emit(round(100 * (self.progress_count / self.to_process)))

        # Process existing rois without bbox
        for i, image in self.rois.iterrows():
            if not self.isInterruptionRequested():
                media_id = image['media_id']
                row = image.to_frame().T

                detections = animl.detect(self.detector,
                                          row,
                                          MEGADETECTORv1000_SIZE,
                                          MEGADETECTORv1000_SIZE,
                                          confidence_threshold=self.confidence_threshold)

                detections = animl.parse_detections(detections, manifest=row)
                detections = animl.get_animals(detections)

                for _, roi in detections.iterrows():
                    frame = roi['frame'] if 'frame' in roi.index else 0

                    bbox_x = roi['bbox_x']
                    bbox_y = roi['bbox_y']
                    bbox_w = roi['bbox_w']
                    bbox_h = roi['bbox_h']

                    # do not add emb_id, to be determined later
                    self.mpDB.edit_row('roi',
                                       image['id'],
                                       {"bbox_x": bbox_x,
                                        "bbox_y": bbox_y,
                                        "bbox_w": bbox_w,
                                        "bbox_h": bbox_h
                                        })
            self.progress_count += 1
            self.progress_update.emit(round(100 * (self.progress_count / self.to_process)))

    def detect_videos(self):
        """Get bounding boxes for media and rois without bbox using ANIML detector"""

        # 2 GET BOXES
        for media_id, video in self.videos.groupby('id'):
            if not self.isInterruptionRequested():

                results = animl.detect(self.detector,
                                       video,
                                       MEGADETECTORv1000_SIZE,
                                       MEGADETECTORv1000_SIZE,
                                       confidence_threshold=self.confidence_threshold,
                                       calculate_clarity=True)
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
            self.progress_count += 1
            self.progress_update.emit(round(100 * (self.progress_count / self.to_process)))
