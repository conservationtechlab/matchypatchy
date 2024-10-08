"""
GUI Window for viewing images
"""
from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QSpacerItem, QSizePolicy)
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
        
        first_layer = QHBoxLayout()
        survey_label = QLabel("Survey:")
        survey_label.setFixedWidth(50)
        first_layer.addWidget(survey_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.survey_select = QComboBox()
        self.survey_select.currentIndexChanged.connect(self.select_survey)
        self.survey_select.setFixedWidth(200)
        first_layer.addWidget(self.survey_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        return_button = QPushButton("Home")
        return_button.clicked.connect(self.home)
        return_button.setFixedWidth(100)
        first_layer.addWidget(return_button, 0,  alignment=Qt.AlignmentFlag.AlignLeft)

        first_layer.addStretch()
        layout.addLayout(first_layer)

        # MEDIA TABLE
        self.media_table = MediaTable(self)
        layout.addWidget(self.media_table, stretch=1)

        self.setLayout(layout)

        self.update_survey()
        
    def home(self):
        self.parent._set_base_view()

    def update_survey(self):
        survey_names = self.mpDB.select('survey',columns='id, name')
        self.survey_list_ordered = list(survey_names)
        if self.survey_list_ordered:
            self.survey_select.addItems([el[1] for el in survey_names])

    def select_survey(self):
        self.active_survey = self.survey_list_ordered[self.survey_select.currentIndex()]

    def update(self):
        self.media_table.update()

    # Keyboard Handler
    def keyPressEvent(self, event):
        key = event.key()
        key_text = event.text()
        print(f"Key pressed: {key_text} (Qt key code: {key})")



