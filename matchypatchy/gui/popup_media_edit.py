"""
Edit A Fields for Multiple Images


"""
import pandas as pd
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QFrame,
                             QLabel, QTextEdit, QDialogButtonBox, QPushButton)
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from matchypatchy.gui.popup_individual import IndividualFillPopup
from matchypatchy.gui.widget_image import ImageWidget

from matchypatchy.algo.models import load
import matchypatchy.database.media as db_roi

class MediaEditPopup(QDialog):
    def __init__(self, parent, ids):
        super().__init__(parent)
        self.setWindowTitle("View Image")