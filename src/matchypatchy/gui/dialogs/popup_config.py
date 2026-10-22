'''
Popup to add or edit config settings
'''
import logging
import os
from pathlib import Path
import animl

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFileDialog, QComboBox, QInputDialog,
                             QPushButton, QLineEdit, QLabel, QDialogButtonBox)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from matchypatchy import config
from matchypatchy.gui.dialogs.popup_alert import AlertPopup
from matchypatchy.gui.dialogs.popup_uploads import UploadManagerPopup
from matchypatchy.gui.widgets.gui_assets import HorizontalSeparator
from matchypatchy.threads.model_download_thread import get_path, is_valid_reid_model
from matchypatchy.project import UsesProject


logger = logging.getLogger(__name__)


class ConfigPopup(UsesProject, QDialog):
    """
    Popup for adding or editing configuration settings.
    """

    ICON_PENCIL = str(config.asset_path("graphics/fluent_pencil_icon.png"))
    DEVICE_OPTIONS = {"CPUExecutionProvider": "CPU", "CUDAExecutionProvider": "CUDA-enabled GPU"}

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Edit Config")
        self.setMinimumWidth(600)
        self.project = parent.project
        self.ml_dir = Path(self.cfg.ML_DIR)
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
        button_home_dir.setToolTip("Open another project folder")
        button_home_dir.clicked.connect(self.set_home_dir)
        directory_layout.addWidget(button_home_dir)
        # Add Button
        button_add = QPushButton("+")
        button_add.setToolTip("Create a new project")
        button_add.clicked.connect(self.new_project)
        button_add.setMaximumHeight(30)
        button_add.setFixedWidth(30)
        directory_layout.addWidget(button_add)
        layout.addLayout(directory_layout)

        # UPDATE UPLOADS DIRECTORIES -------------------------------------------
        uploads_layout = QHBoxLayout()
        self.button_uploads = QPushButton("Edit Source Directories")
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

        # SETTINGS, label and field pairs in two aligned columns -----------
        grid = QGridLayout()
        grid.setColumnMinimumWidth(2, 20)  # gap between the two columns
        grid.setColumnStretch(4, 1)

        def add_setting(row, column, text, tooltip, field):
            """Put a label and its field in the grid, column 0 or 1 of label/field pairs"""
            label = QLabel(text)
            label.setToolTip(tooltip)
            grid.addWidget(label, row, column * 3)
            field.setFixedWidth(self.edit_width)
            grid.addWidget(field, row, column * 3 + 1)
            return label

        # Sequence
        self.sequence_duration = QLineEdit()
        self.sequence_duration.setText(str(self.cfg.SEQUENCE_DURATION))
        self.sequence_duration.textChanged.connect(self.update_sequence)
        add_setting(0, 0, "Sequence Length (s):", "Maximum duration of the sequence in seconds.",
                    self.sequence_duration)
        self.sequence_n = QLineEdit()
        self.sequence_n.setText(str(self.cfg.SEQUENCE_N))
        self.sequence_n.textChanged.connect(self.update_sequence)
        add_setting(0, 1, "Images per Sequence:", "Max number of images in each sequence.", self.sequence_n)

        # VIDEOS
        self.smart_frames = QComboBox()
        self.smart_frames.addItem("Enabled")
        self.smart_frames.addItem("Disabled")
        self.smart_frames.setCurrentIndex(0 if self.cfg.SMART_FRAMES else 1)
        self.smart_frames.setToolTip("Enable or disable smart frame processing for video files.")
        self.smart_frames.currentTextChanged.connect(self.update_smart_frames)
        add_setting(1, 0, "Smart Frames:", "If enabled, only frames with ROIs will be processed for video files.",
                    self.smart_frames)
        self.video_fps = QLineEdit()
        self.video_fps.setText(str(self.cfg.VIDEO_FPS))
        self.video_fps.textChanged.connect(self.update_video_fps)
        self.video_fps_label = add_setting(1, 1, "Video FPS:", "Frames per second to analyze for quality.",
                                           self.video_fps)
        self.video_fps_label.setVisible(self.cfg.SMART_FRAMES)
        self.video_fps.setVisible(self.cfg.SMART_FRAMES)

        self.n_frames = QLineEdit()
        self.n_frames.setText(str(self.cfg.N_FRAMES))
        self.n_frames.textChanged.connect(self.update_n_frames)
        add_setting(2, 0, "Video Frames:", "Number of frames to extract from each video.", self.n_frames)

        # NUM MATCHES
        self.nummatches = QLineEdit()
        self.nummatches.setText(str(self.cfg.KNN))
        self.nummatches.textChanged.connect(self.update_nummatches)
        add_setting(3, 0, "Max # of Matches:", "Number of nearest neighbors to consider.", self.nummatches)

        # CUDA -----------------------------------------------------------------
        providers = animl.get_onnx_device(quiet=True)
        self.device = QComboBox()
        self.device.addItem("CPU")
        if "CUDAExecutionProvider" in providers:
            self.device.addItem("CUDA-enabled GPU")
        current_device = self.cfg.DEVICE
        self.device.setCurrentText(self.DEVICE_OPTIONS.get(current_device, "CPU"))
        self.device.setToolTip("Select the hardware device for running models.")
        self.device.currentTextChanged.connect(self.change_device)
        add_setting(4, 0, "Hardware Device:", "", self.device)

        # MPDB KEY -------------------------------------------------------------
        mpdbkey = self.mpDB.validate()
        self.mpdbkey_valid = QLabel(f"{mpdbkey}")
        self.mpdbkey_valid.setStyleSheet("color: red;" if not mpdbkey else "")
        mpdbkey_label = QLabel("Database Key:")
        mpdbkey_label.setToolTip("Unique identifier for the current database.")
        grid.addWidget(mpdbkey_label, 5, 0)
        grid.addWidget(self.mpdbkey_valid, 5, 1)
        layout.addLayout(grid)

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
        # Save/Cancel Buttons: settings are only written on Save
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        # values to restore on Cancel; fields edit the shared config in memory, OK saves it
        self._original = self._settings()

    # settings this dialog edits
    SETTINGS = ("KNN", "SEQUENCE_DURATION", "SEQUENCE_N", "SMART_FRAMES",
                "VIDEO_FPS", "N_FRAMES", "DEVICE", "REID_KEY")

    def _settings(self):
        """Current values of the settings this dialog edits"""
        return {name: getattr(self.cfg, name) for name in self.SETTINGS}

    def accept(self):
        """Save: write the settings to the project's config file"""
        self.cfg.save()
        logger.info("Configuration saved")
        super().accept()

    def reject(self):
        """Cancel: put back the settings as they were when the dialog opened"""
        for name, value in self._original.items():
            setattr(self.cfg, name, value)
        super().reject()

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
        """Show the current project's values, eg. after switching project"""
        self.ml_dir = Path(self.cfg.ML_DIR)
        fields = (self.home_dir, self.visualizer_model, self.nummatches, self.sequence_duration,
                  self.sequence_n, self.smart_frames, self.video_fps, self.n_frames, self.device)
        # filling the fields must not trigger their save handlers
        for field in fields:
            field.blockSignals(True)
        self.home_dir.setText(str(self.cfg.HOME_DIR))
        reid_path = get_path(self.ml_dir, self.cfg.REID_KEY)
        self.visualizer_model.setText(str(reid_path))
        self.nummatches.setText(str(self.cfg.KNN))
        self.sequence_duration.setText(str(self.cfg.SEQUENCE_DURATION))
        self.sequence_n.setText(str(self.cfg.SEQUENCE_N))
        self.smart_frames.setCurrentIndex(0 if self.cfg.SMART_FRAMES else 1)
        self.video_fps.setText(str(self.cfg.VIDEO_FPS))
        self.n_frames.setText(str(self.cfg.N_FRAMES))
        self.device.setCurrentText(self.DEVICE_OPTIONS.get(self.cfg.DEVICE, "CPU"))
        for field in fields:
            field.blockSignals(False)
        self.video_fps_label.setVisible(self.cfg.SMART_FRAMES)
        self.video_fps.setVisible(self.cfg.SMART_FRAMES)
        mpdbkey = self.mpDB.validate()
        self.mpdbkey_valid.setText(f"{mpdbkey}")
        self.mpdbkey_valid.setStyleSheet("color: red;" if not mpdbkey else "")

    def set_home_dir(self):
        """Change Home directory"""
        new_project = QFileDialog.getExistingDirectory(self, "Get Project Folder",
                                                       os.path.expanduser('~'),)
        if new_project:
            valid = self.parent.change_project(new_project)
            if not valid:
                return
            self._original = self._settings()
            self.refresh()

    def new_project(self):
        """Create new project directory"""
        parent_dir = QFileDialog.getExistingDirectory(self, "Select new Project location",
                                                      os.path.expanduser('~'),)
        if not parent_dir:
            return  # user cancelled

        project_name, ok = QInputDialog.getText(self, "New Project", "Project name:")
        if not ok or not project_name.strip():
            return  # user cancelled or entered nothing

        project_name = project_name.strip()

        if parent_dir and project_name:
            new_project_path = Path(parent_dir) / project_name
            self.parent.new_project(new_project_path)
            self._original = self._settings()
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
                self.cfg.REID_KEY = str(Path(new_model[0]).stem)
                logger.info(f"Re-ID model updated to {self.cfg.REID_KEY}")
            else:
                dialog = AlertPopup(self, prompt="Model not recognized. Please select a valid Re-ID model.")
                dialog.exec()
                del dialog

    def update_nummatches(self):
        """Update max number of matches setting"""
        try:
            nummatches = int(self.nummatches.text())
            if nummatches > 0:
                self.cfg.KNN = nummatches
                logger.info(f"Max number of matches updated to {nummatches}")
        except ValueError:
            pass

    def update_sequence(self):
        """Update sequence settings"""
        try:
            duration = int(self.sequence_duration.text())
            n = int(self.sequence_n.text())
            if duration > 0:
                self.cfg.SEQUENCE_DURATION = duration
                self.cfg.SEQUENCE_N = n
                logger.info(f"Sequence settings updated: duration={duration}, n={n}")
        except ValueError:
            pass

    def update_smart_frames(self):
        """Update smart frames setting"""
        self.cfg.SMART_FRAMES = True if self.smart_frames.currentText() == "Enabled" else False
        self.video_fps_label.setVisible(self.cfg.SMART_FRAMES)
        self.video_fps.setVisible(self.cfg.SMART_FRAMES)

    def update_video_fps(self):
        """Update video fps setting"""
        try:
            fps = int(self.video_fps.text())
            if fps > 0:
                self.cfg.VIDEO_FPS = fps
        except ValueError:
            pass

    def update_n_frames(self):
        """Update number of frames setting"""
        try:
            n_frames = int(self.n_frames.text())
            if n_frames > 0:
                self.cfg.N_FRAMES = n_frames
        except ValueError:
            pass

    def change_device(self):
        """Change hardware device for running models between CPU and CUDA-enabled GPU"""
        logger.info(f"Device changed to {self.device.currentText()}")
        """Change hardware device for running models"""
        selected_device = self.device.currentText()
        if selected_device == "CPU":
            self.cfg.DEVICE = "CPUExecutionProvider"
        elif selected_device == "CUDA-enabled GPU":
            self.cfg.DEVICE = "CUDAExecutionProvider"
        logger.info(f"Device changed to {self.cfg.DEVICE}")

    def edit_uploads(self):
        """Open the upload directories manager popup."""
        dialog = UploadManagerPopup(self)
        dialog.exec()
        del dialog
