"""
Popup for Importing a Manifest
"""
import pandas as pd

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QProgressBar,
                             QComboBox, QDialogButtonBox, QLabel)
from PyQt6.QtCore import Qt

from matchypatchy.threads.import_thread import CSVImportThread, CSVMigrateThread
from matchypatchy.gui.widgets.gui_assets import ComboBoxSeparator


class ImportCSVPopup(QDialog):

    EXPECTED_COLUMNS = {'id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
                        'reviewed', 'favorite', 'media_id', 'individual_id', 'emb',
                        'filepath', 'ext', 'timestamp', 'station_id', 'camera_id', 'sequence_id', 'external_id',
                        'comment', 'name', 'sex', 'age',
                        'station_id', 'station_name', 'lat', 'long', 'station_survey_id', 
                        'survey_name', 'region_name', 'camera_name'}

    def __init__(self, parent, manifest):
        super().__init__(parent)
        self.logger = parent.logger
        self.active_survey = parent.active_survey[1]
        self.data = pd.read_csv(manifest)

        # setup layout
        self.setWindowTitle("Import from CSV")
        layout = QVBoxLayout()
         # Create a label
        self.label = QLabel("")
        layout.addWidget(self.label)
        layout.addSpacing(5)

        # exported mpdb, import directly
        if set(self.data.columns) == self.EXPECTED_COLUMNS:
            self.label.setStyleSheet("QLabel { font-size : 12pt; }")
            self.label.setText("Found an exported MatchyPatchy Database. Do you want to migrate to this database?")
            self.migrate = True

        else:
            self.label.setText("Select Columns to Import Data")
            self.migrate = False
            self.columns = ["None"] + list(self.data.columns)
            self.survey_columns = [str(self.active_survey)] + list(self.data.columns)
            self.selected_filepath = self.columns[0]
            self.selected_timestamp = self.columns[0]
            self.selected_survey = self.survey_columns[0]
            self.selected_station = self.columns[0]
            self.selected_region = self.columns[0]
            self.selected_sequence_id = self.columns[0]
            self.selected_camera = self.columns[0]
            self.selected_external_id = self.columns[0]
            self.selected_viewpoint = self.columns[0]
            self.selected_individual = self.columns[0]
            self.selected_favorite = self.columns[0]
            self.selected_comment = self.columns[0]

            # Survey
            survey_layout = QHBoxLayout()
            survey_layout.addWidget(QLabel("Survey:"))
            asterisk = QLabel("*")
            asterisk.setStyleSheet("QLabel { color : red; }")
            survey_layout.addWidget(asterisk, alignment=Qt.AlignmentFlag.AlignRight)
            self.survey = ComboBoxSeparator()
            self.survey.addItem(str(self.active_survey))
            self.survey.add_separator()
            self.survey.addItems(self.columns)
            self.survey.currentTextChanged.connect(self.select_survey)
            survey_layout.addWidget(self.survey)
            layout.addLayout(survey_layout)
            layout.addSpacing(5)

            required_fields = [("Filepath", "filepath", self.select_region),
                               ("Timestamp", "camera", self.select_camera),
                               ("Station", "external_id", self.select_external),]

            for label_text, attr_name, callback in required_fields:
                field_layout = QHBoxLayout()
                field_layout.addWidget(QLabel(f"{label_text}:"))
                asterisk = QLabel("*")
                asterisk.setStyleSheet("QLabel { color : red; }")
                field_layout.addWidget(asterisk, alignment=Qt.AlignmentFlag.AlignRight)
                combo = QComboBox()
                combo.addItems(self.columns)
                combo.currentTextChanged.connect(callback)
                field_layout.addWidget(combo)
                layout.addLayout(field_layout)
                layout.addSpacing(5)
                setattr(self, attr_name, combo)

            additional_fields = [
                ("Region", "region", self.select_region),
                ("Camera", "camera", self.select_camera),
                ("Sequence ID", "sequence_id", self.select_sequence),
                ("External ID", "external_id", self.select_external),
                ("Viewpoint", "viewpoint", self.select_viewpoint),
                ("Individual", "individual", self.select_individual),
                ("Favorite", "favorite", self.select_individual), 
                ("Comment", "comment", self.select_comment)
            ]

            for label_text, attr_name, callback in additional_fields:
                field_layout = QHBoxLayout()
                field_layout.addWidget(QLabel(f"{label_text}:"))
                combo = QComboBox()
                combo.addItems(self.columns)
                combo.currentTextChanged.connect(callback)
                field_layout.addWidget(combo)
                layout.addLayout(field_layout)
                layout.addSpacing(5)

                setattr(self, attr_name, combo)

        # Ok/Cancel
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.buttonBox, alignment=Qt.AlignmentFlag.AlignCenter)
        self.buttonBox.accepted.connect(self.import_manifest)
        self.buttonBox.rejected.connect(self.reject)
        self.okButton = self.buttonBox.button(self.buttonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)

        # Progress Bar (hidden at start)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.data.shape[0])
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)
        self.check_ok_button()

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

    def select_individual(self):
        try:
            self.selected_individual = self.columns[self.individual.currentIndex()]
            return True
        except IndexError:
            return False

    def select_favorite(self):
        try:
            self.selected_favorite = self.columns[self.favorite.currentIndex()]
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
        if self.migrate:
            self.okButton.setEnabled(True)

        else:
            if self.survey.currentIndex() == 0:
                self.select_survey()
            if (self.selected_filepath != "None") and (self.selected_timestamp != "None") and \
            (self.selected_station != "None") and (self.selected_survey != "None"):
                self.okButton.setEnabled(True)
            else:
                self.okButton.setEnabled(False)

    def collate_selections(self):
        """Collate selected columns into a dictionary"""
        return {"filepath": self.selected_filepath,
                "timestamp": self.selected_timestamp,
                "survey": self.selected_survey,
                "station": self.selected_station,
                "camera": self.selected_camera,
                "region": self.selected_region,
                "sequence_id": self.selected_sequence_id,
                "external_id": self.selected_external_id,
                "viewpoint": self.selected_viewpoint,
                "individual": self.selected_individual,
                "favorite": self.selected_favorite,
                "comment": self.selected_comment}

    def import_manifest(self):
        """
        Media entry (id, filepath, ext, timestamp, comment, station_id)
        """
        # assert bbox in manifest.columns
        self.progress_bar.show()

        # migrate from exported mpdb
        if self.migrate:
            self.logger.info(f"Migrating {len(self.data.groupby("filepath"))} files and {self.data.shape[0]} ROIs to Database")
            self.import_thread = CSVMigrateThread(self.mpDB, self.data, self.logger)
            self.import_thread.progress_update.connect(self.progress_bar.setValue)
            self.import_thread.error_update.connect(self.show_errors)  # Connect error signal
            #self.import_thread.finished.connect(self.close)
            self.import_thread.start()
            return

        # import from manifest with user-selected columns
        else:
            selected_columns = self.collate_selections()
            self.data.sort_values(by=[selected_columns['filepath']])
            unique_images = self.data.groupby(selected_columns["filepath"])
            print(f"Adding {len(unique_images)} files and {self.data.shape[0]} ROIs to Database")
            self.logger.info(f"Adding {len(unique_images)} files and {self.data.shape[0]} ROIs to Database")
            self.import_thread = CSVImportThread(self.mpDB, unique_images, selected_columns, self.logger)
            self.import_thread.progress_update.connect(self.progress_bar.setValue)
            self.import_thread.finished.connect(self.close)
            self.import_thread.start()

    def show_errors(self, errors):
        """
        Show errors encountered during migration in the popup.
        This method is connected to the error_update signal of the CSVMigrateThread.
        """
        if len(errors) > 0:
            self.progress_bar.hide()
            error_message = f"{len(errors)} file(s) could not be imported because they do not exist. View the log for details."
            self.label.setText(error_message)
        else:
            self.label.setText("Import completed successfully.")

        # Disconnect the import_manifest slot and connect the close slot to the accepted signal
        self.buttonBox.accepted.disconnect(self.import_manifest)
        self.buttonBox.accepted.connect(self.close)
