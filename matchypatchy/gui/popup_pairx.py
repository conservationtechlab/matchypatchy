"""
Edit A Single Image

"""
import numpy as np
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QDialogButtonBox, QProgressBar, QPushButton)
from PyQt6.QtCore import Qt

#from matchypatchy.algo.reid_thread import PairXThread
from matchypatchy.algo import models

from matchypatchy.gui.widget_media import ImageWidget
from matchypatchy.gui.popup_alert import AlertPopup

from matchypatchy import config

import animl

class PairXPopup(QDialog):
    def __init__(self, parent, query, match):
        super().__init__(parent)
        self.setWindowTitle("Match Visualizer")
        self.setMinimumSize(880, 900)
        self.parent = parent
        self.query = query
        self.match = match
        self.model = None

        # Layout ---------------------------------------------------------------
        layout = QVBoxLayout()
        # Query Image
        self.image = ImageWidget()
        self.image.setStyleSheet("border: 1px solid black;")
        self.image.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.image, 1)

        # Bottom Buttons
        button_layout = QHBoxLayout()

        self.button_last = QPushButton("<")
        self.button_last.pressed.connect(self.last_layer)
        self.button_next = QPushButton(">")
        self.button_next.pressed.connect(self.next_layer)

        #button_layout.addWidget(self.button_last)
        #button_layout.addWidget(self.button_next)

        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)

        # Progress Bar (hidden at start)
        self.progress = QProgressBar()
        self.progress.setRange(0,0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)

        self.setLayout(layout)

        model_loaded = self.load_model()
        if model_loaded:
            self.explain()

    def explain(self):
        self.progress.show()
        #self.pairx_thread = PairXThread(self.query, self.match, self.model)
        #self.pairx_thread.explained_img.connect(self.capture_explained_img)
        #self.pairx_thread.finished.connect(self.display_images)  # do not continue until finished
        #self.pairx_thread.finished.connect(self.progress.hide)
        #self.pairx_thread.start()
    def load_model(self):
        self.reid_filepath = models.get_path(Path(config.load('ML_DIR')), config.load('REID_KEY'))
        if self.reid_filepath:
            self.model = animl.load_miew(self.reid_filepath)
            return True
        else:
            dialog = AlertPopup(self.parent, prompt="Warning, Re-ID model not found. Make sure the path is correct in configuration or re-download.")
            if dialog.exec():
                del dialog
            return False

    def capture_explained_img(self, img_array):
        self.explained_img = np.asarray(img_array)
        print(self.explained_img.shape)

    def display_images(self):
        self.image.load_from_array(self.explained_img)

    def last_layer(self):
        print('last')

    def next_layer(self):
        print('last')