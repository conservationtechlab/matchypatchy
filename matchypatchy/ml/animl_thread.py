"""
Thread Class for Processing BBox and Species Classification

"""
import os
import pandas as pd

from PyQt6.QtCore import QThread, pyqtSignal

from ..database.roi import (fetch_roi, match)

from animl.reid import viewpoint
from animl.reid import miewid

class AnimnlThread(QThread):
    progress_update = pyqtSignal(str)  # Signal to update the progress bar

    def __init__(self, mpDB):
        super().__init__()
        self.mpDB = mpDB
        media = self.mpDB.select("media", columns="id, filepath, pair_id, sequence_id")
        self.media = pd.DataFrame(media, columns=["id", "filepath", "pair_id", "sequence_id"])
        self.image_paths = pd.Series(self.media["filepath"].values,index=self.media["id"]).to_dict() 

        self.viewpoint_filepath = os.path.join(os.getcwd(), "viewpoint_jaguar.pt")
        self.miew_filepath = os.path.join(os.getcwd(), "miewid.bin")
        
    
    def run(self):
        self.progress_update.emit("Calculating bounding box...")
        self.get_bbox()
        self.progress_update.emit("Calculating viewpoint...")
        self.get_viewpoint()
        self.progress_update.emit("Calculating embeddings...")
        self.get_embeddings()
        self.progress_update.emit("Matching images...")
        match(self.mpDB)
        self.progress_update.emit("Processing complete!")

    def get_bbox(self):
        # TODO: add MD step, assumes no rois yet
        pass

    def get_viewpoint(self):
        # TODO: Utilize probability for pairs/sequences
        self.rois = fetch_roi(self.mpDB)
        viewpoints = viewpoint.matchypatchy(self.rois, self.image_paths, self.viewpoint_filepath)
    
        for v in viewpoints:
            roi_id = v[0]
            value = v[1]
            prob = v[2] 
            print(roi_id, value, prob)
            self.mpDB.edit_row("roi", roi_id, {"viewpoint":value})

        # Match Button
    def get_embeddings(self):
        # 1. fetch images
        self.rois = fetch_roi(self.mpDB)
        embs = miewid.matchypatchy(self.rois, self.image_paths, self.miew_filepath)
        for e in embs:
            roi_id = e[0]
            emb = e[1]
            emb_id = self.mpDB.add_emb(emb)
            self.mpDB.edit_row("roi", roi_id, {"emb_id":emb_id})