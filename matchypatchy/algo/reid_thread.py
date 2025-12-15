"""
Thread Class for Processing Viewpoint and Miew Embedding

"""
import animl
from numpy import argmax
from pathlib import Path
import pandas as pd

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.algo import models
from matchypatchy import config
from matchypatchy.database.media import fetch_roi

#from matchypatchy.pairx.core import explain
#from matchypatchy.pairx import xai_dataset


class ReIDThread(QThread):
    prompt_update = pyqtSignal(str)  # Signal to update the alert prompt
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    done = pyqtSignal()

    def __init__(self, mpDB, REID_KEY, VIEWPOINT_KEY):
        super().__init__()
        self.mpDB = mpDB
        self.ml_dir = Path(config.load('ML_DIR'))
        self.reid_filepath = models.get_path(self.ml_dir, REID_KEY)
        self.viewpoint_filepath = models.get_path(self.ml_dir, VIEWPOINT_KEY)

    def run(self):
        """Process viewpoint and embeddings for ROIs"""
        # ROIS must be fetched after start() to chain with animl
        self.rois = fetch_roi(self.mpDB)

        if self.rois.empty:
            self.prompt_update.emit("No ROIs found, please run detection first...")
            self.done.emit()
            return

        media, _ = self.mpDB.select_join("roi", "media", "roi.media_id = media.id",
                                         columns="roi.id, media_id, filepath, external_id, camera_id, sequence_id")
        self.media = pd.DataFrame(media, columns=["roi_id", "media_id", "filepath", "external_id", "camera_id", "sequence_id"])
        self.image_paths = pd.Series(self.media["filepath"].values, index=self.media["roi_id"]).to_dict()
        self.rois['filepath'] = self.rois['roi_id'].map(self.image_paths)

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
        """Process viewpoint for ROIs"""
        # if no viewpoint model selected, skip
        if self.viewpoint_filepath is None:
            return

        # filter rois without viewpoint
        filtered_rois = self.rois[self.rois['viewpoint'].isna()]
        if len(filtered_rois) > 0:
            filtered_rois.reset_index(drop=True, inplace=True)

            model = animl.load_classifier(self.viewpoint_filepath)
            dataloader = animl.manifest_dataloader(filtered_rois, crop=True)

            for i, batch in enumerate(dataloader):
                if not self.isInterruptionRequested():
                    image = batch[0]
                    output = model.run(None, {model.get_inputs()[0].name: image})[0]
                    value = argmax(animl.softmax(output), axis=1)[0]

                    # TODO: Utilize probability for captures/sequences
                    # sequence = self.media[self.media['sequence_id'] == self.rois.loc[roi_id, "sequence_id"]]
                    roi_id = filtered_rois.at[i, 'roi_id']
                    self.mpDB.edit_row("roi", roi_id, {"viewpoint": int(value)})
                    self.progress_update.emit(round(100 * i / len(filtered_rois)))

    def get_embeddings(self):
        """Process embeddings for ROIs"""
        # If no reid model selected, skip
        if self.reid_filepath is None:
            self.prompt_update.emit("No Re-ID model selected, skipping embedding extraction...")
            return

        # filter rois without embeddings
        filtered_rois = self.rois[self.rois['emb'] == 0]
        if len(filtered_rois) > 0:
            filtered_rois.reset_index(drop=True, inplace=True)
            model = animl.load_miew(self.reid_filepath)

            for i in range(len(filtered_rois)):
                if not self.isInterruptionRequested():
                    row = filtered_rois.iloc[i].to_frame().T
                    if row.at[i, 'bbox_x'] == -1:
                        continue
                    roi_id = row.at[i, 'roi_id']
                    emb = animl.extract_miew_embeddings(model, row)[0]

                    self.mpDB.add_emb(roi_id, emb)
                    self.mpDB.edit_row("roi", roi_id, {"emb": 1}, quiet=False)

                    self.progress_update.emit(round(100 * i / len(filtered_rois)))


# TODO: REMOVE TORCHVISION DEPENDENCY
"""
class PairXThread(QThread):
    explained_img = pyqtSignal(list)  # Signal to update the alert prompt
    done = pyqtSignal()

    def __init__(self, query, match, model):
        super().__init__()
        self.query = query
        self.match = match
        self.model = model
        self.img_transforms = transforms.Compose([transforms.Resize((440, 440)),
                                                  transforms.ToTensor(),
                                                  transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                                                       std=[0.229, 0.224, 0.225])])

    def run(self):
        explained_imgs = self.explain()
        self.explained_img.emit(explained_imgs[0])
        self.done.emit()

    def explain(self):
        device = animl.get_device()

        img_0, img_1, img_np_0, img_np_1 = xai_dataset.get_img_pair_from_paths(device, self.query, self.match,
                                                                               (440,440), self.img_transforms)
        explained_imgs = explain(device, img_0, img_1, 
                                 img_np_0, img_np_1,
                                 self.model, ["backbone.blocks.3"],
                                 k_lines=20, k_colors=10)
        return explained_imgs
    
    def get_bbox(self, roi):
        '''
        Return the bbox coordinates for a given roi row
        '''
        return roi[['bbox_x', 'bbox_y', 'bbox_w', 'bbox_h']]
"""