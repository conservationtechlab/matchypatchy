import sys
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QWidget,
                             QMenuBar, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel,QSizePolicy, QFileDialog)
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QImage, QPixmap



class DisplaySingle(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.mpDB = parent.mpDB
        
        layout = QVBoxLayout()

        self.label = QLabel("Image Viewer")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label,0)

        # Iimage screen
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(True)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        layout.addWidget(self.image_label,1)

        #self.image = QImage()
        #pixmap = QPixmap(self.image)
        #self.image_label.setPixmap(pixmap)