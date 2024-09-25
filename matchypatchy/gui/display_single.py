import sys
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QWidget,
                             QMenuBar, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel,QSizePolicy, QFileDialog)
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QImage, QPixmap



class DisplaySingle(QWidget):
    def __init__(self, mainwindow):
        super().__init__()
        # Title
        print(mainwindow.active_survey)
        layout = QVBoxLayout()
        mainwindow.label = QLabel("Image Viewer")
        mainwindow.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(mainwindow.label,0)

        # Iimage screen
        mainwindow.image_label = QLabel()
        mainwindow.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mainwindow.image_label.setScaledContents(True)
        mainwindow.image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        layout.addWidget(mainwindow.image_label,1)

        #self.image = QImage()
        #pixmap = QPixmap(self.image)
        #self.image_label.setPixmap(pixmap)