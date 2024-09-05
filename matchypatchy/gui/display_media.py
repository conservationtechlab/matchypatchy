"""
GUI Window for viewing images
"""
from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent

from .widget_image import ImageWidget


# TODO
# add single/paired view toggle button

class DisplayMedia(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.mpDB = parent.mpDB
        
        container = QVBoxLayout()

        self.label = QLabel("Welcome to MatchyPatchy")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFixedHeight(20)
        container.addWidget(self.label)
        
        # Control Panel
        control_panel = QVBoxLayout()

        layer_one = QHBoxLayout()
        self.survey_select = QComboBox()
        #self.survey_select.currentIndexChanged.connect(self.select_survey)
        layer_one.addWidget(self.survey_select, 1)

        layer_one = QHBoxLayout()
        layer_one.addWidget(QPushButton("Button 1"))
        layer_one.addWidget(QPushButton("Button 2"))
        layer_two = QHBoxLayout()
        layer_two.addWidget(QLabel("Label 1"))
        layer_two.addWidget(QLabel("Label 2"))
        control_panel.addLayout(layer_one)
        container.addLayout(control_panel)
        
        # Images
        image_layout = QHBoxLayout()
        
        left_side = QVBoxLayout()
        left_label = QLabel("Camera 1")
        left_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_side.addWidget(left_label,0)
        self.left_box = ImageWidget()
        left_side.addWidget(self.left_box)
        image_layout.addLayout(left_side)
        
        right_side = QVBoxLayout()
        right_label = QLabel("Camera 2")
        right_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_side.addWidget(right_label,0)
        self.right_box = ImageWidget()
        right_side.addWidget(self.right_box)
        image_layout.addLayout(right_side)
        
        container.addLayout(image_layout)
        
        # Buttons
        bottom_layer = QHBoxLayout()
        button_home = QPushButton("Home")
        button_home.clicked.connect(self.home)
        button_load = QPushButton("Load Data")
        button_match = QPushButton("Match")

        # Add buttons to the layout
        bottom_layer.addWidget(button_home)
        bottom_layer.addWidget(button_load)
        bottom_layer.addWidget(button_match)
        container.addLayout(bottom_layer)
        
        #self.left_box.display_image_padded('/home/kyra/animl-py/examples/Southwest/2021-06-30_SYFR0218.JPG')
        #self.right_box.display_image_padded('/home/kyra/animl-py/examples/Southwest/2021-08-08_RCNX0063.JPG')

        self.left_box.display_image_padded("C:/Users/tswanson/animl-py/examples/Southwest/2021-06-30_SYFR0218.JPG")
        self.right_box.display_image_padded('C:/Users/tswanson/animl-py/examples/Southwest/2021-08-08_RCNX0063.JPG')

        self.setLayout(container)
        
    def home(self):
        self.parent._set_base_view()

    def update_survey(self):
        survey_names = self.mpDB.fetch_columns(table='survey',columns='name')
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



