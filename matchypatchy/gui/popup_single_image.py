"""
Edit A Single Image


"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QListWidget,
                             QLabel, QLineEdit, QDialogButtonBox)
from PyQt6 import QtCore, QtWidgets

class ImagePopup(QDialog):
    def __init__(self, parent, rid):
        super().__init__(parent)
        self.setWindowTitle("View Image")
        self.mpDB = parent.mpDB
        self.rid = rid
        print(self.rid)

        layout = QVBoxLayout()
        # SITE LIST
        self.list = QListWidget()
        layout.addWidget(self.list)
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        # Buttons
        button_layout = QHBoxLayout()
                # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)

        self.setLayout(layout)
