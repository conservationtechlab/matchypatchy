"""
Popup for Importing a Manifest
"""
import pandas as pd

from PyQt6.QtWidgets import (QDialog, QGridLayout, QVBoxLayout, QHBoxLayout, QProgressBar,
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
                "survey": self.survey_columns[0],
                "filepath": self.columns[0],
                "timestamp": self.columns[0],
                "station": self.columns[0],
                "lat": self.columns[0],
                "long": self.columns[0],
                "region": self.columns[0],
                "camera": self.columns[0],
                "sequence_id": self.columns[0],
                "external_id": self.columns[0],
                "comment": self.columns[0],
                "favorite": self.columns[0],
                "viewpoint": self.columns[0],
                "individual": self.columns[0],
                "sex": self.columns[0],
                "age": self.columns[0],               
            }

            # Create a grid layout for 4 columns x 3 rows
            grid_layout = QGridLayout()
            grid_layout.setSpacing(10)

            # All fields in order (12 total = 4 cols × 3 rows)
            all_fields = [
                ("Filepath", "filepath", True),
                ("Timestamp", "timestamp", True),
                ("Station", "station", True),
                ("Latitude", "lat", False),
                ("Longitude", "long", False),
                ("Region", "region", False),
                ("Camera", "camera", False),
                ("Sequence ID", "sequence_id", False),
                ("External ID", "external_id", False),
                ("Comment", "comment", False),
                ("Favorite", "favorite", False),
                ("Viewpoint", "viewpoint", False),
                ("Individual", "individual", False),
                ("Sex", "sex", False),
                ("Age", "age", False),
            ]

            row = 0
            col = 0

            # Survey goes first (special case)
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
            survey_layout.addSpacing(10)
            grid_layout.addLayout(survey_layout, row, col)
            row += 1

            # Add remaining fields
            for label_text, field_name, is_required in all_fields:
                if row >= 4:  # Move to next row after 4 columns
                    row = 0
                    col += 1
                
                field_layout = QHBoxLayout()
                field_layout.addWidget(QLabel(f"{label_text}:"))
                
                if is_required:
                    asterisk = QLabel("*")
                    asterisk.setStyleSheet("QLabel { color : red; }")
                    field_layout.addWidget(asterisk, alignment=Qt.AlignmentFlag.AlignRight)
                
                combo = QComboBox()
                combo.addItems(self.columns)
                combo.currentIndexChanged.connect(
                    lambda index, field=field_name, req=is_required: self._select_column(index, field, required=req)
                )
                field_layout.addWidget(combo)
                field_layout.addSpacing(10)
                
                grid_layout.addLayout(field_layout, row, col)

                setattr(self, field_name, combo)
                
                row += 1

            layout.addLayout(grid_layout)

                
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


    def _select_column(self, index, field_name, required):
        """
        Generic column selection handler.
        
        Args:
            index: The index of the selected item in the combobox
            field_name: Key for self.selections (e.g., 'filepath')
            required: Whether this field is required
        """
        try:
            self.selections[field_name] = self.columns[index]
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
