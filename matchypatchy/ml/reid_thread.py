"""
Thread Class for Processing Viewpoint and Miew Embedding

"""
import os
import pandas as pd

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QComboBox, QDialogButtonBox, QLabel)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from matchypatchy.ml import models
from matchypatchy import config
from matchypatchy.database.roi import (fetch_roi)

from animl import matchypatchy as animl_mp


class ReIDOptionsPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle('ReID Options')
        layout = QVBoxLayout()

        # Detector
        self.reid_label = QLabel("Select Re-Identification Model:")
        self.reid = QComboBox()
        layout.addWidget(self.reid_label)
        layout.addWidget(self.reid)

        self.available_reids = list(models.available_models(models.REIDS))
        self.reid_list = [models.MODELS[m][0] for m in self.available_reids]
        self.reid.addItems(self.reid_list)

        # Viewpoint
        self.viewpoint_label = QLabel("Select Viewpoint Model:")
        self.viewpoint = QComboBox()
        layout.addWidget(self.viewpoint_label)
        layout.addWidget(self.viewpoint)

        self.available_viewpoints = list(models.available_models(models.VIEWPOINTS))
        self.viewpoint_list = ['None'] + [models.MODELS[m][0] for m in self.available_viewpoints]
        self.viewpoint.addItems(self.viewpoint_list)

        # Ok/Cancel
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.buttonBox, alignment=Qt.AlignmentFlag.AlignCenter)
        self.buttonBox.accepted.connect(self.accept)  
        self.buttonBox.rejected.connect(self.reject)

        self.setLayout(layout)


    def select_reid(self): 
        self.selected_reid_key = self.available_reids[self.reid.currentIndex()]
        return self.selected_reid_key

    def select_viewpoint(self):
        if self.viewpoint.currentIndex() == 0:
            return None
        else:
            self.selected_viewpoint_key = self.available_viewpoints[self.viewpoint.currentIndex() - 1]
            return self.selected_viewpoint_key



class ReIDThread(QThread):
    progress_update = pyqtSignal(str)  # Signal to update the progress bar

    def __init__(self, mpDB, reid_key, viewpoint_key):
        super().__init__()
        self.mpDB = mpDB
        media, _ = self.mpDB.select_join("roi","media", "roi.media_id = media.id", columns="roi.id, media_id, filepath, capture_id, sequence_id")
        self.media = pd.DataFrame(media, columns=["id", "media_id", "filepath", "capture_id", "sequence_id"])
        self.image_paths = pd.Series(self.media["filepath"].values,index=self.media["id"]).to_dict() 
        self.rois = fetch_roi(self.mpDB)

        self.reid_filepath = models.get_path(reid_key)
        self.viewpoint_filepath = models.get_path(viewpoint_key)
        print(self.viewpoint_filepath)
    
    def run(self):
        self.progress_update.emit("Calculating viewpoint...")
        self.get_viewpoint()
        self.progress_update.emit("Calculating embeddings...")
        self.get_embeddings()
        self.progress_update.emit("Processing complete!")

    def get_viewpoint(self):
        # user did not select a viewpoint model
        if self.viewpoint_filepath is None:
            return

        filtered_rois = self.rois[self.rois['viewpoint'] == None]

        viewpoints = animl_mp.viewpoint_estimator(filtered_rois, self.image_paths, self.viewpoint_filepath)
        viewpoints = viewpoints.set_index("id")
        
        for roi_id, v in viewpoints.iterrows():
            # TODO: Utilize probability for captures/sequences
            sequence = self.media[self.media['sequence_id'] == self.rois.loc[roi_id, "sequence_id"]]
            print(sequence)

            self.mpDB.edit_row("roi", roi_id, {"viewpoint":v['value']})


        # Match Button
    def get_embeddings(self):

        filtered_rois = self.rois[self.rois['emb_id'] == 0]

        embs = animl_mp.miew_embedding(filtered_rois, self.image_paths, self.reid_filepath)

        for e in embs:
            roi_id = e[0]
            emb = e[1]
            emb_id = self.mpDB.add_emb(emb)
            self.mpDB.edit_row("roi", roi_id, {"emb_id":emb_id})