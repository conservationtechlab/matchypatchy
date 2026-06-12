"""
Popup for Importing a Manifest
"""
import logging
from pathlib import Path
import pandas as pd

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QProgressBar,
                             QDialogButtonBox, QLabel)
from PyQt6.QtCore import Qt

from matchypatchy.gui.dialogs.popup_alert import AlertPopup
from matchypatchy.gui.widgets.gui_assets import ComboBoxSeparator

from matchypatchy.threads.animl_thread import BuildManifestThread
from matchypatchy.threads.import_thread import FolderImportThread


class ImportFolderPopup(QDialog):
    def __init__(self, parent, directory):
        super().__init__(parent)
        self.mpDB = parent.mpDB
        self.active_survey = parent.active_survey
        self.timezone = self.mpDB.select_join("survey", "region", "survey.region_id=region.id",
                                        columns="region.timezone",
                                        row_cond=f"survey.id={self.active_survey[0]}")[0][0][0]
        self.directory = Path(directory)
        self.data = pd.DataFrame()

        self.setWindowTitle('Import from Folder')
        layout = QVBoxLayout()

        # Create a label
        self.station_label = QLabel("Searching directory...")
        layout.addWidget(self.station_label)
        layout.addSpacing(5)

        # station
        self.station = ComboBoxSeparator()
        self.station.hide()
        layout.addWidget(self.station)
        self.station.addItems(['None'])
        self.station.add_separator()

        layout.addSpacing(10)

        # camera
        self.camera_label = QLabel("")
        layout.addWidget(self.camera_label)
        self.camera = ComboBoxSeparator()
        self.camera.hide()
        layout.addWidget(self.camera)
        self.camera.addItems(['None'])
        self.camera.add_separator()

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
        """Start thread to build manifest from folder"""
        # show progress bar
        self.progress_bar.setRange(0, 0)
        self.build_thread = BuildManifestThread(self.directory, self.timezone)
        self.build_thread.manifest.connect(self.get_manifest)
        self.build_thread.start()

    # 2. Receive data from thread, check if valid
    def get_manifest(self, manifest):
        """Receive manifest from thread, proceed or alert no images found"""
        self.progress_bar.hide()
        self.data = manifest

        if not self.data.empty:
            self.get_options()
        else:
            dialog = AlertPopup(self, "No images found! Choose another directory.", title="Alert")
            if dialog.exec():
                self.reject()

    # 3. Offer Station Options
    def get_options(self):
        """Offer options for station and cameralevel selection"""
        self.station_label.setText("Select directory level that corresponds to STATION, if available:")
        self.station.show()
  
        self.camera_label.setText("Select directory level that corresponds to CAMERA, if available:")
        self.camera.show()

        self.buttonBox.show()

        # get potential station
        example = self.data.loc[0, 'filepath']
        self.station.addItems(list(Path(example).parts)[1:])
        self.camera.addItems(list(Path(example).parts)[1:])

    # 4. Import manifest into media table
    def import_manifest(self):
        """
        Media entry (id, filepath, ext, timestamp, comment, station_id, camera_id)
        """
        # assert bbox in manifest.columns
        self.progress_bar.setRange(0, len(self.data))
        self.progress_bar.show()
        self.buttonBox.setDisabled(True)

        station_level = 0 if self.station.currentIndex() == 0 else self.station.currentIndex() - 1
        camera_level = 0 if self.camera.currentIndex() == 0 else self.camera.currentIndex() - 1

        logging.info(f"Adding {len(self.data)} files to Database")

        self.import_thread = FolderImportThread(self.mpDB, self.active_survey, self.data, station_level, camera_level)
        self.rejected.connect(self.import_thread.requestInterruption)
        self.import_thread.progress_update.connect(self.progress_bar.setValue)
        self.import_thread.finished.connect(self.accept)
        self.import_thread.start()
