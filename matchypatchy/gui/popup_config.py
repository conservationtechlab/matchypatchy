'''
Popup to add or edit species
'''
import os
import logging
from pathlib import Path

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFileDialog, QFrame,
                             QPushButton, QLineEdit, QLabel, QDialogButtonBox)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from matchypatchy import config
from matchypatchy.algo.utils import is_cuda_available
from matchypatchy.gui.popup_alert import AlertPopup


ICON_PENCIL = config.resource_path("assets/fluent_pencil_icon.png")

class ConfigPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Edit Config")
        self.setMinimumWidth(600)
        self.mpDB = parent.mpDB
        self.cfg = config.load()

        layout = QVBoxLayout()

        # Directory ---------------------------------------------------------------
        directory_layout = QHBoxLayout()
        directory_layout.addWidget(QLabel("Project Directory:"))
 
        self.home_dir = QLineEdit()
        self.home_dir.setText(str(self.cfg['HOME_DIR']))
        directory_layout.addWidget(self.home_dir)

        button_home_dir = QPushButton()
        button_home_dir.setMaximumHeight(30)
        button_home_dir.setFixedWidth(30)
        button_home_dir.setIcon(QIcon(ICON_PENCIL))
        button_home_dir.clicked.connect(self.set_home_dir)
        directory_layout.addWidget(button_home_dir)
        layout.addLayout(directory_layout)

        # CUDA -----------------------------------------------------------------
        cuda_layout = QHBoxLayout()
        cuda_layout.addWidget(QLabel("CUDA Available:"))
        cuda = is_cuda_available()
        cuda_available = QLabel(f"{cuda}")
        cuda_available.setStyleSheet("color: green;" if cuda else "color: red;")
        cuda_layout.addWidget(cuda_available)
        layout.addLayout(cuda_layout)

        # MPDB KEY -----------------------------------------------------------------
        mpdbkey_layout = QHBoxLayout()
        mpdbkey_layout.addWidget(QLabel("DBKey:"))
        mpdbkey = self.mpDB.validate()
        mpdbkey_valid = QLabel(f"{mpdbkey}")
        mpdbkey_valid.setStyleSheet("color: red;" if not mpdbkey else "")
        mpdbkey_layout.addWidget(mpdbkey_valid)
        layout.addLayout(mpdbkey_layout)

        # Advanced -------------------------------------------------------------
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.Shape.HLine)  # Set the shape to a horizontal line
        self.separator.setFrameShadow(QFrame.Shadow.Sunken) # Set the shadow style
        self.separator.hide()
        layout.addWidget(self.separator)

        command_layout = QHBoxLayout()
        self.advanced_command = QLabel("Database Command:")
        self.advanced_command.hide()
        command_layout.addWidget(self.advanced_command)
        self.command_line = QLineEdit()
        self.command_line.setText("Enter SQL Command")
        self.command_line.hide()
        command_layout.addWidget(self.command_line)

        self.button_command = QPushButton("↵")
        self.button_command.setMaximumHeight(30)
        self.button_command.setFixedWidth(30)
        self.button_command.clicked.connect(self.command)
        self.button_command.hide()
        command_layout.addWidget(self.button_command)

        layout.addLayout(command_layout)


        # BUTTONS --------------------------------------------------------------
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
        visible = self.advanced_command.isVisible()
        self.separator.setVisible(not visible)
        self.advanced_command.setVisible(not visible)
        self.command_line.setVisible(not visible)
        self.button_command.setVisible(not visible)

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
                # Update home dir
                self.cfg['HOME_DIR'] = str(new_project)
                self.cfg['DB_DIR'] = str(new_db)

                # Update config
                self.cfg['LOG_PATH'] = new_project + "/matchypatchy.log"
                logging.basicConfig(filename=self.cfg['LOG_PATH'], encoding='utf-8', level=logging.DEBUG, force=True)
                logging.info("HOME_DIR CHANGED")
                logging.info('HOME_DIR: ' + self.cfg['HOME_DIR'])

                # Check or create ML, Thumbnail and Frame folders
                new_ml= Path(new_project) / "Models"
                Path.mkdir(new_ml, exist_ok=True)
                self.cfg['ML_DIR'] = str(new_ml)

                new_thumb= Path(new_project) / "Thumbnails"
                Path.mkdir(new_thumb, exist_ok=True)
                self.cfg['THUMBNAIL_DIR'] = str(new_thumb)

                new_frame = Path(new_project) / "Frames"
                Path.mkdir(new_frame, exist_ok=True)
                self.cfg['FRAME_DIR'] = str(new_frame)

                # save changes to yml
                config.update(self.cfg)

            else:
                dialog = AlertPopup(self, prompt="Database is invalid. Please select another path or delete.")
                if dialog.exec():
                    del dialog

          


