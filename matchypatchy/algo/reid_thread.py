"""
Thread Class for Processing Viewpoint and Miew Embedding

"""
from pathlib import Path
import pandas as pd
import torchvision.transforms as transforms

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.algo import models
from matchypatchy import config
from matchypatchy.database.media import fetch_roi

from matchypatchy.pairx.core import explain
from matchypatchy.pairx import xai_dataset

import animl


class ReIDThread(QThread):
    prompt_update = pyqtSignal(str)  # Signal to update the alert prompt
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    done = pyqtSignal()

    def __init__(self, mpDB, reid_key, viewpoint_key):
        super().__init__()
        self.mpDB = mpDB
        self.ml_dir = Path(config.load('ML_DIR'))
        self.reid_filepath = models.get_path(self.ml_dir, reid_key)
        self.viewpoint_filepath = models.get_path(self.ml_dir, viewpoint_key)

    def run(self):
        # must be fetched after start() to chain with animl
        self.rois = fetch_roi(self.mpDB)
        media, _ = self.mpDB.select_join("roi", "media", "roi.media_id = media.id", columns="roi.id, media_id, filepath, external_id, sequence_id")
        self.media = pd.DataFrame(media, columns=["roi_id", "media_id", "filepath", "external_id", "sequence_id"])
        self.image_paths = pd.Series(self.media["filepath"].values, index=self.media["roi_id"]).to_dict()

        if not self.isInterruptionRequested():
            self.prompt_update.emit("Calculating viewpoint...")
            self.get_viewpoint()
        if not self.isInterruptionRequested():
            self.prompt_update.emit("Calculating embeddings...")
            self.get_embeddings()
        if not self.isInterruptionRequested():
            self.prompt_update.emit("Processing complete!")
            self.done.emit()

    def get_viewpoint(self):
        # user did not select a viewpoint model
        if self.viewpoint_filepath is None:
            return

        filtered_rois = self.rois[self.rois['viewpoint'].isna()]
        if len(filtered_rois) > 0:

            model = animl.load_model(self.viewpoint_filepath, 2)
            dataloader = animl.matchypatchy.reid_dataloader(filtered_rois, self.image_paths)

            for i, img in enumerate(dataloader):
                if not self.isInterruptionRequested():
                    roi_id, value, prob = animl.viewpoint_estimator(model, img)
                    print(roi_id, value)

                    # TODO: Utilize probability for captures/sequences
                    # sequence = self.media[self.media['sequence_id'] == self.rois.loc[roi_id, "sequence_id"]]
                    self.mpDB.edit_row("roi", roi_id, {"viewpoint": int(value)})
                    self.progress_update.emit(round(100 * i/len(filtered_rois)))

    def get_embeddings(self):
        # Process only those that have not yet been processed
        filtered_rois = self.rois[self.rois['emb'] == 0]
        if len(filtered_rois) > 0:

            model = animl.load_miew(self.reid_filepath)
            dataloader = animl.matchypatchy.reid_dataloader(filtered_rois, self.image_paths)

            for i, img in enumerate(dataloader):
                if not self.isInterruptionRequested():
                    roi_id, emb = animl.miew_embedding(model, img)

                    self.mpDB.add_emb(roi_id, emb)

                    self.mpDB.edit_row("roi", roi_id, {"emb": 1})
                    self.progress_update.emit(round(100 * i/len(filtered_rois)))



# TODO: load model once?
class PairXThread(QThread):
    explained_img = pyqtSignal(list)  # Signal to update the alert prompt
    done = pyqtSignal()

    def __init__(self, query, match):
        super().__init__()
        self.query = query
        self.match = match
        self.img_transforms = transforms.Compose([transforms.Resize((440, 440)),
                                             transforms.ToTensor(),
                                             transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                                                  std=[0.229, 0.224, 0.225])])

    def run(self):
        self.load_model()
        print("explain")
        explained_imgs = self.explain()
        self.explained_img.emit(explained_imgs[0])
        self.done.emit()

    def load_model(self):
        self.reid_filepath = models.get_path(Path(config.load('ML_DIR')), config.load('reid_key'))
        if self.reid_filepath:
            self.model = animl.load_miew(self.reid_filepath)
        else:
            print(f"Warning, Re-ID model not found. Expected path: {self.reid_filepath}")
            # TODO: if model key exists but file dne, recommend user redownloads

    def explain(self):
        

        img_0, img_1, img_np_0, img_np_1 = xai_dataset.get_img_pair_from_paths(self.model.device, 
                                                                                     self.query, 
                                                                                     self.match, 
                                                                                     (440,440), self.img_transforms)
        explained_imgs = explain(self.model.device, img_0, img_1,  
                                                 img_np_0, img_np_1,
                                                 self.model,
                                                 ["backbone.blocks.3"],  
                                                 k_lines=20, k_colors=10)
        return explained_imgs
    
    def get_bbox(self, roi):
        """
        Return the bbox coordinates for a given roi row
        """
        return roi[['bbox_x', 'bbox_y', 'bbox_w', 'bbox_h']]