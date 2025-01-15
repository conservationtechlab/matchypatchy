"""
Popup for Importing a Manifest
"""
import os
from pathlib import Path
import pandas as pd

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QProgressBar,
                             QComboBox, QDialogButtonBox, QLabel)
from PyQt6.QtCore import Qt

from matchypatchy.gui.popup_alert import AlertPopup

from matchypatchy.algo.animl_thread import BuildManifestThread
from matchypatchy.algo.import_thread import FolderImportThread


class ImportFolderPopup(QDialog):
    def __init__(self, parent, directory):
        super().__init__(parent)
        self.mpDB = parent.mpDB
        self.active_survey = parent.active_survey
        self.directory = Path(directory)
        self.data = pd.DataFrame()

        self.setWindowTitle('Import from Folder')
        layout = QVBoxLayout()

        # Create a label
        self.label = QLabel("Searching directory...")
        layout.addWidget(self.label)
        layout.addSpacing(5)

        # station
        self.station = QComboBox()
        self.station.hide()
        layout.addWidget(self.station)

        # Ok/Cancel
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.buttonBox, alignment=Qt.AlignmentFlag.AlignCenter)
        self.buttonBox.accepted.connect(self.import_manifest)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.hide()

        # Progress Bar (hidden at start)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

        # build manifest
        self.build_manifest()

    # 1. Run Thread on entry
    def build_manifest(self):
        # show progress bar
        self.progress_bar.setRange(0, 0)
        self.build_thread = BuildManifestThread(self.directory)
        self.build_thread.manifest.connect(self.get_manifest)
        self.build_thread.start()

    # 2. Receive data from thread, check if valid
    def get_manifest(self, manifest):
        self.progress_bar.hide()
        self.data = manifest

        if not self.data.empty:
            self.get_options()
        else:
            dialog = AlertPopup(self, "No images found! Choose another directory.", title="Alert")
            if dialog.exec():
                self.reject()

    # 3. Offer
    def get_options(self):
        self.label.setText("Select a level in the directory hierarchy that corresponds to station, if available:")
        self.station.show()
        self.buttonBox.show()

        example = self.data.loc[0, 'FilePath']
        # get potential station
        file_tree = ['None'] + example.split(os.sep)
        self.station.addItems(file_tree)

    # 4. Import manifest into media table
    def import_manifest(self):
        """
        Media entry (id, filepath, ext, timestamp, comment, station_id)
        """
        # assert bbox in manifest.columns
        self.progress_bar.setRange(0, len(self.data))
        self.progress_bar.show()

        station_level = 0 if self.station.currentIndex() == 0 else self.station.currentIndex() - 1

        print(f"Adding {len(self.data)} files to Database")

        self.import_thread = FolderImportThread(self.mpDB, self.active_survey, self.data, station_level)
        self.import_thread.progress_update.connect(self.progress_bar.setValue)
        self.import_thread.finished.connect(self.accept)
        self.import_thread.start()
