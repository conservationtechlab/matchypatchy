"""
Popup for Selection within a list, ie Survey selection

0 MegaDetector v5a
1 Andes
2 Amazon
3 Savanna
4 SE Asia Rainforest
5 Southwest USA

"""
import os
import wget
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QProgressBar, QCheckBox, QLabel, QDialogButtonBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from matchypatchy import config
from matchypatchy.ml import models



class MLDownloadPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.checked_models = set()

        self.setWindowTitle("Select Models")

        # Create layout for the checkboxes and add it to the dialog
        layout = QVBoxLayout(self)
        self.checkbox_layout = QGridLayout()
        layout.addLayout(self.checkbox_layout)

        # Add checkboxes to the grid layout in two columns
        for m in models.MODELS:
            checkbox = QCheckBox(models.MODELS[m][0])
            self.checkbox_layout.addWidget(checkbox, m, 0)

        # Add OK and Cancel buttons
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.buttonBox, alignment=Qt.AlignmentFlag.AlignCenter)
        self.buttonBox.accepted.connect(self.accept)  
        self.buttonBox.rejected.connect(self.reject)

          # Progress Bar (hidden at start)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.available_models = models.import_models()
        self.set_checkboxes()
        

    def set_checkboxes(self):
        for m in self.available_models.keys():
            checkbox = self.checkbox_layout.itemAtPosition(m,0).widget()
            checkbox.setChecked(True)

    def toggle_checkbox(self):
        pass
    
    def download_ml(self):
        self.progress_bar.setRange(0,len(self.checked_models))
        self.progress_bar.show()
        self.build_thread = DownloadMLThread(self.checked_models)
        self.build_thread.downloaded.connect(self.progress_bar.setValue)
        self.build_thread.start()


class DownloadMLThread(QThread):
    """
    Thread for launching 
    """
    downloaded = pyqtSignal(int)
   

    def __init__(self, checked_models):
        super().__init__()
        self.checked_models = checked_models

    def run(self):
        for model in self.checked_models:
            wget.download(models.MODELS[model][2], out=config.ML_PATH)
            self.downloaded.emit(model)
