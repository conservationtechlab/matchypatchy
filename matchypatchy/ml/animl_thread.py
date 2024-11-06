"""
Thread Class for Processing BBox and Species Classification

"""
from pathlib import Path
import pandas as pd


from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QProgressBar,
                             QComboBox, QDialogButtonBox, QLabel)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


from matchypatchy.ml import models
from matchypatchy import config
from matchypatchy.database.roi import fetch_roi

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

        self.detector_list = [models.MODELS[m][0] for m in models.DETECTORS]
        self.detector.addItems(self.detector_list)

        # Classifier
        self.classifier_label = QLabel("Select Classifier Model:")
        self.classifier = QComboBox()
        layout.addWidget(self.classifier_label)
        layout.addWidget(self.classifier)

        self.classifier_list = [models.MODELS[m][0] for m in models.CLASSIFIERS]
        self.classifier.addItems(self.classifier_list)

        # Ok/Cancel
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.buttonBox, alignment=Qt.AlignmentFlag.AlignCenter)
        self.buttonBox.accepted.connect(self.accept)  
        self.buttonBox.rejected.connect(self.reject)

        self.setLayout(layout)


    def select_detector(self):
        self.selected_detector = models.DETECTORS[self.detector.currentIndex()]
        return self.selected_detector

    def select_classifier(self):
        self.selected_classifier = models.CLASSIFIERS[self.classifier.currentIndex()]
        return self.selected_classifier


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
                # all media have been processed
        if not self.media.empty:
            self.progress_update.emit("Extracting frames from videos...")
            self.get_frames()
            self.progress_update.emit("Calculating bounding box...")
            self.get_bbox()
        self.progress_update.emit("Predicting species...")
        self.get_species()

    def get_frames(self):
        self.media = animl_mp.process_videos(self.media, config.FRAME_DIR)
        print(self.media)

    def get_bbox(self):
        # 1 RUN MED
        detections = animl_mp.detect(self.md_filepath, self.media)
        
        for i, roi in detections.iterrows():
            print(i,roi)

            media_id = roi['id']

            # 2. ADD ROI
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
        self.rois = fetch_roi(self.mpDB)


