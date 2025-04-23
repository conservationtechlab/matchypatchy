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

    def __init__(self, mpDB, detector_key, classifier_key):
        super().__init__()
        self.mpDB = mpDB
        self.ml_dir = Path(config.load('ML_DIR'))
        self.confidence_threshold = 0.1

        # select media that do not have rois
        media = self.mpDB._command("""SELECT * FROM media WHERE NOT EXISTS
                                 (SELECT 1 FROM roi WHERE roi.media_id = media.id);""")

        self.media = pd.DataFrame(media, columns=["id", "filepath", "ext", "timestamp", "station",
                                                  "sequence_id", "external_id", "comment", "favorite"])
        self.image_paths = pd.Series(self.media["filepath"].values, index=self.media["id"]).to_dict()

        self.md_filepath = models.get_path(self.ml_dir, detector_key)
        self.classifier_filepath = models.get_path(self.ml_dir, classifier_key)
        self.class_filepath = models.get_class_path(self.ml_dir, classifier_key)
        self.config_filepath = models.get_config_path(self.ml_dir, classifier_key)

    def run(self):
        if not self.media.empty:
            self.prompt_update.emit("Extracting frames from videos...")
            self.get_frames()
            self.prompt_update.emit("Calculating bounding boxes...")
            self.get_bbox()
        #self.progress_update.emit("Predicting species...")
        #self.get_species()

    def get_frames(self):
        self.media = animl.extract_frames(self.media, config.load('FRAME_DIR'), 
                                          frames=int(config.load('VIDEO_FRAMES')), file_col="filepath")

    def get_bbox(self):
        # 1 RUN MED
        detector = animl.MegaDetector(self.md_filepath)

        viewpoint = None
        individual_id = None
        species_id = None


        # 2 GET BOXES
        for i, image in self.media.iterrows():
            if not self.isInterruptionRequested():
                media_id = image['id']

                detections = animl.process_image(image['filepath'], detector, self.confidence_threshold)
                detections = animl.parse_MD([detections], manifest=image)
                detections = animl.get_animals(detections)

                for _, roi in detections.iterrows():
                    frame = roi['FrameNumber'] if 'FrameNumber' in roi.index else 1

                    bbox_x = roi['bbox1']
                    bbox_y = roi['bbox2']
                    bbox_w = roi['bbox3']
                    bbox_h = roi['bbox4']

                    # viewpoint, individual TBD

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
            

