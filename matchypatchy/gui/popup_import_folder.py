"""
Popup for Importing a Manifest
"""
import os
from pathlib import Path
import pandas as pd

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QProgressBar,
                             QComboBox, QDialogButtonBox, QLabel)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from matchypatchy.gui.popup_alert import AlertPopup

from animl.file_management import build_file_manifest


columns=["filepath", "timestamp", 'site_id', 'sequence_id', "external_id", 'comment',
         "viewpoint", "species_id", "individual_id"]

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

        # Site
        self.site = QComboBox()
        self.site.hide()
        layout.addWidget(self.site)

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
        self.label.setText("Select a level in the directory hierarchy that corresponds to site, if available:")
        self.site.show()
        self.buttonBox.show()

        example = self.data.loc[0,'FilePath']
        # get potential site 
        file_tree = ['None'] + example.split(os.sep)
        self.site.addItems(file_tree)

    #. 4. Import manifest into media table
    def import_manifest(self):
        """
        Media entry (id, filepath, ext, timestamp, comment, site_id)
        """
        # assert bbox in manifest.columns
        self.progress_bar.setRange(0, len(self.data))
        self.progress_bar.show()

        site_level = 0 if self.site.currentIndex()==0 else self.site.currentIndex() - 1

        print(f"Adding {len(self.data)} files to Database")

        self.import_thread = FolderImportThread(self.mpDB, self.active_survey, self.data, site_level)
        self.import_thread.progress_update.connect(self.progress_bar.setValue)
        self.import_thread.finished.connect(self.accept)
        self.import_thread.start()


class BuildManifestThread(QThread):
    """
    Thread for launching 
    """
    manifest = pyqtSignal(pd.DataFrame)

    def __init__(self, directory):
        super().__init__()
        self.directory = directory

    def run(self):
        self.data = build_file_manifest(self.directory)
        self.manifest.emit(self.data)


class FolderImportThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    
    def __init__(self, mpDB, active_survey, data, site_level):
        super().__init__()
        self.mpDB = mpDB
        self.active_survey = active_survey
        self.data = data
        self.site_level = site_level
        self.default_site = None
        self.animl_conversion = {"filepath": "FilePath",
                                "timestamp": "DateTime"}    

    def run(self):
        for i, file in self.data.iterrows():

            filepath = file[self.animl_conversion['filepath']]
            timestamp = file[self.animl_conversion['timestamp']]

            # check to see if file exists 
            if not os.path.exists(filepath):
                print(f"Warning, file {filepath} does not exist")
                continue

            # get file extension
            _, ext = os.path.splitext(os.path.basename(filepath))
            
            # get remaining information
            if self.site_level > 0:
                site_name = os.path.normpath(filepath).split(os.sep)[self.site_level]
                try:
                    site_id = self.mpDB.select("site", columns='id', row_cond=f'name="{site_name}"')[0][0]
                except IndexError:
                    site_id = self.mpDB.add_site(str(site_name), None, None, int(self.active_survey[0]))
            else:
                if not self.default_site:
                    self.default_site = self.mpDB.add_site("None", None, None, int(self.active_survey[0]))
                site_id = self.default_site

            # insert into table, force type
            media_id = self.mpDB.add_media(filepath, ext, 
                                           str(timestamp), 
                                           int(site_id),
                                           sequence_id=None, 
                                           external_id=None,
                                           comment=None)

            self.progress_update.emit(i)

        # finished adding media
        self.finished.emit()
