'''
Popup to add or edit config settings
'''
import animl
import os
from pathlib import Path

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFileDialog, QComboBox,
                             QPushButton, QLineEdit, QLabel, QDialogButtonBox)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from matchypatchy import config
from matchypatchy.gui.dialogs.popup_alert import AlertPopup
from matchypatchy.gui.dialogs.popup_uploads import UploadManagerPopup
from matchypatchy.gui.widgets.gui_assets import HorizontalSeparator, VerticalSeparator
from matchypatchy.threads.model_download_thread import get_path, is_valid_reid_model


class ConfigPopup(QDialog):
    ICON_PENCIL = str(config.resource_path("assets/graphics/fluent_pencil_icon.png"))
    DEVICE_OPTIONS = {"CPUExecutionProvider": "CPU", "CUDAExecutionProvider": "CUDA-enabled GPU"}

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Edit Config")
        self.setMinimumWidth(600)
        self.logger = parent.logger
        self.cfg = config.load_cfg()
        self.ml_dir = Path(config.load_cfg('ML_DIR'))
        self.label_width = 130
        self.edit_width = 150

        layout = QVBoxLayout()
        # Home Directory -------------------------------------------------------------
        directory_layout = QHBoxLayout()
        directory_label = QLabel("Project Directory:")
        directory_label.setToolTip("Path to the main project folder containing Database, Models, Thumbnails, etc.")
        directory_label.setFixedWidth(self.label_width)
        directory_layout.addWidget(directory_label)
        # Editable line for project directory
        self.home_dir = QLineEdit()
        self.home_dir.setText(str(self.cfg.HOME_DIR))
        directory_layout.addWidget(self.home_dir)
        # Edit button
        button_home_dir = QPushButton()
        button_home_dir.setMaximumHeight(30)
        button_home_dir.setFixedWidth(30)
        button_home_dir.setIcon(QIcon(self.ICON_PENCIL))
        button_home_dir.clicked.connect(self.set_home_dir)
        directory_layout.addWidget(button_home_dir)
        # Add Button
        button_add = QPushButton("+")
        button_add.clicked.connect(self.new_project)
        button_add.setMaximumHeight(30)
        button_add.setFixedWidth(30)
        directory_layout.addWidget(button_add)
        layout.addLayout(directory_layout)

        # UPDATE UPLOADS DIRECTORIES -------------------------------------------
        uploads_layout = QHBoxLayout()
        self.button_uploads = QPushButton("Edit Source Directories")
        self.button_uploads.setFixedWidth(self.column1_width)
        self.button_uploads.clicked.connect(self.edit_uploads)
        uploads_layout.addWidget(self.button_uploads, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(uploads_layout)

        # Visualizer Model
        visualizer_layout = QHBoxLayout()
        visualizer_label = QLabel("Visualizer Model:")
        visualizer_label.setToolTip("Model used for visualizing and comparing individuals.")
        visualizer_label.setFixedWidth(self.label_width)
        visualizer_layout.addWidget(visualizer_label)
        self.visualizer_model = QLineEdit()
        reid_path = get_path(self.ml_dir, self.cfg.REID_KEY)
        self.visualizer_model.setText(str(reid_path))
        visualizer_layout.addWidget(self.visualizer_model)
        button_visualizer_model = QPushButton()
        button_visualizer_model.setMaximumHeight(30)
        button_visualizer_model.setFixedWidth(30)
        button_visualizer_model.setIcon(QIcon(self.ICON_PENCIL))
        button_visualizer_model.clicked.connect(self.set_visualizer_model)
        visualizer_layout.addWidget(button_visualizer_model)
        # Disable for now
        # layout.addLayout(visualizer_layout)

        # Sequence
        sequence_layout = QHBoxLayout()
        sequence_duration_label = QLabel("Sequence Length (s):")
        sequence_duration_label.setToolTip("Maximum duration of the sequence in seconds.")
        sequence_duration_label.setFixedWidth(self.label_width)
        sequence_layout.addWidget(sequence_duration_label)
        self.sequence_duration = QLineEdit()
        self.sequence_duration.setFixedWidth(self.edit_width)
        self.sequence_duration.setText(str(self.cfg.SEQUENCE_DURATION))
        self.sequence_duration.textChanged.connect(self.update_sequence)
        sequence_layout.addWidget(self.sequence_duration, alignment=Qt.AlignmentFlag.AlignLeft)
        sequence_layout.addWidget(VerticalSeparator())
        sequence_n_label = QLabel("Images per Sequence:")
        sequence_n_label.setFixedWidth(self.label_width)
        sequence_n_label.setToolTip("Max number of images in each sequence.")
        sequence_layout.addWidget(sequence_n_label)
        self.sequence_n = QLineEdit()
        self.sequence_n.setFixedWidth(self.edit_width)
        self.sequence_n.setText(str(self.cfg.SEQUENCE_N))
        self.sequence_n.textChanged.connect(self.update_sequence)
        sequence_layout.addWidget(self.sequence_n, alignment=Qt.AlignmentFlag.AlignLeft)
        sequence_layout.addStretch()
        layout.addLayout(sequence_layout)

        # VIDEOS
        video_layout = QHBoxLayout()
        smart_frames_label = QLabel("Smart Frames:")
        smart_frames_label.setToolTip("If enabled, only frames with ROIs will be processed for video files.")
        smart_frames_label.setFixedWidth(self.label_width)
        video_layout.addWidget(smart_frames_label)
        self.smart_frames = QComboBox()
        self.smart_frames.setFixedWidth(self.edit_width)
        self.smart_frames.addItem("Enabled")
        self.smart_frames.addItem("Disabled")
        self.smart_frames.setCurrentIndex(0 if self.cfg['SMART_FRAMES'] else 1)
        self.smart_frames.setToolTip("Enable or disable smart frame processing for video files.")
        self.smart_frames.currentTextChanged.connect(self.update_smart_frames)
        video_layout.addWidget(self.smart_frames, alignment=Qt.AlignmentFlag.AlignLeft)
        video_layout.addWidget(VerticalSeparator())
        self.video_fps_label = QLabel("Video FPS:")
        self.video_fps_label.setToolTip("Frames per second to analyze for quality.")
        self.video_fps_label.setFixedWidth(self.label_width)
        video_layout.addWidget(self.video_fps_label)
        self.video_fps = QLineEdit()
        self.video_fps.setFixedWidth(self.edit_width)
        self.video_fps.setText(str(self.cfg['VIDEO_FPS']))
        self.video_fps.textChanged.connect(self.update_video_fps)
        video_layout.addWidget(self.video_fps, alignment=Qt.AlignmentFlag.AlignLeft)
        video_layout.addStretch()
        layout.addLayout(video_layout)

        self.video_fps_label.setVisible(self.cfg['SMART_FRAMES'])
        self.video_fps.setVisible(self.cfg['SMART_FRAMES'])

        video_frames_layout = QHBoxLayout()
        video_n_frames_label = QLabel("Video Frames:")
        video_n_frames_label.setToolTip("Number of frames to extract from each video.")
        video_n_frames_label.setFixedWidth(self.label_width)
        video_frames_layout.addWidget(video_n_frames_label)
        self.n_frames = QLineEdit()
        self.n_frames.setFixedWidth(self.edit_width)
        self.n_frames.setText(str(self.cfg['N_FRAMES']))
        self.n_frames.textChanged.connect(self.update_n_frames)
        video_frames_layout.addWidget(self.n_frames, alignment=Qt.AlignmentFlag.AlignLeft)
        video_frames_layout.addStretch()
        layout.addLayout(video_frames_layout)

        # NUM MATCHES
        nummatches_layout = QHBoxLayout()
        nummatches_label = QLabel("Max # of Matches:")
        nummatches_label.setToolTip("Number of nearest neighbors to consider.")
        nummatches_label.setFixedWidth(self.label_width)
        nummatches_layout.addWidget(nummatches_label)
        self.nummatches = QLineEdit()
        self.nummatches.setFixedWidth(self.edit_width)
        self.nummatches.setText(str(self.cfg.KNN))
        nummatches_layout.addWidget(self.nummatches, alignment=Qt.AlignmentFlag.AlignLeft)
        self.nummatches.textChanged.connect(self.update_nummatches)
        layout.addLayout(nummatches_layout)

        # CUDA -----------------------------------------------------------------
        cuda_layout = QHBoxLayout()
        cuda_label = QLabel("Hardware Device:")
        cuda_label.setFixedWidth(self.label_width)
        cuda_layout.addWidget(cuda_label)
        providers = animl.get_onnx_device(quiet=True)
        self.device = QComboBox()
        self.device.setFixedWidth(self.edit_width)
        self.device.addItem("CPU")
        if "CUDAExecutionProvider" in providers:
            self.device.addItem("CUDA-enabled GPU")
        current_device = self.cfg.get('DEVICE', 'CPUExecutionProvider')
        self.device.setCurrentText(self.DEVICE_OPTIONS.get(current_device, "CPU"))
        self.device.setToolTip("Select the hardware device for running models.")
        self.device.currentTextChanged.connect(self.change_device)
        cuda_layout.addWidget(self.device, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(cuda_layout)

        # MPDB KEY -------------------------------------------------------------
        mpdbkey_layout = QHBoxLayout()
        mpdbkey_label = QLabel("Database Key:")
        mpdbkey_label.setToolTip("Unique identifier for the current database.")
        mpdbkey_label.setFixedWidth(self.label_width)
        mpdbkey_layout.addWidget(mpdbkey_label)
        mpdbkey = self.mpDB.validate()
        self.mpdbkey_valid = QLabel(f"{mpdbkey}")
        self.mpdbkey_valid.setStyleSheet("color: red;" if not mpdbkey else "")
        mpdbkey_layout.addWidget(self.mpdbkey_valid, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(mpdbkey_layout)

        # Advanced -------------------------------------------------------------
        self.separator = HorizontalSeparator()
        self.separator.hide()
        layout.addWidget(self.separator)

        command_layout = QHBoxLayout()
        self.advanced_command = QLabel("Database Command:")
        self.advanced_command.setFixedWidth(self.label_width)
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
        # Advanced Button
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
        """Show/hide advanced options."""
        visible = self.advanced_command.isVisible()
        self.separator.setVisible(not visible)
        self.advanced_command.setVisible(not visible)
        self.command_line.setVisible(not visible)
        self.button_command.setVisible(not visible)

    def command(self):
        """Execute custom command on database."""
        new_cmd = self.command_line.text()
        self.mpDB._command(new_cmd, quiet=False)

    def refresh(self):
        """Refresh the config popup with updated values."""
        self.home_dir.setText(str(self.cfg.HOME_DIR))
        reid_path = get_path(self.ml_dir, self.cfg.REID_KEY)
        self.visualizer_model.setText(str(reid_path))
        self.nummatches.setText(str(self.cfg.KNN))
        self.sequence_duration.setText(str(self.cfg.SEQUENCE_DURATION))
        self.sequence_n.setText(str(self.cfg.SEQUENCE_N))
        self.mpdbkey_valid.setText(f"{self.mpDB.validate()}")

    def set_home_dir(self):
        """Change Home directory"""
        new_project = QFileDialog.getExistingDirectory(self, "Get Project Folder",
                                                       os.path.expanduser('~'),)
        if new_project:
            valid = self.parent.change_project(new_project)
            if not valid:
                return
            # Update local references to the new project's database and config
            self.mpDB = self.parent.mpDB
            self.cfg = self.parent.cfg
            self.refresh()

    def new_project(self):
        """Create new project directory"""
        parent_dir = QFileDialog.getExistingDirectory(self, "Select new Project location",
                                                      os.path.expanduser('~'),)
        if parent_dir:
            self.parent.new_project(parent_dir)
            # Update local references to the new project's database and config
            self.mpDB = self.parent.mpDB
            self.cfg = self.parent.cfg
            self.refresh()

    def set_visualizer_model(self):
        """
        Set visualizer model for PairX
        Currently disabled
        """
        new_model = QFileDialog.getOpenFileName(self, "Select Re-ID Model",
                                                os.path.expanduser(self.ml_dir), "Model Files (*.pt *.pth *.bin)")
        if new_model and new_model[0]:
            if is_valid_reid_model(Path(new_model[0]).stem):
                # Update config
                self.visualizer_model.setText(new_model[0])
                self.cfg['REID_KEY'] = str(Path(new_model[0]).stem)
                # save changes to yml
                self.logger.info(f"Re-ID model updated to {self.cfg['REID_KEY']}")
                config.update(self.cfg)
            else:
                dialog = AlertPopup(self, prompt="Model not recognized. Please select a valid Re-ID model.")
                dialog.exec()
                del dialog

    def update_nummatches(self):
        """Update max number of matches setting"""
        try:
            nummatches = int(self.nummatches.text())
            if nummatches > 0:
                self.cfg['KNN'] = nummatches
                self.logger.info(f"Max number of matches updated to {nummatches}")
                config.update(self.cfg)
        except ValueError:
            pass

    def update_sequence(self):
        """Update sequence settings"""
        try:
            duration = int(self.sequence_duration.text())
            n = int(self.sequence_n.text())
            if duration > 0:
                self.cfg['SEQUENCE_DURATION'] = duration
                self.cfg['SEQUENCE_N'] = n
                self.logger.info(f"Sequence settings updated: duration={duration}, n={n}")
                config.update(self.cfg)
        except ValueError:
            pass

    def update_smart_frames(self):
        """Update smart frames setting"""
        self.cfg['SMART_FRAMES'] = True if self.smart_frames.currentText() == "Enabled" else False
        self.video_fps_label.setVisible(self.cfg['SMART_FRAMES'])
        self.video_fps.setVisible(self.cfg['SMART_FRAMES'])
        config.update(self.cfg)

    def update_video_fps(self):
        """Update video fps setting"""
        try:
            fps = int(self.video_fps.text())
            if fps > 0:
                self.cfg['VIDEO_FPS'] = fps
                config.update(self.cfg)
        except ValueError:
            pass

    def update_n_frames(self):
        """Update number of frames setting"""
        try:
            n_frames = int(self.n_frames.text())
            if n_frames > 0:
                self.cfg['N_FRAMES'] = n_frames
                config.update(self.cfg)
        except ValueError:
            pass

    def change_device(self):
        self.logger.info(f"Device changed to {self.device.currentText()}")
        """Change hardware device for running models"""
        selected_device = self.device.currentText()
        if selected_device == "CPU":
            self.cfg.update({'DEVICE': "CPUExecutionProvider"})
        elif selected_device == "CUDA-enabled GPU":
            self.cfg['DEVICE'] = "CUDAExecutionProvider"
        self.logger.info(f"Device changed to {self.cfg['DEVICE']}")
        config.update(self.cfg)

    def edit_uploads(self):
        """Open the upload directories manager popup."""
        dialog = UploadManagerPopup(self)
        dialog.exec()
        del dialog
