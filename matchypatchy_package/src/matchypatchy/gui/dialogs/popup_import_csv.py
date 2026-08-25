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
    """
    Popup for importing data from a CSV manifest.
    """

    EXPECTED_COLUMNS = {'id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
                        'reviewed', 'media_id', 'individual_id', 'emb', 'base_dir_id',
                        'relative_path', 'ext', 'timestamp', 'station_id', 'sequence_id',
                        'camera_id', 'external_id', 'comment', 'favorite', 'name', 'sex', 'age',
                        'filepath', 'station_name', 'lat', 'long', 'station_survey_id',
                        'survey_name', 'region_name', 'camera_name'}

    def __init__(self, parent, manifest):
        super().__init__(parent)
        self.mpDB = parent.mpDB
        self.cfg = parent.cfg
        self.logger = parent.logger
        self.active_survey = parent.active_survey[1]
        self.data = pd.read_csv(manifest)
        self.import_thread = None

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
            self.selections = {
                "filepath": self.columns[0],
                "timestamp": self.columns[0],
                "survey": self.survey_columns[0],
                "station": self.columns[0],
                "region": self.columns[0],
                "sequence_id": self.columns[0],
                "camera": self.columns[0],
                "external_id": self.columns[0],
                "viewpoint": self.columns[0],
                "individual": self.columns[0],
                "favorite": self.columns[0],
                "comment": self.columns[0],
            }

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

            required_fields = [("Filepath", "filepath"),
                               ("Timestamp", "timestamp"),
                               ("Station", "station"),]

            for label_text, attr_name in required_fields:
                field_layout = QHBoxLayout()
                field_layout.addWidget(QLabel(f"{label_text}:"))
                asterisk = QLabel("*")
                asterisk.setStyleSheet("QLabel { color : red; }")
                field_layout.addWidget(asterisk, alignment=Qt.AlignmentFlag.AlignRight)
                combo = QComboBox()
                combo.addItems(self.columns)
                combo.currentTextChanged.connect(
                    lambda field=attr_name, cb=combo: self._select_column(field, cb, check_ok=True)
                )
                field_layout.addWidget(combo)
                layout.addLayout(field_layout)
                layout.addSpacing(5)
                setattr(self, attr_name, combo)

            additional_fields = [
                ("Region", "region"),
                ("Camera", "camera"),
                ("Sequence ID", "sequence_id"),
                ("External ID", "external_id"),
                ("Viewpoint", "viewpoint"),
                ("Individual", "individual"),
                ("Favorite", "favorite"),
                ("Comment", "comment")
            ]

            for label_text, field_name in additional_fields:
                field_layout = QHBoxLayout()
                field_layout.addWidget(QLabel(f"{label_text}:"))
                combo = QComboBox()
                combo.addItems(self.columns)
                combo.currentTextChanged.connect(
                    lambda field=field_name, cb=combo: self._select_column(field, cb)
                )
                field_layout.addWidget(combo)
                layout.addLayout(field_layout)
                layout.addSpacing(5)
                
                setattr(self, field_name, combo)

                
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


    def select_survey(self):
        """Select the survey column from the CSV."""
        if self.survey.currentIndex() == 0:
            self.selections['survey'] = [self.survey_columns[self.survey.currentIndex()]]
            return True
        else:
            try:
                self.selections['survey'] = self.survey_columns[self.survey.currentIndex()]
                self.check_ok_button()
                return True
            except IndexError:
                return False


    def _select_column(self, field_name, combobox, required=False):
        """
        Generic column selection handler.
        
        Args:
            field_name: Key for self.selections (e.g., 'filepath')
            combobox: The QComboBox widget
            required: Whether this field is required
        """
        try:
            self.selections[field_name] = self.columns[combobox.currentIndex()]
            if required:
                self.check_ok_button()
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
            if (self.selections['filepath'] != "None") and (self.selections['timestamp'] != "None") and \
                (self.selections['station'] != "None") and (self.selections['survey'] != "None"):
                self.okButton.setEnabled(True)
            else:
                self.okButton.setEnabled(False)

    def import_manifest(self):
        """
        Media entry (id, filepath, ext, timestamp, comment, station_id)
        """
        # assert bbox in manifest.columns
        self.progress_bar.show()

        # migrate from exported mpdb
        if self.migrate:
            self.logger.info(f"Migrating {len(self.data.groupby("filepath"))} files and {self.data.shape[0]} ROIs to Database")
            self.import_thread = CSVMigrateThread(self, self.data)
            self.import_thread.progress_update.connect(self.progress_bar.setValue)
            self.import_thread.error_update.connect(self.show_errors)  # Connect error signal
            self.import_thread.start()
            return

        # import from manifest with user-selected columns
        else:
            self.data.sort_values(by=[self.selections['filepath']])
            unique_images = self.data.groupby(self.selections["filepath"])
            print(f"Adding {len(unique_images)} files and {self.data.shape[0]} ROIs to Database")
            self.logger.info(f"Adding {len(unique_images)} files and {self.data.shape[0]} ROIs to Database")
            self.import_thread = CSVImportThread(self, unique_images, self.selections)
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
