'''
Popup to add or edit species
'''
import os
import logging
import sqlite3

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFileDialog,
                             QPushButton, QLineEdit, QLabel, QDialogButtonBox)
from PyQt6.QtGui import QIcon

from matchypatchy import config
from matchypatchy.gui.popup_alert import AlertPopup



class ConfigPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Edit Config")
        self.setMinimumWidth(600)
        self.mpDB = parent.mpDB
        self.cfg = config.load()

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
        self.db_path.setText(str(self.cfg['DB_PATH']))
        insert_layout.addWidget(self.db_path)
        self.log_path = QLineEdit()
        self.log_path.setText(str(self.cfg['LOG_PATH']))
        insert_layout.addWidget(self.log_path)
        self.ml_path = QLineEdit()
        self.ml_path.setText(str(self.cfg['ML_DIR']))
        insert_layout.addWidget(self.ml_path)

        path_layout.addLayout(insert_layout)

        path_button_layout = QVBoxLayout()

        button_db_path = QPushButton()
        button_db_path.setMaximumHeight(30)
        button_db_path.setIcon(QIcon("/home/kyra/matchypatchy/matchypatchy/gui/assets/fluent_pencil_icon.png"))
        button_db_path.clicked.connect(self.set_db)

        button_log_path = QPushButton()
        button_log_path.setMaximumHeight(30)
        button_log_path.setIcon(QIcon("/home/kyra/matchypatchy/matchypatchy/gui/assets/fluent_pencil_icon.png"))
        button_log_path.clicked.connect(self.set_log)

        button_ml_path = QPushButton()
        button_ml_path.setIcon(QIcon("/home/kyra/matchypatchy/matchypatchy/gui/assets/fluent_pencil_icon.png"))
        button_ml_path.setMaximumHeight(30)
        button_ml_path.clicked.connect(self.set_ml)

        path_button_layout.addWidget(button_db_path)
        path_button_layout.addWidget(button_log_path)
        path_button_layout.addWidget(button_ml_path)
        path_layout.addLayout(path_button_layout)

        layout.addLayout(path_layout)

        # Buttons
        button_layout = QHBoxLayout()
        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def set_db(self):
        new_db = QFileDialog.getOpenFileName(self, "Get Database",
                                              os.path.expanduser('~'),
                                              ("DB Files (*.db)"))[0]
        if new_db:
            self.ml_path.setText(new_db)
            # TODO: verify db
            # Update config
            self.cfg['DB_PATH'] = str(new_db)
            config.update(self.cfg)
            # Log changes
            logging.info("DB_PATH CHANGED")
            logging.info('DB_PATH: ' + self.cfg['DB_PATH'])



    def set_log(self):
        new_log = QFileDialog.getSaveFileName(self, "New File",
                                              os.path.expanduser('~'),
                                              ("Log Files (*.log)"))[0]
        if new_log:
            self.log_path.setText(new_log)
            # Update config
            self.cfg['LOG_PATH'] = str(new_log)
            config.update(self.cfg)
            # Log changes
            logging.basicConfig(filename=self.cfg['LOG_PATH'], encoding='utf-8', level=logging.DEBUG, force=True)
            logging.info("LOG_PATH CHANGED")


    def set_ml(self):
        new_ml = QFileDialog.getExistingDirectory(self)
        if new_ml:
            self.ml_path.setText(new_ml)
            # Update config
            self.cfg['ML_DIR'] = str(new_ml)
            config.update(self.cfg)
            # Log changes
            logging.info("ML_DIR CHANGED")
            logging.info('ML_DIR: ' + self.cfg['ML_DIR'])
