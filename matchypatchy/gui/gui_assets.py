"""
Custom assets for the GUI, such as buttons and separators.

"""
from PyQt6.QtWidgets import (QFrame, QSizePolicy, QPushButton, QComboBox)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt


class VerticalSeparator(QFrame):
    def __init__(self, linewidth=1):
        super().__init__()
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setLineWidth(linewidth)


class HorizontalSeparator(QFrame):
    def __init__(self, linewidth=1):
        super().__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setLineWidth(linewidth)


class StandardButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        #self.setFixedHeight(30)
        self.setFixedWidth(100)
        #self.setStyleSheet("font-size: 14px; padding: 5px 15px;")


class ComboBoxSeparator(QComboBox):
    def __init__(self):
        super().__init__()
        self.setModel(QStandardItemModel())

    def add_separator(self, label="────────"):
        separator = QStandardItem(label)
        separator.setFlags(Qt.ItemFlag.NoItemFlags)  # Non-selectable, disabled
        self.model().appendRow(separator)


class FilterBox(QComboBox):
    def __init__(self, initial_list, width):
        super().__init__()
        self.setModel(QStandardItemModel())
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedWidth(width)
        self.addItems([el[1] for el in initial_list])
