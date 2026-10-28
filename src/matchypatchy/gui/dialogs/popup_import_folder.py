"""
Popup for Importing a Manifest
"""
import logging
from pathlib import Path
import pandas as pd

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QProgressBar,
                             QDialogButtonBox, QLabel)
from PyQt6.QtCore import Qt

from matchypatchy.database.location import survey_timezone
from matchypatchy.gui.widgets.gui_assets import ComboBoxSeparator

from matchypatchy.threads.animl_thread import BuildManifestThread
from matchypatchy.threads.import_thread import FolderImportThread
from matchypatchy.project import UsesProject


logger = logging.getLogger(__name__)


class ImportFolderPopup(UsesProject, QDialog):
    """
    Popup for importing data from a folder.
    """

    def __init__(self, parent, directory):
        super().__init__(parent)
        self.project = parent.project
        self.active_survey = parent.active_survey
        self.timezone = self._survey_timezone(self.active_survey[0])
        self.directory = Path(directory)
        self.data = pd.DataFrame()
        self.import_thread = None
        # set when the directory has no images, so the caller can ask for another one
        self.no_images = False
        self._closed = False

        self.setWindowTitle(f'Importing into "{self.active_survey[1]}"')
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

    def _survey_timezone(self, survey_id):
        """Timezone of the survey's region, None (local time) if it has no region"""
        return survey_timezone(self.mpDB, survey_id)

    def reject(self):
        """Cancel: stop a running import and close when it has finished"""
        if self.import_thread is not None and self.import_thread.isRunning():
            self.import_thread.requestInterruption()
            # finished -> accept closes the popup once the thread has stopped
            return
        self._closed = True
        super().reject()

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
        """Receive manifest from thread, proceed or report no images found"""
        # the user cancelled while the directory was being searched
        if self._closed:
            return
        self.progress_bar.hide()
        self.data = manifest

        if not self.data.empty:
            self.get_options()
        else:
            # OK closes and asks for another directory, Cancel just closes
            self.station_label.setText("No images found! Choose another directory.")
            self.buttonBox.accepted.disconnect(self.import_manifest)
            self.buttonBox.accepted.connect(self.choose_another_directory)
            self.buttonBox.show()

    def choose_another_directory(self):
        """Close and flag the caller to reopen the directory picker"""
        self.no_images = True
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

        logger.info(f"Adding {len(self.data)} files to Database")

        self.import_thread = FolderImportThread(self, self.active_survey, self.data, station_level, camera_level)
        self.import_thread.progress_update.connect(self.progress_bar.setValue)
        self.import_thread.import_failed.connect(self.show_import_failed)
        self.import_thread.finished.connect(self.accept)
        self.import_thread.start()

    def show_import_failed(self, message):
        """Show a fatal import error in the popup instead of closing it"""
        # QThread.finished still fires when run() returns, keep the popup open
        self.import_thread.finished.disconnect(self.accept)
        self.progress_bar.hide()
        self.station.hide()
        self.camera.hide()
        self.camera_label.hide()
        self.station_label.setText(f"Import failed, some files may have been partially imported. "
                                   f"View the log for details.\n{message}")
        self.buttonBox.accepted.disconnect(self.import_manifest)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.setDisabled(False)
