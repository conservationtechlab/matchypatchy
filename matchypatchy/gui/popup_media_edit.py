"""
Batch Edit Selected Media
"""

import pandas as pd
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QFrame,
                             QLabel, QTextEdit, QDialogButtonBox, QPushButton)
from PyQt6.QtCore import Qt

from matchypatchy.gui.widget_image import ImageWidget
from matchypatchy.algo.models import load
import matchypatchy.database.media as db_media
from matchypatchy.database.location import fetch_station_names_from_id

import pandas as pd
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QFrame,
                             QLabel, QTextEdit, QDialogButtonBox, QPushButton)
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from matchypatchy.gui.popup_individual import IndividualFillPopup
from matchypatchy.gui.widget_image import ImageWidget

from matchypatchy.algo.models import load
import matchypatchy.database.media as db_roi

class MediaEditPopup(QDialog):
    def __init__(self, parent, ids):
        super().__init__(parent)
        self.setWindowTitle("Batch Edit Media")
        self.setFixedSize(1000, 500)
        self.mpDB = parent.mpDB
        self.ids = ids
        self.current_index = 0  # Track current media index
        self.data = self.load_selected_media()

        # Load Viewpoint options
        self.VIEWPOINTS = load('VIEWPOINTS')

        # Layout ---------------------------------------------------------------
        container_layout = QVBoxLayout()

        # Title
        top = QHBoxLayout()
        top.addWidget(QLabel("Batch Edit Media"), 1, alignment=Qt.AlignmentFlag.AlignCenter)
        container_layout.addLayout(top)

        layout = QHBoxLayout()

        # Image Display
        self.image = ImageWidget()
        self.image.setStyleSheet("border: 1px solid black;")
        self.image.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.image, 1)

        # Metadata Panel -------------------------------------------------------------
        border_widget = QWidget()
        border_widget.setObjectName("borderWidget")
        border_widget.setStyleSheet("#borderWidget { border: 1px solid black; }")
        info_layout = QVBoxLayout()

        horizontal_gap = 80
        vertical_gap = 8

        # Timestamp
        timestamp = QHBoxLayout()
        timestamp_label = QLabel("Timestamp: ")
        timestamp_label.setFixedWidth(horizontal_gap)
        timestamp.addWidget(timestamp_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.timestamp_data = QLabel()
        timestamp.addWidget(self.timestamp_data, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        info_layout.addLayout(timestamp)
        info_layout.addSpacing(vertical_gap)

        # Station
        station = QHBoxLayout()
        station_label = QLabel("Station: ")
        station_label.setFixedWidth(horizontal_gap)
        station.addWidget(station_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.station_data = QLabel()
        station.addWidget(self.station_data, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        info_layout.addLayout(station)
        info_layout.addSpacing(vertical_gap)

        # Sequence ID
        sequence = QHBoxLayout()
        sequence_label = QLabel("Sequence ID: ")
        sequence_label.setFixedWidth(horizontal_gap)
        sequence.addWidget(sequence_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.sequence_data = QLabel()
        sequence.addWidget(self.sequence_data, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        info_layout.addLayout(sequence)
        info_layout.addSpacing(vertical_gap)

        # External ID
        external = QHBoxLayout()
        external_label = QLabel("External ID: ")
        external_label.setFixedWidth(horizontal_gap)
        external.addWidget(external_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.external_data = QLabel()
        external.addWidget(self.external_data, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        info_layout.addLayout(external)
        info_layout.addSpacing(vertical_gap)

        line = QFrame()
        line.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Raised)
        line.setLineWidth(2)
        info_layout.addWidget(line)
        info_layout.addSpacing(vertical_gap)

        # EDITABLE FIELDS -------------------------------------------------------------
        # Viewpoint - EDITABLE
        viewpoint_layout = QHBoxLayout()
        viewpoint_label = QLabel("Viewpoint: ")
        viewpoint_label.setFixedWidth(horizontal_gap)
        viewpoint_layout.addWidget(viewpoint_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.viewpoint = QComboBox()
        self.viewpoint.addItems(["None"] + list(self.VIEWPOINTS.values()))
        self.viewpoint.currentIndexChanged.connect(self.change_viewpoint)
        viewpoint_layout.addWidget(self.viewpoint, 1)
        info_layout.addLayout(viewpoint_layout)
        info_layout.addSpacing(vertical_gap)

        # Comment - EDITABLE
        comment_layout = QHBoxLayout()
        comment_label = QLabel("Comment: ")
        comment_label.setFixedWidth(horizontal_gap)
        comment_layout.addWidget(comment_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.comment = QTextEdit()
        self.comment.setFixedHeight(60)
        comment_layout.addWidget(self.comment, 1)
        info_layout.addLayout(comment_layout)
        info_layout.addSpacing(vertical_gap)

        border_widget.setLayout(info_layout)
        layout.addWidget(border_widget, 1)
        container_layout.addLayout(layout)

        # Bottom Buttons ---------------------------------------------------------
        button_layout = QHBoxLayout()

        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.prev_image)
        self.prev_button.setEnabled(False)
        button_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.next_image)
        button_layout.addWidget(self.next_button)

        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.apply_changes)
        buttonBox.rejected.connect(self.reject)
        button_layout.addWidget(buttonBox)

        container_layout.addLayout(button_layout)

        self.setLayout(container_layout)

        # Load first image
        self.load_image()

    def load_selected_media(self):
        """Load data for selected media items."""
        return self.parent.media_table.data_filtered.loc[self.parent.media_table.data_filtered["id"].isin(self.ids)]

    def load_image(self):
        """Load current media and its details."""
        current_media = self.data.iloc[self.current_index]
        image_path = current_media["filepath"]
        self.image.load(image_path)

        # Metadata
        self.timestamp_data.setText(str(current_media["timestamp"]))
        survey_info = fetch_station_names_from_id(self.mpDB, current_media["station_id"])
        self.station_data.setText(str(survey_info['station_name']))
        self.sequence_data.setText(str(current_media["sequence_id"]))
        self.external_data.setText(str(current_media["external_id"]))

        # Editable fields
        self.viewpoint.setCurrentIndex(list(self.VIEWPOINTS.values()).index(self.VIEWPOINTS.get(str(current_media["viewpoint"]), "None")))
        self.comment.setText(str(current_media["comment"]) if pd.notna(current_media["comment"]) else "")

        # Enable/Disable navigation buttons
        self.prev_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < len(self.data) - 1)

    def prev_image(self):
        """Move to the previous image."""
        if self.current_index > 0:
            self.current_index -= 1
            self.load_image()

    def next_image(self):
        """Move to the next image."""
        if self.current_index < len(self.data) - 1:
            self.current_index += 1
            self.load_image()

    def change_viewpoint(self):
        """Update viewpoint selection for all selected media."""
        selected_viewpoint = self.viewpoint.currentText()
        for i in range(len(self.data)):
            self.data.at[self.data.index[i], "viewpoint"] = selected_viewpoint

    def apply_changes(self):
        """Save the changes for all selected media."""
        new_viewpoint = self.viewpoint.currentText()
        new_comment = self.comment.toPlainText()

        for row in self.data.index:
            self.parent.media_table.data_filtered.at[row, "viewpoint"] = new_viewpoint
            self.parent.media_table.data_filtered.at[row, "comment"] = new_comment

            # Update database
            self.parent.mpDB.edit_row("media", self.data.at[row, "id"],
                                      {"viewpoint": new_viewpoint, "comment": new_comment},
                                      allow_none=False, quiet=False)

        self.parent.media_table.refresh_table()
        self.accept()
