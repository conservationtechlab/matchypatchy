"""
Popup for Importing a Manifest
"""
import logging
from pathlib import Path
import pandas as pd

from PyQt6.QtWidgets import (QDialog, QGridLayout, QVBoxLayout, QHBoxLayout, QProgressBar,
                             QComboBox, QDialogButtonBox, QLabel)
from PyQt6.QtCore import Qt

from matchypatchy.threads.import_thread import CSVImportThread, CSVMigrateThread
from matchypatchy.gui.widgets.gui_assets import ComboBoxSeparator
from matchypatchy.project import UsesProject


logger = logging.getLogger(__name__)


class ImportCSVPopup(UsesProject, QDialog):
    """
    Popup for importing data from a CSV manifest.
    """

    EXPECTED_COLUMNS = {'id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
                        'reviewed', 'media_id', 'individual_id', 'emb', 'base_dir_id',
                        'relative_path', 'ext', 'timestamp', 'station_id', 'sequence_id',
                        'camera_id', 'external_id', 'comment', 'favorite', 'name', 'sex',
                        'filepath', 'station_name', 'lat', 'long', 'station_survey_id',
                        'survey_name', 'region_name', 'camera_name'}

    # Accepted CSV column names (normalized) for each field, in order of preference
    COLUMN_ALIASES = {
        "survey": ["survey", "survey_name"],
        "filepath": ["filepath", "file_path", "filename", "file_name", "path", "file"],
        "timestamp": ["timestamp", "datetime", "date_time"],
        "station": ["station", "station_name"],
        "lat": ["lat", "latitude"],
        "long": ["long", "lon", "lng", "longitude"],
        "region": ["region", "region_name"],
        "camera": ["camera", "camera_name"],
        "sequence_id": ["sequence_id", "sequence"],
        "external_id": ["external_id"],
        "comment": ["comment", "comments"],
        "favorite": ["favorite"],
        "viewpoint": ["viewpoint"],
        "individual": ["individual", "individual_name", "individual_id", "name"],
        "sex": ["sex"],
    }

    def __init__(self, parent, manifest):
        super().__init__(parent)
        self.project = parent.project
        self.active_survey = parent.active_survey[1]
        self.data, self.read_error = self._read_manifest(manifest)
        self.import_thread = None

        # setup layout
        self.setWindowTitle("Import from CSV")
        layout = QVBoxLayout()
        # Create a label
        self.label = QLabel("")
        layout.addWidget(self.label)
        layout.addSpacing(5)

        # unreadable csv, show why and only allow closing
        if self.read_error is not None:
            self.label.setText(f"Could not read {Path(manifest).name}. View the log for details.\n{self.read_error}")
            self.migrate = False

        # exported mpdb, import directly
        elif set(self.data.columns) == self.EXPECTED_COLUMNS:
            self.label.setStyleSheet("QLabel { font-size : 12pt; }")
            self.label.setText("Found an exported MatchyPatchy Database. Do you want to migrate to this database?")
            self.migrate = True

        else:
            self.label.setText("Select Columns to Import Data")
            self.migrate = False
            self.columns = ["None"] + list(self.data.columns)
            self.survey_columns = [str(self.active_survey)] + self.columns
            self.selections = {
                # None = import into the active survey (first entry); otherwise a CSV column
                "survey": None,
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
                "sex": self.columns[0]
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
                # create combobox for column selection
                combo = QComboBox()
                combo.addItems(self.columns)
                combo.currentIndexChanged.connect(
                    lambda index, field=field_name,
                    req=is_required: self._select_column(index, field, required=req)
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

        # Progress message label
        self.progress_label = QLabel()
        self.progress_label.hide()
        layout.addWidget(self.progress_label)
        # Progress Bar (hidden at start)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.data.shape[0])
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)
        # nothing to import, OK stays disabled
        if self.read_error is not None:
            return
        if not self.migrate:
            self.auto_populate_columns()
        self.check_ok_button()

    def _read_manifest(self, manifest):
        """Read the csv, returns (data, None) or (empty DataFrame, error) if it can't be read"""
        try:
            try:
                return pd.read_csv(manifest), None
            except UnicodeDecodeError:
                # Excel on Windows saves csvs as cp1252, not utf-8
                return pd.read_csv(manifest, encoding="cp1252"), None
        except (UnicodeDecodeError, pd.errors.EmptyDataError, pd.errors.ParserError, OSError) as e:
            logger.error(f"Could not read manifest {manifest}: {e}")
            return pd.DataFrame(), e

    @staticmethod
    def _normalize(name):
        """Normalize a column name for matching (case, whitespace, hyphens)."""
        return str(name).strip().lower().replace(" ", "_").replace("-", "_")

    def auto_populate_columns(self):
        """Preselect combobox entries for CSV columns that match known field names."""
        normalized = {}
        for column in self.data.columns:
            normalized.setdefault(self._normalize(column), column)

        for field_name, aliases in self.COLUMN_ALIASES.items():
            match = next((normalized[a] for a in aliases if a in normalized), None)
            if match is None:
                continue
            # setting the index fires the change handler, which updates self.selections
            combo = getattr(self, field_name)
            # survey combo leads with the active survey and a separator; search after them
            start = 2 if field_name == "survey" else 0
            index = next((i for i in range(start, combo.count()) if combo.itemText(i) == str(match)), -1)
            if index >= 0:
                combo.setCurrentIndex(index)

    def select_survey(self):
        """Select the survey column from the CSV."""
        if self.survey.currentIndex() == 0:
            self.selections['survey'] = None
            self.check_ok_button()
            return True
        else:
            try:
                # remove spacer
                self.selections['survey'] = self.survey_columns[self.survey.currentIndex() - 1]
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
        # one import at a time; re-enabled when it reports back
        self.okButton.setEnabled(False)
        self._cancel_pending = False  # Cancel pressed once, waiting for a second press
        self._cancelled = False  # stop requested, report it when the thread ends
        # assert bbox in manifest.columns
        self.progress_bar.show()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v/%m")

        # migrate from exported mpdb
        if self.migrate:
            logger.info(f"Migrating {len(self.data.groupby("filepath"))} files and {self.data.shape[0]} ROIs to Database")
            self.import_thread = CSVMigrateThread(self, self.data)
            self.import_thread.progress_update.connect(self.progress_bar.setValue)
            self.import_thread.error_update.connect(self.show_errors)  # Connect error signal
            self.import_thread.import_failed.connect(self.show_import_failed)
            self.import_thread.finished.connect(self.import_finished)
            self.import_thread.start()
            return

        # import from manifest with user-selected columns
        else:
            self.data.sort_values(by=[self.selections['filepath']])
            unique_images = self.data.groupby(self.selections["filepath"])
            print(f"Adding {len(unique_images)} files and {self.data.shape[0]} ROIs to Database")
            logger.info(f"Adding {len(unique_images)} files and {self.data.shape[0]} ROIs to Database")
            self.import_thread = CSVImportThread(self, unique_images, self.selections, self.active_survey)
            self.import_thread.progress_update.connect(self.progress_bar.setValue)
            self.import_thread.progress_message.connect(self.show_message)  # Connect progress message signal
            self.import_thread.import_failed.connect(self.show_import_failed)
            self.import_thread.finished.connect(self.import_finished)
            self.import_thread.start()

    def show_import_failed(self, message):
        """
        Show a fatal import error in the popup instead of closing it.
        This method is connected to the import_failed signal of the CSVImportThread.
        """
        # QThread.finished still fires when run() returns, keep the popup open
        try:
            self.import_thread.finished.disconnect(self.import_finished)
        except TypeError:
            pass
        self.progress_bar.hide()
        self.progress_label.hide()
        self.label.setText(f"Import failed, some files may have been partially imported. View the log for details.\n{message}")

        # Disconnect the import_manifest slot and connect the close slot to the accepted signal
        self.buttonBox.accepted.disconnect(self.import_manifest)
        self.buttonBox.accepted.connect(self.close)
        self.okButton.setEnabled(True)

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
        self.okButton.setEnabled(True)

    def show_message(self, message):
        """Show progress messages from the import thread."""
        self.progress_label.show()
        self.progress_label.setText(message)

    def import_finished(self):
        """
        The import thread ended: close after a csv import, or say where a cancelled import stopped.

        Connected to QThread.finished in import_manifest. A finished migrate is reported by
        show_errors and a failed import by show_import_failed (which disconnects this), so
        here only a cancel needs reporting; without it the bar just froze and the popup
        looked stuck.
        """
        if getattr(self, "_cancelled", False):
            self.label.setText(f"Import stopped after {self.progress_bar.value()} of {self.progress_bar.maximum()} "
                               "rows. Rows imported so far are kept, import the same file again to resume.")
            self.progress_label.hide()
            self.buttonBox.accepted.disconnect(self.import_manifest)
            self.buttonBox.accepted.connect(self.close)
            self.okButton.setEnabled(True)
        elif not self.migrate:
            self.close()

    def reject(self):
        """Cancel: close, or while importing ask in the popup and stop on a second press"""
        if getattr(self, "import_thread", None) is not None and self.import_thread.isRunning():
            # once OK is disabled, focus moves to Cancel and a stray space would press it
            if not getattr(self, "_cancel_pending", False):
                self._cancel_pending = True
                self.label.setText("Press Cancel again to stop the import. Rows imported so far are kept, "
                                   "and importing the same file again resumes where it stopped.")
                return
            self._cancelled = True
            self.label.setText("Stopping the import...")
            self.import_thread.requestInterruption()
            # import_finished reports where it stopped once the thread has ended
            return
        super().reject()
