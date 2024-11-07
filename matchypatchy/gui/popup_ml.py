"""
Popup for Selection within a list, ie Survey selection



"""
import wget
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QProgressBar, 
                             QComboBox, QCheckBox, QLabel, QDialogButtonBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from matchypatchy import config
from matchypatchy.ml import models



class MLDownloadPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.models = list(models.MODELS.keys())
        self.checked_models = set()

        self.setWindowTitle("Select Models")

        # Create layout for the checkboxes and add it to the dialog
        layout = QVBoxLayout(self)
        self.checkbox_layout = QGridLayout()
        layout.addLayout(self.checkbox_layout)

        # Add checkboxes to the grid layout in two columns
        for i, m in enumerate(self.models):
            checkbox = QCheckBox(m)
            self.checkbox_layout.addWidget(checkbox, i, 0)

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

        self.available_models = models.available_models()
        print(self.available_models)
        self.set_checkboxes()
        

    def set_checkboxes(self):
        for m in self.available_models.keys():
            checkbox = self.checkbox_layout.itemAtPosition(self.models.index(m),0).widget()
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



class MLOptionsPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle('Model Options')
        layout = QVBoxLayout()

        # Detector
        self.detector_label = QLabel("Select Detector Model:")
        self.detector = QComboBox()
        layout.addWidget(self.detector_label)
        layout.addWidget(self.detector)

        self.available_detectors = list(models.available_models(models.DETECTORS))
        self.detector.addItems(self.available_detectors)

        # Classifier
        self.classifier_label = QLabel("Select Classifier Model:")
        self.classifier = QComboBox()
        layout.addWidget(self.classifier_label)
        layout.addWidget(self.classifier)

        self.available_classifiers = list(models.available_models(models.CLASSIFIERS))
        self.classifier.addItems(self.available_classifiers)

        # Re-ID
        self.reid_label = QLabel("Select Re-Identification Model:")
        self.reid = QComboBox()
        layout.addWidget(self.reid_label)
        layout.addWidget(self.reid)

        self.available_reids = list(models.available_models(models.REIDS))
        self.reid.addItems(self.available_reids)

        # Viewpoint
        self.viewpoint_label = QLabel("Select Viewpoint Model:")
        self.viewpoint = QComboBox()
        layout.addWidget(self.viewpoint_label)
        layout.addWidget(self.viewpoint)

        self.available_viewpoints = list(models.available_models(models.VIEWPOINTS))
        self.viewpoint_list = ['None'] + self.available_viewpoints
        self.viewpoint.addItems(self.viewpoint_list)

        # Ok/Cancel
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.buttonBox, alignment=Qt.AlignmentFlag.AlignCenter)
        self.buttonBox.accepted.connect(self.accept)  
        self.buttonBox.rejected.connect(self.reject)

        self.setLayout(layout)


    def select_detector(self): 
        self.selected_detector_key = self.available_detectors[self.detector.currentIndex()]
        return self.selected_detector_key

    def select_classifier(self):
        self.selected_classifier_key = self.available_classifiers[self.classifier.currentIndex()]
        return self.selected_classifier_key
    
    def select_reid(self): 
        self.selected_reid_key = self.available_reids[self.reid.currentIndex()]
        return self.selected_reid_key

    def select_viewpoint(self):
        if self.viewpoint.currentIndex() == 0:
            return None
        else:
            self.selected_viewpoint_key = self.available_viewpoints[self.viewpoint.currentIndex() - 1]
            return self.selected_viewpoint_key