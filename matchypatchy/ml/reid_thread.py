"""
Thread Class for Processing Viewpoint and Miew Embedding

"""
import pandas as pd

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.ml import models
from matchypatchy.database.roi import fetch_roi

import animl.api.matchypatchy as animl_mp


class ReIDThread(QThread):
    progress_update = pyqtSignal(str)  # Signal to update the progress bar

    def __init__(self, mpDB, reid_key, viewpoint_key):
        super().__init__()
        self.mpDB = mpDB
        self.reid_filepath = models.get_path(reid_key)
        self.viewpoint_filepath = models.get_path(viewpoint_key)

    def run(self):
        # must be fetched after start() to chain with animl
        self.rois = fetch_roi(self.mpDB)
        media, _ = self.mpDB.select_join("roi", "media", "roi.media_id = media.id", columns="roi.id, media_id, filepath, external_id, sequence_id")
        self.media = pd.DataFrame(media, columns=["id", "media_id", "filepath", "external_id", "sequence_id"])
        self.image_paths = pd.Series(self.media["filepath"].values, index=self.media["id"]).to_dict()

        self.progress_update.emit("Calculating viewpoint...")
        self.get_viewpoint()
        self.progress_update.emit("Calculating embeddings...")
        self.get_embeddings()
        self.progress_update.emit("Processing complete!")

    def get_viewpoint(self):
        # user did not select a viewpoint model
        if self.viewpoint_filepath is None:
            return

        filtered_rois = self.rois[self.rois['viewpoint'].isna()]

        viewpoints = animl_mp.viewpoint_estimator(filtered_rois, self.image_paths, self.viewpoint_filepath)
        viewpoints = viewpoints.set_index("id")

        for roi_id, v in viewpoints.iterrows():
            # TODO: Utilize probability for captures/sequences
            # sequence = self.media[self.media['sequence_id'] == self.rois.loc[roi_id, "sequence_id"]]
            self.mpDB.edit_row("roi", roi_id, {"viewpoint": v['value']})

        # Match Button
    def get_embeddings(self):
        # Process only those that have not yet been processed
        filtered_rois = self.rois[self.rois['emb_id'] == 0]

        embs = animl_mp.miew_embedding(filtered_rois, self.image_paths, self.reid_filepath)
        for e in embs:
            roi_id = e[0]
            emb = e[1]
            emb_id = self.mpDB.add_emb(emb)
            self.mpDB.edit_row("roi", roi_id, {"emb_id": emb_id})
