"""
QThread Class for Processing BBox, Frames, BuildFileManifest with ANIML

"""
import animl
import pandas as pd
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.database.thumbnails import save_roi_thumbnail
from matchypatchy.database.media import fetch_roi_media
from matchypatchy.algo import models
from matchypatchy import config



MEGADETECTORv1000_SIZE = 960


class BuildManifestThread(QThread):
    """
    Thread for launching buildfilemanifest
    """
    manifest = pyqtSignal(pd.DataFrame)

    def __init__(self, directory):
        super().__init__()
        self.directory = directory

    def run(self):
        self.data = animl.build_file_manifest(self.directory)
        self.manifest.emit(self.data)


class AnimlThread(QThread):
    prompt_update = pyqtSignal(str)  # Signal to update the alert prompt
    progress_update = pyqtSignal(int)  # Signal to update the progress bar

    def __init__(self, mpDB, DETECTOR_KEY):
        super().__init__()
        self.mpDB = mpDB
        self.ml_dir = Path(config.load_cfg('ML_DIR'))
        self.n_frames = config.load_cfg('VIDEO_FRAMES')
        self.thumbnail_dir = config.load_cfg('THUMBNAIL_DIR')
        self.confidence_threshold = 0.1
        self.DETECTOR_KEY = DETECTOR_KEY
        self.md_filepath = models.get_path(self.ml_dir, DETECTOR_KEY)

        # select media that do not have rois
        media = self.mpDB._command("""SELECT * FROM media WHERE NOT EXISTS
                                 (SELECT 1 FROM roi WHERE roi.media_id = media.id);""")
        self.media = pd.DataFrame(media, columns=["id", "filepath", "ext", "timestamp", "station_id", "camera_id",
                                                  "sequence_id", "external_id", "comment"])
        # select rois that do not have bbox
        rois = fetch_roi_media(mpDB, reset_index=False)
        self.rois = rois[rois['bbox_x'] == -1]  # imported without bbox
        self.rois = self.rois.drop(columns=['bbox_x', 'bbox_y', 'bbox_w', 'bbox_h'])
        # count total to process for progress bar
        self.to_process = len(self.media) + len(self.rois)

    def run(self):
        if self.to_process > 0:
            self.prompt_update.emit("Extracting frames from videos...")
            self.get_frames()
            self.prompt_update.emit("Calculating bounding boxes...")
            self.get_bbox()

    def get_frames(self):
        """Extract frames from video media using ANIML"""
        self.media = animl.extract_frames(self.media, frames=self.n_frames)

    def get_bbox(self):
        """Get bounding boxes for media and rois without bbox using ANIML detector"""
        # SKIP if no detector selected
        if self.DETECTOR_KEY is None:
            self.prompt_update.emit("No detector selected, skipping detection...")
            return
        # load detector
        else:
            detector = animl.load_detector(self.md_filepath)

        # viewpoint, individual TBD
        viewpoint = None
        individual_id = None

        # 2 GET BOXES
        for i, image in self.media.iterrows():
            if not self.isInterruptionRequested():
                media_id = image['id']
                row = image.to_frame().T

                detections = animl.detect(detector,
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
                    roi_id = self.mpDB.add_roi(media_id, frame,
                                               bbox_x, bbox_y, bbox_w, bbox_h,
                                               viewpoint=viewpoint,
                                               individual_id=individual_id,
                                               emb=0)
                    # save thumbnails
                    roi_thumbnail = save_roi_thumbnail(self.thumbnail_dir,
                                                       image['filepath'], image['ext'], frame,
                                                       bbox_x, bbox_y, bbox_w, bbox_h)
                    self.mpDB.add_thumbnail("roi", roi_id, roi_thumbnail)
            self.progress_update.emit(round(100 * (i + 1) / self.to_process))

        # Process existing rois without bbox
        for i, image in self.rois.iterrows():
            if not self.isInterruptionRequested():
                media_id = image['media_id']
                row = image.to_frame().T

                detections = animl.detect(detector,
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
                    self.mpDB.edit_row('roi', image['id'], {
                        "bbox_x": bbox_x,
                        "bbox_y": bbox_y,
                        "bbox_w": bbox_w,
                        "bbox_h": bbox_h
                    })
            self.progress_update.emit(round(100 * (i + 1) / self.to_process))
