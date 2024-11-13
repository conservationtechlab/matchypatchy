"""
Popup for Importing a Manifest
"""
import os
import pandas as pd

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QProgressBar,
                             QComboBox, QDialogButtonBox, QLabel)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


columns=["filepath", "timestamp", 'site_id', 'sequence_id', "external_id", 'comment',
         "viewpoint", "species_id", "individual_id"]

class ImportCSVPopup(QDialog):
    def __init__(self, parent, manifest):
        super().__init__(parent)
        self.mpDB = parent.mpDB
        self.data = pd.read_csv(manifest)
        self.columns = ["None"] + list(self.data.columns)
        self.survey_columns = [str(parent.active_survey[1])] + list(self.data.columns)
        
        self.selected_filepath = self.columns[0]
        self.selected_timestamp = self.columns[0]
        self.selected_site = self.columns[0]
        self.selected_survey = self.columns[0]
        self.selected_region = self.columns[0]
        self.selected_sequence_id = self.columns[0]
        self.selected_external_id = self.columns[0]
        self.selected_viewpoint = self.columns[0]
        self.selected_species = self.columns[0]
        self.selected_individual = self.columns[0]
        self.selected_comment = self.columns[0]

        self.setWindowTitle('Import from CSV')
        layout = QVBoxLayout()

        # Create a label
        self.label = QLabel("Select Columns to Import Data")
        layout.addWidget(self.label)
        layout.addSpacing(5)

        # Filepath
        filepath_layout = QHBoxLayout()
        filepath_layout.addWidget(QLabel("Filepath:"))
        asterisk = QLabel("*")
        asterisk.setStyleSheet("QLabel { color : red; }")
        filepath_layout.addWidget(asterisk, alignment=Qt.AlignmentFlag.AlignRight)
        self.filepath = QComboBox()
        self.filepath.addItems(self.columns)
        self.filepath.currentTextChanged.connect(self.select_filepath)
        filepath_layout.addWidget(self.filepath)
        layout.addLayout(filepath_layout)
        layout.addSpacing(5)

        # Timestamp
        timestamp_layout = QHBoxLayout()
        timestamp_layout.addWidget(QLabel("Timestamp:"))
        asterisk = QLabel("*")
        asterisk.setStyleSheet("QLabel { color : red; }")
        timestamp_layout.addWidget(asterisk, alignment=Qt.AlignmentFlag.AlignRight)
        self.timestamp = QComboBox()
        self.timestamp.addItems(self.columns)
        self.timestamp.currentTextChanged.connect(self.select_timestamp)
        timestamp_layout.addWidget(self.timestamp)
        layout.addLayout(timestamp_layout)
        layout.addSpacing(5)

        # Survey
        survey_layout = QHBoxLayout()
        survey_layout.addWidget(QLabel("Survey:"))
        asterisk = QLabel("*")
        asterisk.setStyleSheet("QLabel { color : red; }")
        survey_layout.addWidget(asterisk, alignment=Qt.AlignmentFlag.AlignRight)
        self.survey = QComboBox()
        self.survey.addItems(self.survey_columns)
        self.survey.currentTextChanged.connect(self.select_survey)
        survey_layout.addWidget(self.survey)
        layout.addLayout(survey_layout)
        layout.addSpacing(5)

        # Site
        site_layout = QHBoxLayout()
        site_layout.addWidget(QLabel("Site:"))
        asterisk = QLabel("*")
        asterisk.setStyleSheet("QLabel { color : red; }")
        site_layout.addWidget(asterisk, alignment=Qt.AlignmentFlag.AlignRight)
        self.site = QComboBox()
        self.site.addItems(self.columns)
        self.site.currentTextChanged.connect(self.select_site)
        site_layout.addWidget(self.site)
        layout.addLayout(site_layout)
        layout.addSpacing(5)

        # Region
        region_layout = QHBoxLayout()
        region_layout.addWidget(QLabel("Region:"))
        self.region = QComboBox()
        self.region.addItems(self.columns)
        self.region.currentTextChanged.connect(self.select_region)
        region_layout.addWidget(self.region)
        layout.addLayout(region_layout)
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

        # External ID
        external_layout = QHBoxLayout()
        external_layout.addWidget(QLabel("External ID:"))
        self.external_id = QComboBox()
        self.external_id.addItems(self.columns)
        self.external_id.currentTextChanged.connect(self.select_external)
        external_layout.addWidget(self.external_id)
        layout.addLayout(external_layout)
        layout.addSpacing(5)

        # Viewpoint
        viewpoint_layout = QHBoxLayout()
        viewpoint_layout.addWidget(QLabel("Viewpoint:"))
        self.viewpoint = QComboBox()
        self.viewpoint.addItems(self.columns)
        self.viewpoint.currentTextChanged.connect(self.select_viewpoint)
        viewpoint_layout.addWidget(self.viewpoint)
        layout.addLayout(viewpoint_layout)
        layout.addSpacing(5)

        # Species
        species_layout = QHBoxLayout()
        species_layout.addWidget(QLabel("Species:"))
        self.species = QComboBox()
        self.species.addItems(self.columns)
        self.species.currentTextChanged.connect(self.select_species)
        species_layout.addWidget(self.species)
        layout.addLayout(species_layout)
        layout.addSpacing(5)

        # Individual
        individual_layout = QHBoxLayout()
        individual_layout.addWidget(QLabel("Individual:"))
        self.individual = QComboBox()
        self.individual.addItems(self.columns)
        self.individual.currentTextChanged.connect(self.select_individual)
        individual_layout.addWidget(self.individual)
        layout.addLayout(individual_layout)
        layout.addSpacing(5)

        # Comment
        comment_layout = QHBoxLayout()
        comment_layout.addWidget(QLabel("Comment:"))
        self.comment = QComboBox()
        self.comment.addItems(self.columns)
        self.comment.currentTextChanged.connect(self.select_sequence)
        comment_layout.addWidget(self.comment)
        layout.addLayout(comment_layout)

        # Ok/Cancel
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttonBox, alignment=Qt.AlignmentFlag.AlignCenter)
        buttonBox.accepted.connect(self.import_manifest)  
        buttonBox.rejected.connect(self.reject)
        self.okButton = buttonBox.button(buttonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)

        # Progress Bar (hidden at start)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.data.shape[0])
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    # would this be better as a switch statement? probably
    def select_filepath(self):
        try:
            self.selected_filepath = self.columns[self.filepath.currentIndex()]
            self.check_ok_button()
            return True
        except IndexError:
            return False
        
    def select_timestamp(self):
        try:
            self.selected_timestamp = self.columns[self.timestamp.currentIndex()]
            self.check_ok_button()
            return True
        except IndexError:
            return False
        
    def select_survey(self):
        try:
            self.selected_survey = self.survey_columns[self.survey.currentIndex()]
            self.check_ok_button()
            return True
        except IndexError:
            return False
        
    def select_site(self):
        try:
            self.selected_site = self.columns[self.site.currentIndex()]
            self.check_ok_button()
            return True
        except IndexError:
            return False
        
    def select_region(self):
        try:
            self.selected_region = self.columns[self.region.currentIndex()]
            self.check_ok_button()
            return True
        except IndexError:
            return False

    def select_sequence(self):
        try:
            self.selected_sequence_id = self.columns[self.sequence_id.currentIndex()]
            return True
        except IndexError:
            return False
        
    def select_external(self):
        try:
            self.selected_external_id = self.columns[self.external_id.currentIndex()]
            return True
        except IndexError:
            return False
        
    def select_viewpoint(self):
        try:
            self.selected_viewpoint = self.columns[self.viewpoint.currentIndex()]
            return True
        except IndexError:
            return False
        
    def select_species(self):
        try:
            self.selected_species = self.columns[self.species.currentIndex()]
            return True
        except IndexError:
            return False
        
    def select_individual(self):
        try:
            self.selected_individual = self.columns[self.individual.currentIndex()]
            return True
        except IndexError:
            return False
        
    def select_comment(self):
        try:
            self.selected_comment = self.columns[self.comment.currentIndex()]
            return True
        except IndexError:
            return False

    def check_ok_button(self):
        """
        Determine if sufficient information for import

        Must include filepath, timestamp, site
        """
        if (self.selected_filepath != "None") and (self.selected_timestamp != "None") and \
              (self.selected_site != "None") and (self.selected_survey != "None"):
            self.okButton.setEnabled(True)
        else:
            self.okButton.setEnabled(False)

    def collate_selections(self):
        return {"filepath": self.selected_filepath,
                "timestamp": self.selected_timestamp,
                "survey": self.selected_survey,
                "site": self.selected_site,
                "region": self.selected_region,
                "sequence_id": self.selected_sequence_id,
                "external_id": self.selected_external_id,
                "viewpoint": self.selected_viewpoint,
                "species": self.selected_species,
                "individual": self.selected_individual,
                "comment": self.selected_comment}

    # TODO: Check for duplicates
    def import_manifest(self):
        """
        Media entry (id, filepath, ext, timestamp, comment, site_id)
        """
        # assert bbox in manifest.columns
        self.progress_bar.show()
        selected_columns = self.collate_selections()
        print(selected_columns)

        self.data.sort_values(by=["FilePath"])

        unique_images = self.data.groupby(selected_columns['filepath'])

        print(f"Adding {len(unique_images)} files and {self.data.shape[0]} ROIs to Database")

        self.import_thread = CSVImportThread(self.mpDB, unique_images, selected_columns)
        self.import_thread.progress_update.connect(self.progress_bar.setValue)
        self.import_thread.finished.connect(self.close)
        self.import_thread.start()


class CSVImportThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar

    def __init__(self, mpDB, unique_images, selected_columns):
        super().__init__()
        self.mpDB = mpDB
        self.unique_images = unique_images
        self.selected_columns = selected_columns
    
    def run(self):
        roi_counter = 0  # progressbar counter
        for filepath, group in self.unique_images:

            # check to see if file exists 
            if not os.path.exists(filepath):
                print(f"Warning, file {filepath} does not exist")
                continue

            # get file extension
            _, ext = os.path.splitext(os.path.basename(filepath))
            
            # get remaining information
            exemplar = group.head(1)

            timestamp = exemplar[self.selected_columns['timestamp']].item()

            # get or create new survey
            survey_name = exemplar[self.selected_columns['survey']].item()
            region_name = exemplar[self.selected_columns['region']].item()
            region_name = None if region_name == 'None' else str(region_name)
            try:
                survey_id = self.mpDB.select("survey", columns='id', row_cond=f'name="{survey_name}"')[0][0]
            except IndexError:
                survey_id = self.mpDB.add_site(str(site_name), region_name, None, None)

            # get or create site
            site_name = exemplar[self.selected_columns['site']].item()  
            try:
                site_id = self.mpDB.select("site", columns='id', row_cond=f'name="{site_name}"')[0][0]
            except IndexError:
                site_id = self.mpDB.add_site(str(site_name), None, None, survey_id)

            # Optional data
            sequence_id = int(exemplar[self.selected_columns['sequence_id']].item()) if self.selected_columns['sequence_id'] != 'None' else None

            # get external_id and convert or create new one
            if self.selected_columns['external_id'] != 'None':
                external_id = int(exemplar[self.selected_columns['external_id']].item())
            else:
                external_id = None

            comment = exemplar[self.selected_columns['comment']].item() if self.selected_columns['comment'] != 'None' else None

            media_id = self.mpDB.add_media(filepath, ext, timestamp, site_id,
                                           sequence_id=sequence_id, 
                                           external_id=external_id,
                                           comment=comment)
            # TODO: add dtype checks
            for i, roi in group.iterrows():
                # Frame number for videos, else 1 if image 
                # WARNING! WILL HAVE TO DYNAMICALLY PULL FRAME WHEN RUNNING miewid
                frame = roi['frame_number'] if 'frame_number' in group.columns else 1
 
                if 'bbox1' in roi:
                    bbox_x = roi['bbox1']
                    bbox_y = roi['bbox2']
                    bbox_w = roi['bbox3']
                    bbox_h = roi['bbox4']
                elif 'bbox_x' in roi:
                    bbox_x = roi['bbox_x']
                    bbox_y = roi['bbox_y']
                    bbox_w = roi['bbox_w']
                    bbox_h = roi['bbox_h']
                else: # add filterable empties 
                    bbox_x = -1 
                    bbox_y = -1
                    bbox_w = -1
                    bbox_h = -1

                # add species
                if self.selected_columns['species'] != 'None':
                    species_name = roi[self.selected_columns['species']]
                    try:
                        species_id = self.mpDB.select("species", columns='id', row_cond=f'common="{species_name}"')[0][0]
                    except IndexError:
                        species_id = self.mpDB.add_species("Taxon not specified", str(species_name))
                else: # no species
                    species_id = None

                # viewpoint
                viewpoint = roi[self.selected_columns['viewpoint']] if self.selected_columns['viewpoint'] != 'None' else None

                # individual
                if self.selected_columns['individual'] != 'None': 
                    individual = roi[self.selected_columns['individual']]
                    try:
                        individual_id = self.mpDB.select("individual", columns='id', row_cond=f'name="{individual}"')[0][0]
                    except IndexError:
                        individual_id = self.mpDB.add_individual(species_id, str(individual))
                    
                else: # no individual id, need review
                    individual_id = None
                    
                # set reviewed to 1 for named images
                reviewed = 1 if individual_id is not None else 0

                # do not add emb_id, to be determined later
                roi_id = self.mpDB.add_roi(media_id, frame, bbox_x, bbox_y, bbox_w, bbox_h,  
                                           species_id, viewpoint=viewpoint, reviewed=reviewed, 
                                           individual_id=individual_id, emb_id=0)
                roi_counter += 1
                self.progress_update.emit(roi_counter)

        # finished adding media
        self.finished.emit()