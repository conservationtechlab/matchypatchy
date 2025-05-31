'''
Popup to add or edit species
'''
import os
import logging

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFileDialog,
                             QPushButton, QLineEdit, QLabel, QDialogButtonBox)
from PyQt6.QtGui import QIcon

from matchypatchy import config
from matchypatchy.gui.popup_alert import AlertPopup


ICON_PENCIL = "/home/kyra/matchypatchy/matchypatchy/gui/assets/fluent_pencil_icon.png"
# TODO ICON_PENCIL = os.path.normpath("assets/fluent_pencil_icon.png")

#TODO: rename project folder

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
        titles_layout.addWidget(QLabel("Project Directory:"))
        #titles_layout.addWidget(QLabel("Log File:"))
        #titles_layout.addWidget(QLabel("Model Directory:"))
        path_layout.addLayout(titles_layout)
        
        insert_layout = QVBoxLayout()
        self.home_dir = QLineEdit()
        self.home_dir.setText(str(self.cfg['HOME_DIR']))
        insert_layout.addWidget(self.home_dir)

        path_layout.addLayout(insert_layout)

        path_button_layout = QVBoxLayout()

        button_home_dir = QPushButton()
        button_home_dir.setMaximumHeight(30)
        button_home_dir.setIcon(QIcon(ICON_PENCIL))
        button_home_dir.clicked.connect(self.set_home_dir)

        path_button_layout.addWidget(button_home_dir)
        path_layout.addLayout(path_button_layout)

        layout.addLayout(path_layout)

        # Buttons
        button_layout = QHBoxLayout()
        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def command(self, command):
        self.mpDB._command(self)

    def set_home_dir(self):
        new_db = QFileDialog.getExistingDirectory(self, "Get Project Folder",
                                                  os.path.expanduser('~'),)
        

        # TODO
        # if new_db:
        #     self.home_dir.setText(new_db)
        #     valid = self.mpDB.update_paths(new_db)
        #     if valid:
        #     # Update config
        #         self.cfg['DB_DIR'] = str(new_db)
        #         config.update(self.cfg)
        #         # Log changes
        #         logging.info("DB_DIR CHANGED")
        #         logging.info('DB_DIR: ' + self.cfg['DB_DIR'])
        #     else:
        #         dialog = AlertPopup(self, prompt="Database is invalid. Please select another path or delete.")
        #         if dialog.exec():
        #             del dialog

            # Update config
            # self.cfg['LOG_PATH'] = str(new_log)
            # config.update(self.cfg)
            # # Log changes
            # logging.basicConfig(filename=self.cfg['LOG_PATH'], encoding='utf-8', level=logging.DEBUG, force=True)
            # logging.info("LOG_PATH CHANGED")

            # # Update config
            # self.cfg['ML_DIR'] = str(new_ml)
            # config.update(self.cfg)
            # # Log changes
            # logging.info("ML_DIR CHANGED")
            # logging.info('ML_DIR: ' + self.cfg['ML_DIR'])


