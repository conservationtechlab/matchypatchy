"""
Thread Class for Processing BBox and Species Classification

"""
from pathlib import Path
import pandas as pd

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.algo import models
from matchypatchy import config

import animl


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

    def __init__(self, mpDB, DETECTOR_KEY): #, classifier_key):
        super().__init__()
        self.mpDB = mpDB
        self.ml_dir = Path(config.load('ML_DIR'))
        self.n_frames = config.load('VIDEO_FRAMES')
        self.confidence_threshold = 0.1
        self.DETECTOR_KEY = DETECTOR_KEY

        # select media that do not have rois
        media = self.mpDB._command("""SELECT * FROM media WHERE NOT EXISTS
                                 (SELECT 1 FROM roi WHERE roi.media_id = media.id);""")

        self.media = pd.DataFrame(media, columns=["id", "filepath", "ext", "timestamp", "station_id", "camera_id",
                                                  "sequence_id", "external_id", "comment", "favorite"])
        self.image_paths = pd.Series(self.media["filepath"].values, index=self.media["id"]).to_dict()

        self.md_filepath = models.get_path(self.ml_dir, DETECTOR_KEY)
        #self.classifier_filepath = models.get_path(self.ml_dir, classifier_key)
        #self.class_filepath = models.get_class_path(self.ml_dir, classifier_key)
        #self.config_filepath = models.get_config_path(self.ml_dir, classifier_key)

    def run(self):
        if not self.media.empty:
            self.prompt_update.emit("Extracting frames from videos...")
            self.get_frames()
            self.prompt_update.emit("Calculating bounding boxes...")
            self.get_bbox()
        #self.progress_update.emit("Predicting species...")
        #self.get_species()

    def get_frames(self):
        self.media = animl.extract_frames2(self.media, frames=self.n_frames)

    def get_bbox(self):
        # SKIP if no detector selected
        if self.DETECTOR_KEY is None:
            print("No detector selected, skipping detection...")
            self.prompt_update.emit("No detector selected, skipping detection...")
            return
        # load detector
        elif self.DETECTOR_KEY == "MegaDetector v5a" or self.DETECTOR_KEY == "MegaDetector v5b":
            detector = animl.load_detector(self.md_filepath, "MDV5")

        # viewpoint, individual TBD
        viewpoint = None
        individual_id = None
        species_id = None

        # 2 GET BOXES
        for i, image in self.media.iterrows():
            if not self.isInterruptionRequested():
                media_id = image['id']
                row = image.to_frame().T


                detections = animl.detect(detector, row, animl.MEGADETECTORv5_SIZE, animl.MEGADETECTORv5_SIZE,
                                           confidence_threshold=self.confidence_threshold)

                detections = animl.parse_detections(detections, manifest=row)
                detections = animl.get_animals(detections)

                for _, roi in detections.iterrows():
                    frame = roi['framenumber'] if 'framenumber' in roi.index else 0

                    bbox_x = roi['bbox_x']
                    bbox_y = roi['bbox_y']
                    bbox_w = roi['bbox_w']
                    bbox_h = roi['bbox_h']

                    # do not add emb_id, to be determined later
                    self.mpDB.add_roi(media_id, frame, bbox_x, bbox_y, bbox_w, bbox_h,
                                      viewpoint=viewpoint, reviewed=0, species_id=species_id,
                                      individual_id=individual_id, emb=0)
                    
            self.progress_update.emit(round(100 * (i + 1) / len(self.media)))


    def get_species(self, label_col="code", binomen_col='species'):
        if self.classifier_filepath is None:
            # user opted to skip classification
            return

        classes = pd.read_csv(self.class_filepath).set_index(label_col)
        self.add_species_list(classes, binomen_col)

        info = "roi.id, media_id, filepath, frame, species_id, bbox_x, bbox_y, bbox_w, bbox_h"
        rois, columns = self.mpDB.select_join("roi", "media", 'roi.media_id = media.id', columns=info)
        rois = pd.DataFrame(rois, columns=columns)

        filtered_rois = rois[rois["species_id"].isna()]

        # if there are unlabeled rois
        if not filtered_rois.empty:
            filtered_rois = animl.classify_mp(filtered_rois, self.config_filepath)
            for i, row in filtered_rois.iterrows():
                if not self.isInterruptionRequested():
                    prediction = row['prediction']
                    # get species_id for prediction
                    try:
                        species_id = self.mpDB.select("species", columns='id', row_cond=f'common="{prediction}"')[0][0]
                    except IndexError:
                        binomen = classes.loc[prediction, binomen_col]
                        species_id = self.mpDB.add_species(binomen, prediction)
                    # update species_id
                    self.mpDB.edit_row('roi', row['id'], {"species_id": species_id})

    def add_species_list(self, classes, binomen_col):
        for common, cl in classes.iterrows():
            binomen = cl[common, binomen_col]
            species_id = self.mpDB.add_species(binomen, common)
            

