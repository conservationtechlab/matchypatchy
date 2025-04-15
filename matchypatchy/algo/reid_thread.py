"""
Thread Class for Processing Viewpoint and Miew Embedding

"""
import pandas as pd

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.algo import models
from matchypatchy.database.media import fetch_roi

import animl


class ReIDThread(QThread):
    prompt_update = pyqtSignal(str)  # Signal to update the alert prompt
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    done = pyqtSignal()

    def __init__(self, mpDB, reid_key, viewpoint_key):
        super().__init__()
        self.mpDB = mpDB
        self.reid_filepath = models.get_path(reid_key)
        self.viewpoint_filepath = models.get_path(viewpoint_key)

    def run(self):
        # must be fetched after start() to chain with animl
        self.rois = fetch_roi(self.mpDB)
        media, _ = self.mpDB.select_join("roi", "media", "roi.media_id = media.id", columns="roi.id, media_id, filepath, external_id, sequence_id")
        self.media = pd.DataFrame(media, columns=["roi_id", "media_id", "filepath", "external_id", "sequence_id"])
        self.image_paths = pd.Series(self.media["filepath"].values, index=self.media["roi_id"]).to_dict()

        self.prompt_update.emit("Calculating viewpoint...")
        self.get_viewpoint()
        self.prompt_update.emit("Calculating embeddings...")
        self.get_embeddings()
        self.prompt_update.emit("Processing complete!")
        self.done.emit()

    def get_viewpoint(self):
        # user did not select a viewpoint model
        if self.viewpoint_filepath is None:
            return

        filtered_rois = self.rois[self.rois['viewpoint'].isna()]
        if len(filtered_rois) > 0:

            viewpoints = animl.viewpoint_estimator(filtered_rois, self.image_paths, self.viewpoint_filepath)
            viewpoints = viewpoints.set_index("id")

            for roi_id, v in viewpoints.iterrows():
                if not self.isInterruptionRequested():
                    # TODO: Utilize probability for captures/sequences
                    # sequence = self.media[self.media['sequence_id'] == self.rois.loc[roi_id, "sequence_id"]]
                    self.mpDB.edit_row("roi", roi_id, {"viewpoint": int(v['value'])})

    def get_embeddings(self):
        # Process only those that have not yet been processed
        filtered_rois = self.rois[self.rois['emb_id'] == 0]
        if len(filtered_rois) > 0:

            model = animl.load_miew(self.reid_filepath)
            dataloader = animl.matchypatchy.reid_dataloader(filtered_rois, self.image_paths)

            for i, img in enumerate(dataloader):
                if not self.isInterruptionRequested():
                    roi_id, emb = animl.miew_embedding(model, img)

                    emb_id = self.mpDB.add_emb(emb)
                    self.mpDB.edit_row("roi", roi_id, {"emb_id": emb_id})
                    self.progress_update.emit(round(100 * i/len(filtered_rois)))
