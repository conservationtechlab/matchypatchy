"""
Popup for Importing a Manifest
"""
import os
import pandas as pd

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QProgressBar,
                             QComboBox, QDialogButtonBox, QLabel)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from .popup_alert import AlertPopup

from animl.file_management import build_file_manifest

columns=["filepath", "timestamp", 'site_id', 'sequence_id', "capture_id", 'comment',
         "viewpoint", "species_id", "individual_id"]

class ImportFolderPopup(QDialog):
    def __init__(self, parent, directory):
        super().__init__(parent)
        self.mpDB = parent.mpDB
        self.active_survey = parent.active_survey
        self.directory = os.path.normpath(directory)

        self.file_tree = ['None'] + self.directory.split(os.sep)

        self.setWindowTitle('Import from Folder')
        layout = QVBoxLayout()

        # Create a label
        self.label = QLabel("If available, select the directory level associated with Site:")
        layout.addWidget(self.label)
        layout.addSpacing(5)

        # Site
        site_layout = QHBoxLayout()
        self.site = QComboBox()
        self.site.addItems(self.file_tree)
        self.site.currentTextChanged.connect(self.select_site)
        site_layout.addWidget(self.site)
        layout.addLayout(site_layout)
        layout.addSpacing(5)

        # Ok/Cancel
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttonBox, alignment=Qt.AlignmentFlag.AlignCenter)
        buttonBox.accepted.connect(self.build_manifest)  
        buttonBox.rejected.connect(self.reject)

        # Progress Bar (hidden at start)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)


    def select_site(self):
        try:
            self.site_level = self.site.currentIndex()
            return True
        except IndexError:
            return False
        

    def build_manifest(self):
        # show progress bar
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()

        self.build_thread = BuildManifestThread(self.directory)
        self.build_thread.manifest.connect(self.get_manifest)
        self.build_thread.start()

    def get_manifest(self, manifest):
        print(manifest)
        self.progress_bar.hide()
        self.data = manifest

        if not self.data.empty:
            self.import_manifest()
        else:
            dialog = AlertPopup(self, "No images found! Please try another folder.", title="Alert")
            if dialog.exec():
                self.reject()
        

    def import_manifest(self):
        """
        Media entry (id, filepath, ext, timestamp, comment, site_id)
        """
        # assert bbox in manifest.columns
        self.progress_bar.setRange(0, len(self.data))
        self.progress_bar.show()

        site_level = 1

        print(f"Adding {len(self.data)} files to Database")

        self.import_thread = FolderImportThread(self.mpDB, self.active_survey, self.data, self.site_level)
        self.import_thread.progress_update.connect(self.progress_bar.setValue)
        self.import_thread.finished.connect(self.close)
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

        self.animl_conversion = {"filepath": "FilePath",
                                "timestamp": "DateTime"}    
        

    def run(self):
        for i, file in self.data.iterrows():

            filepath = file[self.animl_conversion['filepath']].item()
            timestamp = file[self.animl_conversion['timestamp']].item()

            # check to see if file exists 
            if not os.path.exists(filepath):
                print(f"Warning, file {filepath} does not exist")
                continue

            # get file extension
            _, ext = os.path.splitext(os.path.basename(filepath))
            
            # get remaining information
            if self.site_level > 0:
                site_name = os.path.normpath(filepath).split(os.sep)[self.site_level + 1]
                print(site_name)
                try:
                    site_id = self.mpDB.select("site", columns='id', row_cond=f'name="{site_name}"')[0][0]
                except IndexError:
                    site_id = self.mpDB.add_site(str(site_name), None, None, int(self.active_survey[0]))
            else:
                if not self.default_site:
                    self.default_site = self.mpDB.add_site("None", None, None, int(self.active_survey[0]))
                site_id = self.default_site

            media_id = self.mpDB.add_media(filepath, ext, timestamp, site_id,
                                           sequence_id=None, 
                                           capture_id=None,
                                           comment=None)
            
            self.progress_update.emit(i)

        # finished adding media
        self.finished.emit()

