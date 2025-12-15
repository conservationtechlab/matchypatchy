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

        # Initialize selected fields using a dictionary for cleaner code
        self.selected_fields = {
            'filepath': self.columns[0],
            'timestamp': self.columns[0],
            'station': self.columns[0],
            'survey': self.survey_columns[0],
            'region': self.columns[0],
            'sequence_id': self.columns[0],
            'external_id': self.columns[0],
            'viewpoint': self.columns[0],
            'species': self.columns[0],
            'individual': self.columns[0],
            'comment': self.columns[0]
        }
        
        # Store references to combo boxes for easy access
        self.combo_boxes = {}

        self.setWindowTitle("Import from CSV")
        layout = QVBoxLayout()

        # Create a label
        self.label = QLabel("Select Columns to Import Data")
        layout.addWidget(self.label)
        layout.addSpacing(5)

        # Define field configurations: (label, field_name, is_required, use_separator)
        field_configs = [
            ("Filepath:", "filepath", True, False),
            ("Timestamp:", "timestamp", True, False),
            ("Survey:", "survey", True, True),  # Special: uses separator
            ("Station:", "station", True, False),
            ("Region:", "region", False, False),
            ("Sequence ID:", "sequence_id", False, False),
            ("External ID:", "external_id", False, False),
            ("Viewpoint:", "viewpoint", False, False),
            ("Species:", "species", False, False),
            ("Individual:", "individual", False, False),
            ("Comment:", "comment", False, False),
        ]

        # Create all field layouts using the helper method
        for label_text, field_name, is_required, use_separator in field_configs:
            items = self.survey_columns if field_name == 'survey' else self.columns
            field_layout = self._create_field_layout(
                label_text, field_name, items, is_required, use_separator
            )
            layout.addLayout(field_layout)
            layout.addSpacing(5)

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

    def _create_field_layout(self, label_text, field_name, items, is_required=False, 
                            use_separator=False, connect_handler=None):
        """
        Helper method to create a field layout with label and combobox.
        
        Args:
            label_text: Text for the label
            field_name: Key for storing the combobox reference
            items: List of items for the combobox
            is_required: Whether to show red asterisk
            use_separator: Whether to use ComboBoxSeparator instead of QComboBox
            connect_handler: Optional custom handler, otherwise uses generic handler
        
        Returns:
            QHBoxLayout containing the field widgets
        """
        field_layout = QHBoxLayout()
        field_layout.addWidget(QLabel(label_text))
        
        if is_required:
            asterisk = QLabel("*")
            asterisk.setStyleSheet("QLabel { color : red; }")
            field_layout.addWidget(asterisk, alignment=Qt.AlignmentFlag.AlignRight)
        
        # Create combobox
        if use_separator:
            combo = ComboBoxSeparator()
            combo.addItem(items[0])
            combo.add_separator()
            combo.addItems(items[1:])
        else:
            combo = QComboBox()
            combo.addItems(items)
        
        # Store reference
        self.combo_boxes[field_name] = combo
        
        # Connect handler
        if connect_handler:
            combo.currentTextChanged.connect(connect_handler)
        else:
            combo.currentTextChanged.connect(lambda: self._generic_select_handler(field_name))
        
        field_layout.addWidget(combo)
        return field_layout

    def _generic_select_handler(self, field_name):
        """
        Generic handler for field selection that works for most fields.
        
        Args:
            field_name: The key in selected_fields dictionary
        
        Returns:
            True if successful, False otherwise
        """
        try:
            combo = self.combo_boxes[field_name]
            
            # Special handling for survey field
            if field_name == 'survey':
                if combo.currentIndex() == 0:
                    self.selected_fields['survey'] = ["active_survey", self.survey_columns[0]]
                else:
                    self.selected_fields['survey'] = self.survey_columns[combo.currentIndex()]
                self.check_ok_button()
                return True
            
            # Standard handling for other fields
            self.selected_fields[field_name] = self.columns[combo.currentIndex()]
            
            # Check button state for required fields
            if field_name in ['filepath', 'timestamp', 'station']:
                self.check_ok_button()
            
            return True
        except IndexError:
            return False

    # Legacy methods for backward compatibility - they now delegate to generic handler
    def select_filepath(self):
        return self._generic_select_handler('filepath')

    def select_timestamp(self):
        return self._generic_select_handler('timestamp')

    def select_survey(self):
        return self._generic_select_handler('survey')

    def select_station(self):
        return self._generic_select_handler('station')

    def select_region(self):
        return self._generic_select_handler('region')

    def select_sequence(self):
        return self._generic_select_handler('sequence_id')

    def select_external(self):
        return self._generic_select_handler('external_id')

    def select_viewpoint(self):
        return self._generic_select_handler('viewpoint')

    def select_species(self):
        return self._generic_select_handler('species')

    def select_individual(self):
        return self._generic_select_handler('individual')

    def select_comment(self):
        return self._generic_select_handler('comment')

    def check_ok_button(self):
        """
        Determine if sufficient information for import

        Must include filepath, timestamp, station
        """
        self.select_survey()
        if (self.selected_fields['filepath'] != "None" and 
            self.selected_fields['timestamp'] != "None" and
            self.selected_fields['station'] != "None" and 
            self.selected_fields['survey'] != "None"):
            self.okButton.setEnabled(True)
        else:
            self.okButton.setEnabled(False)

    def collate_selections(self):
        return self.selected_fields.copy()

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
