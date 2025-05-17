"""
Edit A Single Image

"""
import pairx
import pandas as pd
from pathlib import Path
import torch
import torchvision.transforms as transforms

from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QDialogButtonBox, QPushButton)
from PyQt6.QtCore import Qt

from animl import load_miew

from matchypatchy import config
from matchypatchy.algo import models

from matchypatchy.gui.widget_image import ImageWidget
import matchypatchy.database.media as db_roi
import pairx.core
import pairx.xai_dataset

class PairXPopup(QDialog):
    def __init__(self, parent, query, match):
        super().__init__(parent)
        self.setWindowTitle("Match Visualizer")
        self.setFixedSize(1000, 500)

        self.query = query
        self.match = match
        print(self.query)
        print(self.match)

        # Layout ---------------------------------------------------------------
        layout = QVBoxLayout()
        # Query Image
        self.image = ImageWidget()
        self.image.setStyleSheet("border: 1px solid black;")
        self.image.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.image.load(image_path=self.query["filepath"],
                        bbox=db_roi.get_bbox(self.query), crop=False)
        layout.addWidget(self.image, 1)


        # Bottom Buttons
        button_layout = QHBoxLayout()
        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        #self.load_model()
        #self.explain()


    def load_model(self):
        # TODO: add model to config
        self.reid_filepath = models.get_path(Path(config.load('ML_DIR')), Path(config.load('REID_MODEL')))
        # if model key exists but file dne, recommend user redownloads

        self.model = load_miew(self.reid_filepath)


    def explain(self):
        img_transforms = transforms.Compose([transforms.Resize((440, 440)),
                                             transforms.ToTensor(),
                                             transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                                                  std=[0.229, 0.224, 0.225])])

        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        img_0, img_1, img_np_0, img_np_1 = pairx.xai_dataset.get_img_pair_from_paths(device, 
                                                                                     self.roi_query.at[0,'filepath'], 
                                                                                     self.roi_match.at[0,'filepath'], 
                                                                                     (440,440), img_transforms)

        self.explained_imgs = pairx.core.explain(device,
                  img_0,                     # First image, transformed
                  img_1,                     # Second image, transformed      
                  img_np_0,                  # First image, pretransform
                  img_np_1,                  # Second image, pretransform
                  self.model,                # Model
                  ["backbone.blocks.3"],     # Layer keys for intermediate layers (read below about choosing this)
                  k_lines=20,                # Number of matches to visualize as lines
                  k_colors=10                # Number of matches to visualize in fine-grained color map
                  )

    def display_images(self):
        pass