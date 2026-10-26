'''
Popup to add or edit config settings
'''
import logging
import os
from pathlib import Path
import animl

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFileDialog, QComboBox, QInputDialog,
                             QPushButton, QLineEdit, QLabel, QDialogButtonBox, QSpinBox)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from matchypatchy import config
from matchypatchy.gui.dialogs.popup_alert import AlertPopup
from matchypatchy.gui.dialogs.popup_uploads import UploadManagerPopup
from matchypatchy.gui.widgets.gui_assets import HorizontalSeparator, VerticalSeparator
from matchypatchy.models import get_path, is_valid_reid_model
from matchypatchy.project import UsesProject


logger = logging.getLogger(__name__)


class ConfigPopup(UsesProject, QDialog):
    """
    Popup for adding or editing configuration settings.
    """

    ICON_PENCIL = str(config.resource_path("assets/graphics/fluent_pencil_icon.png"))
    DEVICE_OPTIONS = {"CPUExecutionProvider": "CPU", "CUDAExecutionProvider": "CUDA-enabled GPU"}
    FONT_SIZE_MIN = 8
    FONT_SIZE_MAX = 24

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
        self.button_uploads.setFixedWidth(self.label_width)
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
        self.smart_frames.setCurrentIndex(0 if self.cfg.SMART_FRAMES else 1)
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
        self.video_fps.setText(str(self.cfg.VIDEO_FPS))
        self.video_fps.textChanged.connect(self.update_video_fps)
        video_layout.addWidget(self.video_fps, alignment=Qt.AlignmentFlag.AlignLeft)
        video_layout.addStretch()
        layout.addLayout(video_layout)

        self.video_fps_label.setVisible(self.cfg.SMART_FRAMES)
        self.video_fps.setVisible(self.cfg.SMART_FRAMES)

        video_frames_layout = QHBoxLayout()
        video_n_frames_label = QLabel("Video Frames:")
        video_n_frames_label.setToolTip("Number of frames to extract from each video.")
        video_n_frames_label.setFixedWidth(self.label_width)
        video_frames_layout.addWidget(video_n_frames_label)
        self.n_frames = QLineEdit()
        self.n_frames.setFixedWidth(self.edit_width)
        self.n_frames.setText(str(self.cfg.N_FRAMES))
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
        current_device = self.cfg.DEVICE
        self.device.setCurrentText(self.DEVICE_OPTIONS.get(current_device, "CPU"))
        self.device.setToolTip("Select the hardware device for running models.")
        self.device.currentTextChanged.connect(self.change_device)
        cuda_layout.addWidget(self.device, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(cuda_layout)

        # FONT SIZE ------------------------------------------------------------
        font_layout = QHBoxLayout()
        font_label = QLabel("Font Size:")
        font_label.setToolTip(f"Default text size in points, for all projects. "
                              f"The system's size is {self.parent.system_font_size} pt.")
        font_label.setFixedWidth(self.label_width)
        font_layout.addWidget(font_label)
        self.font_size = QSpinBox()
        self.font_size.setFixedWidth(self.edit_width)
        self.font_size.setRange(self.FONT_SIZE_MIN, self.FONT_SIZE_MAX)
        self.font_size.setSuffix(" pt")
        self._original_font_size = self.parent.font_size()
        self.font_size.setValue(self._original_font_size)
        self.font_size.valueChanged.connect(self.parent.apply_font_size)
        font_layout.addWidget(self.font_size, alignment=Qt.AlignmentFlag.AlignLeft)
        button_font_reset = QPushButton("System Default")
        button_font_reset.setToolTip("Go back to the system's text size.")
        button_font_reset.clicked.connect(lambda: self.font_size.setValue(self.parent.system_font_size))
        font_layout.addWidget(button_font_reset, alignment=Qt.AlignmentFlag.AlignLeft)
        font_layout.addStretch()
        layout.addLayout(font_layout)

        # THEME ----------------------------------------------------------------
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme:")
        theme_label.setToolTip("Light or dark colors for all projects. System follows the computer's setting.")
        theme_label.setFixedWidth(self.label_width)
        theme_layout.addWidget(theme_label)
        self.theme = QComboBox()
        self.theme.setFixedWidth(self.edit_width)
        self.theme.addItems(list(self.parent.THEMES))
        self._original_theme = self.parent.theme()
        self.theme.setCurrentText(self._original_theme)
        self.theme.currentTextChanged.connect(self.parent.apply_theme)
        theme_layout.addWidget(self.theme, alignment=Qt.AlignmentFlag.AlignLeft)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)

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
    SETTINGS = ("KNN", "SEQUENCE_DURATION", "SMART_FRAMES",
                "VIDEO_FPS", "N_FRAMES", "DEVICE", "REID_KEY")

    def _settings(self):
        """Current values of the settings this dialog edits"""
        return {name: getattr(self.cfg, name) for name in self.SETTINGS}

    def accept(self):
        """Save: write the settings to the project's config file, and the font size and theme to the app's settings"""
        self.cfg.save()
        self.parent.save_font_size(self.font_size.value())
        self.parent.save_theme(self.theme.currentText())
        logger.info("Configuration saved")
        super().accept()

    def reject(self):
        """Cancel: put back the settings, font size and theme as they were when the dialog opened"""
        for name, value in self._original.items():
            setattr(self.cfg, name, value)
        self.parent.apply_font_size(self._original_font_size)
        self.parent.apply_theme(self._original_theme)
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
                  self.smart_frames, self.video_fps, self.n_frames, self.device)
        # filling the fields must not trigger their save handlers
        for field in fields:
            field.blockSignals(True)
        self.home_dir.setText(str(self.cfg.HOME_DIR))
        reid_path = get_path(self.ml_dir, self.cfg.REID_KEY)
        self.visualizer_model.setText(str(reid_path))
        self.nummatches.setText(str(self.cfg.KNN))
        self.sequence_duration.setText(str(self.cfg.SEQUENCE_DURATION))
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
            if duration > 0:
                self.cfg.SEQUENCE_DURATION = duration
                logger.info(f"Sequence settings updated: duration={duration}")
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
