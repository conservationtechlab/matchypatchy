"""
GUI Window for viewing images
"""
from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent

from .widget_image import ImageWidget
from .media_table import MediaTable

# TODO
# add single/paired view toggle button

class DisplayMedia(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.mpDB = parent.mpDB
        
        layout = QVBoxLayout()

        self.label = QLabel("Media")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFixedHeight(20)
        layout.addWidget(self.label)
        
        first_layer = QHBoxLayout()
        survey_label = QLabel("Survey:")
        first_layer.addWidget(survey_label, 0)
        self.survey_select = QComboBox()
        self.survey_select.currentIndexChanged.connect(self.select_survey)
        first_layer.addWidget(self.survey_select, 2)
        self.update_survey()
        layout.addLayout(first_layer)


        self.setLayout(layout)
        
    def home(self):
        self.parent._set_base_view()

    def update_survey(self):
        survey_names = self.mpDB.select('survey',columns='id, name')
        self.survey_list_ordered = list(survey_names)
        if self.survey_list_ordered:
            self.survey_select.addItems([el[1] for el in survey_names])

    def select_survey(self):
        self.active_survey = self.survey_list_ordered[self.survey_select.currentIndex()]

    # Keyboard Handler
    def keyPressEvent(self, event):
        key = event.key()
        key_text = event.text()
        print(f"Key pressed: {key_text} (Qt key code: {key})")



