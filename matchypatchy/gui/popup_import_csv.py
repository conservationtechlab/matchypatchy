"""
Popup for Importing a Manifest
"""
import logging
import pandas as pd

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QProgressBar,
                             QComboBox, QDialogButtonBox, QLabel)
from PyQt6.QtCore import Qt

from matchypatchy.algo.import_thread import CSVImportThread
from matchypatchy.gui.widget_combobox import ComboBoxSeparator


class ImportCSVPopup(QDialog):
    def __init__(self, parent, manifest):
        super().__init__(parent)
        self.mpDB = parent.mpDB
        self.data = pd.read_csv(manifest)
        self.columns = ["None"] + list(self.data.columns)
        self.survey_columns = [str(parent.active_survey[1])] + list(self.data.columns)

        self.selected_filepath = self.columns[0]
        self.selected_timestamp = self.columns[0]
        self.selected_station = self.columns[0]
        self.selected_survey = self.survey_columns[0]
        self.selected_region = self.columns[0]
        self.selected_sequence_id = self.columns[0]
        self.selected_camera_id = self.columns[0]
        self.selected_external_id = self.columns[0]
        self.selected_viewpoint = self.columns[0]
        self.selected_species = self.columns[0]
        self.selected_individual = self.columns[0]
        self.selected_comment = self.columns[0]

        self.setWindowTitle("Import from CSV")
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
        self.survey = ComboBoxSeparator()
        self.survey.addItem(str(parent.active_survey[1]))
        self.survey.add_separator()
        self.survey.addItems(self.columns)
        self.survey.currentTextChanged.connect(self.select_survey)
        survey_layout.addWidget(self.survey)
        layout.addLayout(survey_layout)
        layout.addSpacing(5)

        # station
        station_layout = QHBoxLayout()
        station_layout.addWidget(QLabel("Station:"))
        asterisk = QLabel("*")
        asterisk.setStyleSheet("QLabel { color : red; }")
        station_layout.addWidget(asterisk, alignment=Qt.AlignmentFlag.AlignRight)
        self.station = QComboBox()
        self.station.addItems(self.columns)
        self.station.currentTextChanged.connect(self.select_station)
        station_layout.addWidget(self.station)
        layout.addLayout(station_layout)
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

        # Camera
        camera_layout = QHBoxLayout()
        camera_layout.addWidget(QLabel("Camera:"))
        self.camera = QComboBox()
        self.camera.addItems(self.columns)
        self.camera.currentTextChanged.connect(self.select_camera)
        camera_layout.addWidget(self.camera)
        layout.addLayout(camera_layout)
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
        if self.survey.currentIndex() == 0:
            self.selected_survey = ["active_survey", self.survey_columns[self.survey.currentIndex()]]
            return True
        else:
            try:
                self.selected_survey = self.survey_columns[self.survey.currentIndex()]
                self.check_ok_button()
                return True
            except IndexError:
                return False

    def select_station(self):
        try:
            self.selected_station = self.columns[self.station.currentIndex()]
            self.check_ok_button()
            return True
        except IndexError:
            return False

    # OPTIONAL
    def select_region(self):
        try:
            self.selected_region = self.columns[self.region.currentIndex()]
            return True
        except IndexError:
            return False

    def select_camera(self):
        try:
            self.selected_camera = self.columns[self.camera.currentIndex()]
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

        Must include filepath, timestamp, station
        """
        if self.survey.currentIndex() == 0:
            self.select_survey()
        if (self.selected_filepath != "None") and (self.selected_timestamp != "None") and \
           (self.selected_station != "None") and (self.selected_survey != "None"):
            self.okButton.setEnabled(True)
        else:
            self.okButton.setEnabled(False)

    def collate_selections(self):
        return {"filepath": self.selected_filepath,
                "timestamp": self.selected_timestamp,
                "survey": self.selected_survey,
                "station": self.selected_station,
                "camera": self.selected_camera,
                "region": self.selected_region,
                "sequence_id": self.selected_sequence_id,
                "external_id": self.selected_external_id,
                "viewpoint": self.selected_viewpoint,
                "species": self.selected_species,
                "individual": self.selected_individual,
                "comment": self.selected_comment}

    def import_manifest(self):
        """
        Media entry (id, filepath, ext, timestamp, comment, station_id)
        """
        # assert bbox in manifest.columns
        self.progress_bar.show()
        selected_columns = self.collate_selections()

        self.data.sort_values(by=[selected_columns['filepath']])

        unique_images = self.data.groupby(selected_columns["filepath"])

        print(f"Adding {len(unique_images)} files and {self.data.shape[0]} ROIs to Database")
        logging.info(f"Adding {len(unique_images)} files and {self.data.shape[0]} ROIs to Database")

        self.import_thread = CSVImportThread(self.mpDB, unique_images, selected_columns)
        self.import_thread.progress_update.connect(self.progress_bar.setValue)
        self.import_thread.finished.connect(self.close)
        self.import_thread.start()
