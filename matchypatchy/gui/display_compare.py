import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QWidget,
                             QMenuBar, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel)
from PyQt6.QtCore import QSize, Qt


class DisplayCompare(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.mpDB = parent.mpDB
        layout = QVBoxLayout(self)
        
        self.label = QLabel("Welcome to MatchyPatchy")
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.label)