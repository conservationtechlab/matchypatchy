"""
Thread Class for Processing Viewpoint and Miew Embedding

"""
import os
import pandas as pd

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.database.roi import (fetch_roi)
from animl import matchypatchy as animl_mp


class MiewThread(QThread):
    progress_update = pyqtSignal(str)  # Signal to update the progress bar

    def __init__(self, mpDB):
        super().__init__()
        self.mpDB = mpDB
        media, _ = self.mpDB.select_join("roi","media", "roi.media_id = media.id", columns="roi.id, media_id, filepath, capture_id, sequence_id")
        self.media = pd.DataFrame(media, columns=["id", "media_id", "filepath", "capture_id", "sequence_id"])
        self.image_paths = pd.Series(self.media["filepath"].values,index=self.media["id"]).to_dict() 
        self.rois = fetch_roi(self.mpDB)

        self.viewpoint_filepath = os.path.join(os.getcwd(), "viewpoint_jaguar.pt")
        self.miew_filepath = os.path.join(os.getcwd(), "miewid.bin")
    
    def run(self):
        self.progress_update.emit("Calculating viewpoint...")
        self.get_viewpoint()
        self.progress_update.emit("Calculating embeddings...")
        self.get_embeddings()
        self.progress_update.emit("Processing complete!")

    def get_viewpoint(self):
        # TODO: Utilize probability for captures/sequences

        filtered_rois = self.rois[self.rois['viewpoint'] == None]

        viewpoints = animl_mp.viewpoint_estimator(filtered_rois, self.image_paths, self.viewpoint_filepath)
        viewpoints = viewpoints.set_index("id")
        
        for roi_id, v in viewpoints.iterrows():
            sequence = self.media[self.media['sequence_id'] == self.rois.loc[roi_id, "sequence_id"]]
            print(sequence)

            self.mpDB.edit_row("roi", roi_id, {"viewpoint":v['value']})


        # Match Button
    def get_embeddings(self):

        filtered_rois = self.rois[self.rois['emb_id'] == 0]

        embs = animl_mp.miew_embedding(filtered_rois, self.image_paths, self.miew_filepath)
        for e in embs:
            roi_id = e[0]
            emb = e[1]
            emb_id = self.mpDB.add_emb(emb)
            self.mpDB.edit_row("roi", roi_id, {"emb_id":emb_id})