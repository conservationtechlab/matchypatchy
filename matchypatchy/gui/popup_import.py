"""
Popup for Importing a Manifest
"""
import os
import pandas as pd

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QProgressBar,
                             QComboBox, QDialogButtonBox, QLabel)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from ..utils import is_unique


columns=["filepath", "timestamp", 'site_id', 'sequence_id', "pair_id", 'comment',
         "viewpoint", "species_id",  "individual_id"]

class ImportCSVPopup(QDialog):
    def __init__(self, parent, manifest):
        super().__init__(parent)
        self.mpDB = parent.mpDB
        self.data = pd.read_csv(manifest)
        self.columns = ["None"] + list(self.data.columns)
        
        self.selected_filepath = 0
        self.selected_timestamp = 0
        self.selected_site = 0
        self.selected_sequence_id = 0
        self.selected_pair_id = 0
        self.selected_viewpoint = 0

        self.setWindowTitle('Import from CSV')

        # Create layout
        layout = QVBoxLayout()

        # Create a label
        self.label = QLabel("Select Columns to Import Data")
        layout.addWidget(self.label)
        layout.addSpacing(5)

        # filepath
        filepath_layout = QHBoxLayout()
        filepath_layout.addWidget(QLabel("Filepath:"))
        self.filepath = QComboBox()
        self.filepath.addItems(self.columns)
        self.filepath.currentTextChanged.connect(self.select_filepath)
        filepath_layout.addWidget(self.filepath)
        layout.addLayout(filepath_layout)
        layout.addSpacing(5)

        # timestamp
        timestamp_layout = QHBoxLayout()
        timestamp_layout.addWidget(QLabel("Timestamp:"))
        self.timestamp = QComboBox()
        self.timestamp.addItems(self.columns)
        self.timestamp.currentTextChanged.connect(self.select_timestamp)
        timestamp_layout.addWidget(self.timestamp)
        layout.addLayout(timestamp_layout)
        layout.addSpacing(5)

        # site
        site_layout = QHBoxLayout()
        site_layout.addWidget(QLabel("Site:"))
        self.site = QComboBox()
        self.site.addItems(self.columns)
        self.site.currentTextChanged.connect(self.select_site)
        site_layout.addWidget(self.site)
        layout.addLayout(site_layout)
        layout.addSpacing(5)

        # Sequence
        sequence_layout = QHBoxLayout()
        sequence_layout.addWidget(QLabel("Sequence ID:"))
        self.sequence_id = QComboBox()
        self.sequence_id.addItems(self.columns)
        self.sequence_id.currentTextChanged.connect(self.select_sequence)
        sequence_layout.addWidget(self.sequence_id)
        layout.addLayout(sequence_layout)
        layout.addSpacing(5)

        # Pair
        sequence_layout = QHBoxLayout()
        sequence_layout.addWidget(QLabel("Pair ID:"))
        self.sequence_id = QComboBox()
        self.sequence_id.addItems(self.columns)
        self.sequence_id.currentTextChanged.connect(self.select_sequence)
        sequence_layout.addWidget(self.sequence_id)
        layout.addLayout(sequence_layout)
        layout.addSpacing(5)


        # Comment
        comment_layout = QHBoxLayout()
        comment_layout.addWidget(QLabel("Comment:"))
        self.comment = QComboBox()
        self.comment.addItems(self.columns)
        self.comment.currentTextChanged.connect(self.select_sequence)
        comment_layout.addWidget(self.comment)
        layout.addLayout(comment_layout)

        # Create OK button
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttonBox, alignment=Qt.AlignmentFlag.AlignCenter)
        buttonBox.accepted.connect(self.import_manifest)  
        buttonBox.rejected.connect(self.reject)
        self.okButton = buttonBox.button(buttonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)



        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.data.shape[0])
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        

        self.setLayout(layout)


    def select_filepath(self):
        try:
            self.selected_filepath = self.columns[self.filepath.currentIndex()]
            return True
        except IndexError:
            return False
        
    def select_timestamp(self):
        try:
            self.selected_timestamp = self.columns[self.timestamp.currentIndex()]
            return True
        except IndexError:
            return False
        
    def select_site(self):
        try:
            self.selected_site = self.columns[self.site.currentIndex()]
            return True
        except IndexError:
            return False
        
    def select_sequence(self):
        try:
            self.selected_sequence_id = self.columns[self.sequence_id.currentIndex()]
            return True
        except IndexError:
            return False
        

    def check_ok_button(self):
        """
        Determine if sufficient information for import

        Must include filepath, timestamp, site
        """
        # 
        # must have 
        

        if self.selected_filepath != 0 :
            self.okButton.setEnabled(True)


    def collate_selections(self):
        return {"filepath": self.selected_filepath,
                "timestamp": self.selected_timestamp,
                "site": self.selected_site,
                "sequence_id": self.selected_sequence_id}


    # TODO: Check for duplicates
    def import_manifest(self):
        """
        Media entry (id, filepath, ext, timestamp, comment, site_id)
        """
        # assert bbox in manifest.columns
        selected_columns = self.collate_selections()

        self.data.sort_values(by=["FilePath"])

        unique_images = self.data.groupby(selected_columns['filepath'])

        self.import_thread = ImportThread(unique_images, selected_columns)
        self.import_thread.progress_update.connect(self.progress_bar.setValue)
        self.import_thread.start()


        print(f"Added {len(unique_images)} files and {self.data.shape[0]} ROIs to Database")



class ImportThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar

    def __init__(self, unique_images, selected_columns):
        super().__init__()
        self.unique_images = unique_images
        self.selected_columns = selected_columns
    
    def run(self):
        i = 0  # progressbar counter
        for filepath, group in self.unique_images:
            print(group)

            # create site
            if is_unique(group[self.selected_columns['site']]):
                site = group.loc[0, self.selected_columns['site']] # get first one
            else:
                AssertionError(f"File {filepath} has ROI references to multiple sites, should be one.") 

            # check all datetimes are the same
            if is_unique(group[self.selected_columns['timestamp']]):
                timestamp = group.loc[0, self.selected_columns['site']]
            else:
                AssertionError(f"File {filepath} has ROI references to multiple datetimes, should be one.") 

"""
            # check all sequence_id are the same
            if "sequence_id" in manifest.columns:
                sequence_id = group["sequence_id"].iloc[0] if is_unique(group["sequence_id"]) else None
            else:
                sequence_id = None
                
            filename = os.path.basename(filepath)
            _, ext = os.path.splitext(filename)

            try:
                site_id = valid_sites.loc[valid_sites["name"]==site,"id"].values[0]
                site_id = int(site_id)
            except KeyError:
                print('Site referenced but not added to Database')
                return False

            media_id = mpDB.add_media(filepath, ext, site_id, datetime=datetime, sequence_id=sequence_id)


            # "bbox_x", "bbox_y", "bbox_w", "bbox_h"

            # TODO: add dtype checks
            for _, roi in group.iterrows():
                # Frame number for videos, else 1 if image 
                # WARNING! WILL HAVE TO DYNAMICALLY PULL FRAME WHEN RUNNING miewid
                frame = roi['frame_number'] if 'frame_number' in manifest.columns else 1

                bbox_x = roi['bbox1']
                bbox_y = roi['bbox2']
                bbox_w = roi['bbox3']
                bbox_h = roi['bbox4']
                
                # add viewpoint if exists
                viewpoint = roi['Viewpoint'] if 'Viewpoint' in manifest.columns else None
                individual = roi['Individual'] if 'Individual' in manifest.columns else None

                species = roi['Species']
                # look up species id
                if isinstance(species, str):
                    species_id = mpDB.select("species", columns='id', row_cond=f'common="{species}"')
                    if species_id:
                        species_id = species_id[0][0]

                # already references table id
                elif isinstance(species, int):
                    species_id = species 
                else:
                    print(f"Could not add detection for unknown species {species}")
                    continue

                # do not add emb_id, to be determined later
                roi_id = mpDB.add_roi(frame, bbox_x, bbox_y, bbox_w, bbox_h, media_id, species_id,
                                    viewpoint=viewpoint, reviewed=0, individual_id=individual)
        

                self.progress_update.emit(int((i + 1) / len(self.data.shape[0])))
"""