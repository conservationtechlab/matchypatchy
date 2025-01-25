"""
Edit A Single Image


"""
import pandas as pd
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QFrame,
                             QLabel, QLineEdit, QDialogButtonBox, QPushButton)
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from matchypatchy.gui.widget_image import ImageWidget
import matchypatchy.database.media as db_roi

class ImagePopup(QDialog):
    def __init__(self, parent, rid):
        super().__init__(parent)
        self.setWindowTitle("View Image")
        self.mpDB = parent.mpDB
        self.rid = rid
        print(self.rid)

        data, column_names = self.mpDB.all_media(row_cond=f"roi.id={self.rid}")
        self.roi_data = pd.DataFrame(data, columns=column_names).replace({float('nan'): None}).reset_index(drop=True)
        print(self.roi_data)

        layout = QVBoxLayout()
        # Title
        label = QLabel(self.roi_data.at[0,"filepath"])
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        # Image
        self.image = ImageWidget()
        self.image.setStyleSheet("border: 1px solid black;")
        self.image.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.image.load(image_path=self.roi_data.at[0,"filepath"])
        layout.addWidget(self.image, 1)


        # MetaData
        columns = ['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
                    'reviewed', 'media_id', 'species_id', 'individual_id', 'emb_id',
                    'filepath', 'ext', 'timestamp', 'station_id', 'sequence_id', 'external_id',
                    'comment', 'favorite', 'binomen', 'common', 'name', 'sex']
        
        # VIEWPOINT, REVIEWED, FAVORITE, NAME, SEX, COMMON, COMMENT, 
        # EXTERNAL ID, SEQUENCE ID, TIMESTAMP, STATION
        # REGION, SURVEY?
        
        border_widget = QWidget()
        border_widget.setObjectName("borderWidget")
        border_widget.setStyleSheet("""#borderWidget { border: 1px solid black; }
                                       QLabel {font-size: 20px;}""")
        info_layout = QVBoxLayout()



        # Timestamp
        timestamp = QHBoxLayout()
        timestamp_label = QLabel("Timestamp: ")
        timestamp_label.setFixedWidth(75)
        timestamp.addWidget(timestamp_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        timestamp.addWidget(QLabel(str(self.roi_data.at[0,"timestamp"])), 1, alignment=Qt.AlignmentFlag.AlignLeft)
        info_layout.addLayout(timestamp)

        # Station
        # TODO: Convert to name, get survey and region
        station = QHBoxLayout()
        station_label = QLabel("Station: ")
        station_label.setFixedWidth(75)
        station.addWidget(station_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        station.addWidget(QLabel(str(self.roi_data.at[0,"station_id"])), 1, alignment=Qt.AlignmentFlag.AlignLeft)
        info_layout.addLayout(station)

        # Sequence ID
        sequence = QHBoxLayout()
        sequence_label = QLabel("Sequence ID: ")
        sequence_label.setFixedWidth(75)
        sequence.addWidget(sequence_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        sequence.addWidget(QLabel(str(self.roi_data.at[0,"sequence_id"])), 1, alignment=Qt.AlignmentFlag.AlignLeft)
        info_layout.addLayout(sequence)

        # External ID
        external = QHBoxLayout()
        external_label = QLabel("External ID: ")
        external_label.setFixedWidth(75)
        external.addWidget(external_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        external.addWidget(QLabel(str(self.roi_data.at[0,"external_id"])), 1, alignment=Qt.AlignmentFlag.AlignLeft)
        info_layout.addLayout(external)

        line = QFrame()
        line.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Raised)
        line.setLineWidth(2)
        info_layout.addWidget(line)


        # Species - EDITABLE
        species = QHBoxLayout()
        species_label = QLabel("Species: ")
        species_label.setFixedWidth(75)
        species.addWidget(species_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.species = QLineEdit()
        self.species.setText(str(self.roi_data.at[0,"common"]))
        species.addWidget(self.species, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        info_layout.addLayout(species)

        # Viewpoint - EDITABLE
        viewpoint = QHBoxLayout()
        viewpoint_label = QLabel("Viewpoint: ")
        viewpoint_label.setFixedWidth(75)
        viewpoint.addWidget(viewpoint_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.viewpoint = QComboBox()
        viewpoint.addWidget(self.viewpoint, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        info_layout.addLayout(viewpoint)

        # Comment - EDITABLE
        comment = QHBoxLayout()
        comment_label = QLabel("Comment: ")
        comment_label.setFixedWidth(75)
        comment.addWidget(comment_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.comment = QLineEdit()
        self.comment.setText(str(self.roi_data.at[0,"comment"]))
        comment.addWidget(self.comment, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        info_layout.addLayout(comment)

        info_layout.addSpacing(10)

        border_widget.setLayout(info_layout)
        layout.addWidget(border_widget, 1)

        # OK/Cancel Buttons
        button_layout = QHBoxLayout()
                # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)

        self.setLayout(layout)
