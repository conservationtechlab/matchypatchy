'''
Popup to add or edit species
'''
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
                             QHBoxLayout, QPushButton, QLineEdit, QLabel, QDialogButtonBox)
from PyQt6.QtGui import QIcon

from matchypatchy.gui.popup_alert import AlertPopup

import matchypatchy.config as cfg


class ConfigPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Edit Config")
        self.mpDB = parent.mpDB

        layout = QVBoxLayout()

        # Paths
        path_layout = QHBoxLayout()

        titles_layout = QVBoxLayout()
        titles_layout.addWidget(QLabel("Database:"))
        titles_layout.addWidget(QLabel("Log File:"))
        titles_layout.addWidget(QLabel("Model Directory:"))
        path_layout.addLayout(titles_layout)
        
        insert_layout = QVBoxLayout()
        self.db_path = QLineEdit()
        insert_layout.addWidget(self.db_path)
        self.log_path = QLineEdit()
        insert_layout.addWidget(self.log_path)
        self.ml_path = QLineEdit()
        insert_layout.addWidget(self.ml_path)

        path_layout.addLayout(insert_layout)

        path_button_layout = QVBoxLayout()
        button_db_path = QPushButton()
        button_db_path.setMaximumHeight(30)
        button_db_path.setIcon(QIcon("/home/kyra/matchypatchy/matchypatchy/gui/assets/fluent_pencil_icon.png"))
        button_log_path = QPushButton()
        button_log_path.setIcon(QIcon("/home/kyra/matchypatchy/matchypatchy/gui/assets/fluent_pencil_icon.png"))
        button_log_path.setMaximumHeight(30)
        button_ml_path = QPushButton()
        button_ml_path.setIcon(QIcon("/home/kyra/matchypatchy/matchypatchy/gui/assets/fluent_pencil_icon.png"))
        button_ml_path.setMaximumHeight(30)
        path_button_layout.addWidget(button_db_path)
        path_button_layout.addWidget(button_log_path)
        path_button_layout.addWidget(button_ml_path)

        path_layout.addLayout(path_button_layout)

        layout.addLayout(path_layout)

        # Buttons
        button_layout = QHBoxLayout()

        button_new = QPushButton("New")
        self.button_edit = QPushButton("Edit")
        self.button_del = QPushButton("Delete")

        # not enabled until site is selected
        self.button_del.setEnabled(False)
        self.button_edit.setEnabled(False)

        button_layout.addWidget(button_new)
        button_layout.addWidget(self.button_edit)
        button_layout.addWidget(self.button_del)

        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)

        self.setLayout(layout)
