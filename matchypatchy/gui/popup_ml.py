"""
Popup for Selection within a list, ie Survey selection

"""
import logging

from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QProgressBar,
                             QComboBox, QCheckBox, QLabel, QDialogButtonBox)
from PyQt6.QtCore import Qt

from matchypatchy.algo import models
from matchypatchy import config


class MLDownloadPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        # update model yml 
        update_confirmed = models.update_model_yml()
        logging.info(f"Model yaml update attempt: {update_confirmed}")
        self.ml_dir = Path(config.load('ML_DIR'))
        self.ml_cfg = models.load()
        self.models = self.ml_cfg['MODELS']
        self.checked_models = set()
        self.available_models = self.discover_models()

        self.setWindowTitle("Select Models")

        # Create layout for the checkboxes and add it to the dialog
        layout = QVBoxLayout(self)
        self.checkbox_layout = QGridLayout()
        layout.addLayout(self.checkbox_layout)

        # Add checkboxes to the grid layout in two columns
        self.models = list(self.models)  # convert to ordered list
        for i, m in enumerate(self.models):
            checkbox = QCheckBox(m)
            checkbox.stateChanged.connect(self.toggle_checkbox)
            self.checkbox_layout.addWidget(checkbox, i, 0)

        # Add OK and Cancel buttons
        layout.addSpacing(20)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.buttonBox, alignment=Qt.AlignmentFlag.AlignCenter)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.cancel)

        # Progress Bar (hidden at start)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # check already downloaded models
        self.set_checkboxes()

    def discover_models(self):
        models_dict = dict()
        for m in self.models.keys():
            path = self.ml_dir / self.models[m][0]
            if path.exists():
                models_dict[m] = path
        # if looking for a particular model, give back path
        return models_dict

    def set_checkboxes(self):
        for m in self.available_models.keys():
            checkbox = self.checkbox_layout.itemAtPosition(self.models.index(m), 0).widget()
            checkbox.setChecked(True)

    def toggle_checkbox(self):
        all = set()
        for i, m in enumerate(self.models):
            checkbox = self.checkbox_layout.itemAtPosition(i, 0).widget()
            if checkbox.isChecked():
                all.add(m)
        # see if any are newly checked
        self.checked_models = all - set(self.available_models.keys())
        if self.checked_models:
            self.download_ml()
    
    def toggle_close(self):
        ok_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setEnabled(not ok_button.isEnabled())  # Disable the OK button

    def download_ml(self):
        # Start download thread
        self.toggle_close()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        self.build_thread = models.DownloadMLThread(self.ml_dir, self.checked_models)
        self.build_thread.finished.connect(self.progress_bar.hide)
        self.build_thread.finished.connect(self.toggle_close)
        self.build_thread.start()

    def cancel(self):
        for key in self.checked_models:
            models.delete(self.ml_dir, key)
        self.reject()


class MLOptionsPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.ml_dir = Path(config.load('ML_DIR'))
        self.ml_cfg = models.load()
        self.available_models = self.discover_models()

        self.setWindowTitle('Model Options')
        layout = QVBoxLayout()
        layout.addSpacing(10)

        # Sequence
        self.sequence = QCheckBox("Calculate Sequence")
        self.sequence.setStyleSheet("""QCheckBox {padding: 5px;}
                                       QCheckBox::indicator {width: 25px; height: 25px;}""")
        layout.addWidget(self.sequence)

        # Detector
        self.detector_label = QLabel("Select Detector Model:")
        self.detector = QComboBox()
        layout.addWidget(self.detector_label)
        layout.addWidget(self.detector)

        self.available_detectors = self.get_subset('DETECTOR_MODELS')
        self.detector.addItems(self.available_detectors)

        # Classifier
        #self.classifier_label = QLabel("Select Classifier Model:")
        #self.classifier = QComboBox()
        #layout.addWidget(self.classifier_label)
        #layout.addWidget(self.classifier)

        #self.available_classifiers = ['None'] + self.get_subset('CLASSIFIER_MODELS')
        #self.classifier.addItems(self.available_classifiers)

        # Re-ID
        self.reid_label = QLabel("Select Re-Identification Model:")
        self.reid = QComboBox()
        layout.addWidget(self.reid_label)
        layout.addWidget(self.reid)

        self.available_reids = self.get_subset('REID_MODELS')
        self.reid.addItems(self.available_reids)

        # Viewpoint
        self.viewpoint_label = QLabel("Select Viewpoint Model:")
        self.viewpoint = QComboBox()
        layout.addWidget(self.viewpoint_label)
        layout.addWidget(self.viewpoint)

        self.available_viewpoints = ['None'] + self.get_subset('VIEWPOINT_MODELS')
        self.viewpoint.addItems(self.available_viewpoints)

        # Ok/Cancel
        layout.addSpacing(20)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.buttonBox, alignment=Qt.AlignmentFlag.AlignCenter)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.setLayout(layout)

    def discover_models(self):
        models_dict = dict()
        for m in self.ml_cfg['MODELS'].keys():
            path = self.ml_dir / self.ml_cfg['MODELS'][m][0]
            if path.exists():
                models_dict[m] = path
        # if looking for a particular model, give back path
        return models_dict

    def get_subset(self, subset):
        # GET THE AVAILABLE MODELS OF SUBSET TYPE
        models_dict = dict()
        for m in self.ml_cfg[subset]:
            if m in self.available_models.keys():
                path = self.ml_dir / self.available_models[m]
                if path.exists():
                    models_dict[m] = path
        # if looking for a particular model, give back path
        return list(models_dict)

    def select_sequence(self):
        return self.sequence.isChecked()

    def select_detector(self):
        if len(self.available_detectors) == 0:
            return None
        else:
            self.selected_DETECTOR_KEY = self.available_detectors[self.detector.currentIndex()]
            return self.selected_DETECTOR_KEY

    # def select_classifier(self):
    #     if self.classifier.currentIndex() == 0:
    #         return None
    #     else:
    #         self.selected_classifier_key = self.available_classifiers[self.classifier.currentIndex()]
    #         return self.selected_classifier_key

    def select_reid(self):
        if len(self.available_reids) == 0:
            return None
        else:
            self.selected_REID_KEY = self.available_reids[self.reid.currentIndex()]
            return self.selected_REID_KEY

    def select_viewpoint(self):
        if self.viewpoint.currentIndex() == 0:
            return None
        else:
            self.selected_VIEWPOINT_KEY = self.available_viewpoints[self.viewpoint.currentIndex()]
            return self.selected_VIEWPOINT_KEY
        
    def return_selections(self):
        sequence_checked = self.select_sequence()
        DETECTOR_KEY = self.select_detector()
        #classifier_key = self.select_classifier()
        REID_KEY = self.select_reid()
        VIEWPOINT_KEY = self.select_viewpoint()
        return {"sequence_checked":sequence_checked,
                "DETECTOR_KEY":DETECTOR_KEY,
                #"classifier_key":classifier_key,
                "REID_KEY":REID_KEY,
                "VIEWPOINT_KEY":VIEWPOINT_KEY,}
