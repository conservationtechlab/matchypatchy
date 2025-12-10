'''
Popup to add or edit config settings
'''
import os
import logging
from pathlib import Path

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFileDialog,
                             QPushButton, QLineEdit, QLabel, QDialogButtonBox)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from matchypatchy import config
from matchypatchy.gui.popup_alert import AlertPopup
from matchypatchy.gui.gui_assets import HorizontalSeparator, VerticalSeparator

from matchypatchy.algo.models import get_path, is_valid_reid_model


ICON_PENCIL = config.resource_path("assets/graphics/fluent_pencil_icon.png")

class ConfigPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Edit Config")
        self.setMinimumWidth(600)
        self.mpDB = parent.mpDB
        self.cfg = config.load()
        self.ml_dir = Path(config.load('ML_DIR'))
        self.column1_width = 120
        self.edit_width = 80

        layout = QVBoxLayout()

        # Directory ---------------------------------------------------------------
        directory_layout = QHBoxLayout()
        directory_label = QLabel("Project Directory:")
        directory_label.setToolTip("Path to the main project folder containing Database, Models, Thumbnails, etc.")
        directory_label.setFixedWidth(self.column1_width)
        directory_layout.addWidget(directory_label)

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

        # Visualizer Model
        visualizer_layout = QHBoxLayout()
        visualizer_label = QLabel("Visualizer Model:")
        visualizer_label.setToolTip("Model used for visualizing and comparing individuals.")
        visualizer_label.setFixedWidth(self.column1_width)
        visualizer_layout.addWidget(visualizer_label)
        self.visualizer_model = QLineEdit()
        reid_path = get_path(self.ml_dir, self.cfg['REID_KEY'])
        self.visualizer_model.setText(str(reid_path))
        visualizer_layout.addWidget(self.visualizer_model)
        button_visualizer_model = QPushButton()
        button_visualizer_model.setMaximumHeight(30)
        button_visualizer_model.setFixedWidth(30)
        button_visualizer_model.setIcon(QIcon(ICON_PENCIL))
        button_visualizer_model.clicked.connect(self.set_visualizer_model)
        visualizer_layout.addWidget(button_visualizer_model)
        layout.addLayout(visualizer_layout)

        # Sequence
        sequence_layout = QHBoxLayout()
        sequence_duration_label = QLabel("Sequence Length (s):")
        sequence_duration_label.setToolTip("Maximum duration of the sequence in seconds.")
        sequence_duration_label.setFixedWidth(self.column1_width)
        sequence_layout.addWidget(sequence_duration_label)
        self.sequence_duration = QLineEdit()
        self.sequence_duration.setFixedWidth(self.edit_width)
        self.sequence_duration.setText(str(self.cfg['SEQUENCE_DURATION']))
        self.sequence_duration.textChanged.connect(self.update_sequence)
        sequence_layout.addWidget(self.sequence_duration, alignment=Qt.AlignmentFlag.AlignLeft)
        sequence_layout.addWidget(VerticalSeparator())
        sequence_n_label = QLabel("Images per Sequence:")
        sequence_n_label.setToolTip("Max number of images in each sequence.")
        #sequence_n_label.setFixedWidth(self.column1_width)
        sequence_layout.addWidget(sequence_n_label)
        self.sequence_n = QLineEdit()
        self.sequence_n.setFixedWidth(self.edit_width)
        self.sequence_n.setText(str(self.cfg['SEQUENCE_N']))
        self.sequence_n.textChanged.connect(self.update_sequence)
        sequence_layout.addWidget(self.sequence_n, alignment=Qt.AlignmentFlag.AlignLeft)
        sequence_layout.addStretch()
        layout.addLayout(sequence_layout)

        # NUM MATCHES
        nummatches_layout = QHBoxLayout()
        nummatches_label = QLabel("Max # of Matches:")
        nummatches_label.setToolTip("Number of nearest neighbors to consider.")
        nummatches_label.setFixedWidth(self.column1_width)
        nummatches_layout.addWidget(nummatches_label)
        self.nummatches = QLineEdit()
        self.nummatches.setFixedWidth(self.edit_width)
        self.nummatches.setText(str(self.cfg['KNN']))
        nummatches_layout.addWidget(self.nummatches, alignment=Qt.AlignmentFlag.AlignLeft)
        self.nummatches.textChanged.connect(self.update_nummatches)
        layout.addLayout(nummatches_layout)


        # CUDA -----------------------------------------------------------------
        cuda_layout = QHBoxLayout()
        cuda_label = QLabel("CUDA Available:")
        cuda_label.setFixedWidth(self.column1_width)
        cuda_layout.addWidget(cuda_label)
        import onnxruntime as ort
        cuda = ort.get_available_providers()
        #cuda = True if "CUDAExecutionProvider" in ort.get_available_providers() else False
        cuda_available = QLabel(f"{cuda}")
        cuda_available.setStyleSheet("color: green;" if cuda else "color: red;")
        cuda_layout.addWidget(cuda_available, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(cuda_layout)

        # MPDB KEY -----------------------------------------------------------------
        mpdbkey_layout = QHBoxLayout()
        mpdbkey_label = QLabel("Database Key:")
        mpdbkey_label.setToolTip("Unique identifier for the current database.")
        mpdbkey_label.setFixedWidth(self.column1_width)
        mpdbkey_layout.addWidget(mpdbkey_label)
        mpdbkey = self.mpDB.validate()
        mpdbkey_valid = QLabel(f"{mpdbkey}")
        mpdbkey_valid.setStyleSheet("color: red;" if not mpdbkey else "")
        mpdbkey_layout.addWidget(mpdbkey_valid, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(mpdbkey_layout)

        # Advanced -------------------------------------------------------------
        self.separator = HorizontalSeparator()
        self.separator.hide()
        layout.addWidget(self.separator)

        command_layout = QHBoxLayout()
        self.advanced_command = QLabel("Database Command:")
        self.advanced_command.setFixedWidth(self.column1_width)
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
                global HOME_DIR
                HOME_DIR = Path(new_project)
                self.cfg['DB_DIR'] = str(new_db)

                # Update config
                self.cfg['LOG_PATH'] = new_project + "/matchypatchy.log"
                logging.basicConfig(filename=self.cfg['LOG_PATH'], encoding='utf-8', level=logging.DEBUG, force=True)
                logging.info("HOME_DIR CHANGED")
                logging.info('HOME_DIR: ' + str(HOME_DIR))

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

    def set_visualizer_model(self):
        
        new_model = QFileDialog.getOpenFileName(self, "Select Re-ID Model",
                                                  os.path.expanduser(self.ml_dir),"Model Files (*.pt *.pth *.bin)")
        if new_model and new_model[0]:
            if is_valid_reid_model(Path(new_model[0]).stem):
                # Update config
                self.visualizer_model.setText(new_model[0])
                self.cfg['REID_KEY'] = str(Path(new_model[0]).stem)
                # save changes to yml
                config.update(self.cfg)
            else:
                dialog = AlertPopup(self, prompt="Model not recognized. Please select a valid Re-ID model.")
                if dialog.exec():
                    del dialog
          
    def update_nummatches(self):
        try:
            nummatches = int(self.nummatches.text())
            if nummatches > 0:
                self.cfg['KNN'] = nummatches
                config.update(self.cfg)
        except ValueError:
            pass

    def update_sequence(self):
        try:
            duration = int(self.sequence_duration.text())
            n = int(self.sequence_n.text())
            if duration > 0:
                self.cfg['SEQUENCE_DURATION'] = duration
                self.cfg['SEQUENCE_N'] = n
                config.update(self.cfg)
        except ValueError:
            pass

