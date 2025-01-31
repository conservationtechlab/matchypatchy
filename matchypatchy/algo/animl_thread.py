"""
Thread Class for Processing BBox and Species Classification

"""
import pandas as pd

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.algo import models
from matchypatchy import config

from animl.file_management import build_file_manifest
from animl.api import matchypatchy as animl_mp


class BuildManifestThread(QThread):
    """
    Thread for launching buildfilemanifest
    """
    manifest = pyqtSignal(pd.DataFrame)

    def __init__(self, directory):
        super().__init__()
        self.directory = directory

    def run(self):
        self.data = build_file_manifest(self.directory)
        self.manifest.emit(self.data)


class AnimlThread(QThread):
    progress_update = pyqtSignal(str)  # Signal to update the progress bar

    def __init__(self, mpDB, detector_key, classifier_key):
        super().__init__()
        self.mpDB = mpDB

        # select media that do not have rois
        media = self.mpDB._command("""SELECT * FROM media WHERE NOT EXISTS
                                 (SELECT 1 FROM roi WHERE roi.media_id = media.id);""")

        self.media = pd.DataFrame(media, columns=["id", "filepath", "ext", "timestamp", "station",
                                                  "sequence_id", "external_id", "comment", "favorite"])
        self.image_paths = pd.Series(self.media["filepath"].values, index=self.media["id"]).to_dict()

        self.md_filepath = models.get_path(detector_key)
        self.classifier_filepath = models.get_path(classifier_key)
        self.class_filepath = models.get_class_path(classifier_key)
        self.config_filepath = models.get_config_path(classifier_key)

    def run(self):
        if not self.media.empty:
            self.progress_update.emit("Extracting frames from videos...")
            self.get_frames()
            self.progress_update.emit("Calculating bounding box...")
            self.get_bbox()
        self.progress_update.emit("Predicting species...")
        self.get_species()

    def get_frames(self):
        self.media = animl_mp.process_videos(self.media, config.load('FRAME_DIR'))

    def get_bbox(self):
        # 1 RUN MED
        detections = animl_mp.detect_mp(self.md_filepath, self.media)
        # 2 GET BOXES
        for _, roi in detections.iterrows():
            media_id = roi['id']

            frame = roi['FrameNumber'] if 'FrameNumber' in roi.index else 1

            bbox_x = roi['bbox1']
            bbox_y = roi['bbox2']
            bbox_w = roi['bbox3']
            bbox_h = roi['bbox4']

            # species, viewpoint, individual TBD
            species_id = None
            viewpoint = None
            individual_id = None

            # do not add emb_id, to be determined later
            self.mpDB.add_roi(media_id, frame, bbox_x, bbox_y, bbox_w, bbox_h,
                              species_id, viewpoint=viewpoint, reviewed=0,
                              individual_id=individual_id, emb_id=0)

    def get_species(self, label_col="Code"):
        if self.classifier_filepath is None:
            # user opted to skip classification
            return

        classes = pd.read_csv(self.class_filepath).set_index(label_col)

        info = "roi.id, media_id, filepath, frame, species_id, bbox_x, bbox_y, bbox_w, bbox_h"
        rois, columns = self.mpDB.select_join("roi", "media", 'roi.media_id = media.id', columns=info)
        rois = pd.DataFrame(rois, columns=columns)

        filtered_rois = rois[rois["species_id"].isna()]

        # if there are unlabeled rois
        if not filtered_rois.empty:
            filtered_rois = animl_mp.classify_mp(filtered_rois, self.config_filepath)
            for i, row in filtered_rois.iterrows():
                prediction = row['prediction']
                # get species_id for prediction
                try:
                    species_id = self.mpDB.select("species", columns='id', row_cond=f'common="{prediction}"')[0][0]
                except IndexError:
                    binomen = classes.loc[prediction, 'species']   # FIXME: Hardcoded column name
                    species_id = self.mpDB.add_species(binomen, prediction)
                # update species_id
                self.mpDB.edit_row('roi', row['id'], {"species_id": species_id})
