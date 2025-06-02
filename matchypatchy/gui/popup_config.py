'''
Popup to add or edit species
'''
import os
import logging
from pathlib import Path

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

        # TITLES ---------------------------------------------------------------
        path_layout = QHBoxLayout()

        titles_layout = QVBoxLayout()
        titles_layout.addWidget(QLabel("Project Directory:"))
        #titles_layout.addWidget(QLabel("Model Directory:"))

        # Advanced
        self.advanced_command = QLabel("Database Command:")
        self.advanced_command.hide()
        titles_layout.addWidget(self.advanced_command)
        path_layout.addLayout(titles_layout)
        
        # TEXT -----------------------------------------------------------------
        insert_layout = QVBoxLayout()
        self.home_dir = QLineEdit()
        self.home_dir.setText(str(self.cfg['HOME_DIR']))
        insert_layout.addWidget(self.home_dir)

        # Advanced
        self.command_line = QLineEdit()
        self.command_line.setText("Enter SQL Command")
        self.command_line.hide()
        insert_layout.addWidget(self.command_line)
        path_layout.addLayout(insert_layout)

        # BUTTONS --------------------------------------------------------------
        path_button_layout = QVBoxLayout()
        button_home_dir = QPushButton()
        button_home_dir.setMaximumHeight(30)
        button_home_dir.setFixedWidth(30)
        button_home_dir.setIcon(QIcon(ICON_PENCIL))
        button_home_dir.clicked.connect(self.set_home_dir)
        path_button_layout.addWidget(button_home_dir)

        # Advanced
        self.button_command = QPushButton("↵")
        self.button_command.setMaximumHeight(30)
        self.button_command.setFixedWidth(30)
        self.button_command.clicked.connect(self.command)
        self.button_command.hide()
        path_button_layout.addWidget(self.button_command)
        path_layout.addLayout(path_button_layout)

        layout.addLayout(path_layout)

        # Buttons
        button_layout = QHBoxLayout()

        button_advanced = QPushButton("Advanced")
        button_advanced.clicked.connect(self.show_advanced)
        button_layout.addWidget(button_advanced)

        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def show_advanced(self):
        self.advanced_command.show()
        self.command_line.show()
        self.button_command.show()

    def command(self):
        new_cmd = self.command_line.text()
        self.mpDB._command(new_cmd)

    def set_home_dir(self):
        new_project = QFileDialog.getExistingDirectory(self, "Get Project Folder",
                                                  os.path.expanduser('~'),)
        if new_project:
            self.home_dir.setText(new_project)
            new_db = Path(new_project) / "Database"
            valid = self.mpDB.update_paths(new_db)


            if valid:
            # Update config
                self.cfg['DB_DIR'] = str(new_db)
                config.update(self.cfg)
                # Log changes
                logging.info("DB_DIR CHANGED")
                logging.info('DB_DIR: ' + self.cfg['DB_DIR'])
            else:
                dialog = AlertPopup(self, prompt="Database is invalid. Please select another path or delete.")
                if dialog.exec():
                    del dialog

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


