"""
GUI Window for viewing images
"""
from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QSizePolicy)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt


class DisplayMedia(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.mpDB = parent.mpDB
        container = QVBoxLayout(self)

        self.label = QLabel("Welcome to MatchyPatchy")
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        container.addWidget(self.label,0)
        
        # Images
        image_layout = QHBoxLayout()

        self.left_box = QLabel()
        self.left_box.resize(400,300)
        self.left_box.setScaledContents(True)
        self.left_box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        image_layout.addWidget(self.left_box,0)
         
        self.right_box = QLabel()
        self.right_box.resize(400,300)
        self.right_box.setScaledContents(True)
        self.right_box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        image_layout.addWidget(self.right_box,0)
        container.addLayout(image_layout,0)
        
        
        # Buttons
        bottom_layer = QHBoxLayout()
        button_validate = QPushButton("Validate DB")
        button_load = QPushButton("Load Data")
        button_match = QPushButton("Match")

        # Add buttons to the layout
        bottom_layer.addWidget(button_validate)
        bottom_layer.addWidget(button_load)
        bottom_layer.addWidget(button_match)
        container.addLayout(bottom_layer)
        
        
        self.load_image1('/home/kyra/animl-py/examples/Southwest/2021-06-30_SYFR0218.JPG')
        self.load_image2('/home/kyra/animl-py/examples/Southwest/2021-08-08_RCNX0063.JPG')
        
        

    def load_image1(self, filepath):
        self.image1 = QPixmap(filepath)
        self.left_box.setPixmap(self.image1)

        
    def load_image2(self, filepath):
        self.image2 = QPixmap(filepath)
        self.right_box.setPixmap(self.image2)