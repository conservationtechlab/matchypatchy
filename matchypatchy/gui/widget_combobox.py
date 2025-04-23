from PyQt6.QtWidgets import QComboBox
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt

class ComboBoxSeparator(QComboBox):
    def __init__(self):
        super().__init__()
        self.setModel(QStandardItemModel())

    def add_separator(self, label="────────"):
        separator = QStandardItem(label)
        separator.setFlags(Qt.ItemFlag.NoItemFlags)  # Non-selectable, disabled
        self.model().appendRow(separator)