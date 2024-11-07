"""
Thread Class for Processing BBox and Species Classification

"""
import pandas as pd

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QComboBox, QDialogButtonBox, QLabel)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from matchypatchy.ml import models
from matchypatchy import config

from animl import matchypatchy as animl_mp

# TODO: HANDLE VIDEOS

class AnimlOptionsPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle('Animl Options')
        layout = QVBoxLayout()

        # Detector
        self.detector_label = QLabel("Select Detector Model:")
        self.detector = QComboBox()
        layout.addWidget(self.detector_label)
        layout.addWidget(self.detector)

        self.available_detectors = list(models.available_models(models.DETECTORS))
        self.detector_list = [models.MODELS[m][0] for m in self.available_detectors]
        self.detector.addItems(self.detector_list)

        # Classifier
        self.classifier_label = QLabel("Select Classifier Model:")
        self.classifier = QComboBox()
        layout.addWidget(self.classifier_label)
        layout.addWidget(self.classifier)

        self.available_classifiers = list(models.available_models(models.CLASSIFIERS))
        self.classifier_list = [models.MODELS[m][0] for m in self.available_classifiers]
        self.classifier.addItems(self.classifier_list)

        # Ok/Cancel
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.buttonBox, alignment=Qt.AlignmentFlag.AlignCenter)
        self.buttonBox.accepted.connect(self.accept)  
        self.buttonBox.rejected.connect(self.reject)

        self.setLayout(layout)


    def select_detector(self): 
        self.selected_detector_key = self.available_detectors[self.detector.currentIndex()]
        return self.selected_detector_key

    def select_classifier(self):
        self.selected_classifier_key = self.available_classifiers[self.classifier.currentIndex()]
        return self.selected_classifier_key


class AnimlThread(QThread):
    progress_update = pyqtSignal(str)  # Signal to update the progress bar

    def __init__(self, mpDB, detector_key, classifier_key):
        super().__init__()
        self.mpDB = mpDB

        # select media that do not have rois
        media = self.mpDB._fetch("""SELECT * FROM media WHERE NOT EXISTS 
                                 (SELECT 1 FROM roi WHERE roi.media_id = media.id);""")


        self.media = pd.DataFrame(media, columns=["id", "filepath", "ext", "timestamp", "site", 
                                                  "sequence_id", "capture_id", "comment", "favorite"])
        self.image_paths = pd.Series(self.media["filepath"].values,index=self.media["id"]).to_dict() 

        self.md_filepath = models.get_path(detector_key)
        self.classifier_filepath = models.get_path(classifier_key)
        self.classifier_classlist = models.get_class_path(classifier_key)
    
    def run(self):
        if not self.media.empty:
            self.progress_update.emit("Extracting frames from videos...")
            self.get_frames()
            self.progress_update.emit("Calculating bounding box...")
            self.get_bbox()
        self.progress_update.emit("Predicting species...")
        self.get_species()

    def get_frames(self):
        self.media = animl_mp.process_videos(self.media, config.FRAME_DIR)

    def get_bbox(self):
        # 1 RUN MED 
        print(self.md_filepath)
        detections = animl_mp.detect(self.md_filepath, self.media)
        # 2 GET BOXES
        for i, roi in detections.iterrows():
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
    
    def get_species(self):
        # TODO: Utilize probability for captures/sequences
        classes = pd.read_csv(self.classifier_classlist).set_index("Code")

        info = "roi.id, media_id, filepath, frame, species_id, bbox_x, bbox_y, bbox_w, bbox_h"
        rois, columns = self.mpDB.select_join("roi", "media", 'roi.media_id = media.id', columns=info)
        rois = pd.DataFrame(rois,columns=columns)

        filtered_rois = rois[rois["species_id"].isna()]
        
        # if there are unlabeled rois 
        if not filtered_rois.empty:
            filtered_rois = animl_mp.classify(filtered_rois, self.classifier_filepath, self.classifier_classlist)
            for i, row in filtered_rois.iterrows():
                prediction = row['prediction']
                # get species_id for prediction
                try:
                    species_id = self.mpDB.select("species", columns='id', row_cond=f'common="{prediction}"')[0][0]
                except IndexError:
                    binomen = classes.loc[prediction,'Species']  # FIXME: Hardcoded column name 
                    species_id = self.mpDB.add_species(binomen, prediction)
                # update species_id        
                self.mpDB.edit_row('roi', row['id'], {"species_id": species_id})


