"""
View log popup

"""
import logging
from pathlib import Path

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
                             QPushButton, QLabel)
from PyQt6.QtGui import QDesktopServices, QFontDatabase
from PyQt6.QtCore import Qt, QUrl

# only show the end of large logs so the dialog opens quickly
MAX_BYTES = 1024 * 1024


def get_log_path():
    """Path of the file the root logger writes to, None if there isn't one"""
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.FileHandler):
            return Path(handler.baseFilename)
    return None


class LogPopup(QDialog):
    """
    Popup to view the application log
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.log_path = get_log_path()
        self.setMinimumSize(900, 500)
        self.setWindowTitle('View Log')

        layout = QVBoxLayout()
        self.path_label = QLabel(str(self.log_path) if self.log_path else "No log file")
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.path_label)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.text_edit.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        layout.addWidget(self.text_edit)

        buttons = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.display_log)
        self.folder_button = QPushButton("Open Log Folder")
        self.folder_button.clicked.connect(self.open_folder)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        buttons.addWidget(self.refresh_button)
        buttons.addWidget(self.folder_button)
        buttons.addStretch()
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)

        self.setLayout(layout)
        self.folder_button.setEnabled(self.log_path is not None)
        self.display_log()

    def display_log(self):
        """Show the log (its last MAX_BYTES if larger), scrolled to the newest entries"""
        if self.log_path is None:
            self.text_edit.setPlainText("Logging to a file is not set up.")
            return
        # flush so the view includes everything logged so far
        for handler in logging.getLogger().handlers:
            handler.flush()
        try:
            with open(self.log_path, "rb") as file:
                file.seek(0, 2)
                size = file.tell()
                file.seek(max(0, size - MAX_BYTES))
                data = file.read()
        except OSError as e:
            self.text_edit.setPlainText(f"Could not read {self.log_path}: {e}")
            return
        text = data.decode("utf-8", errors="replace")
        if size > MAX_BYTES:
            # drop the partial first line
            text = "[earlier entries not shown]\n" + text.split("\n", 1)[-1]
        self.text_edit.setPlainText(text)
        scrollbar = self.text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def open_folder(self):
        """Open the folder containing the log in the system file browser"""
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.log_path.parent)))
