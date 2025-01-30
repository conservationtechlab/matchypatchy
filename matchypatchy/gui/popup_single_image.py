"""
Edit A Single Image


"""
import pandas as pd
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QFrame,
                             QLabel, QTextEdit, QDialogButtonBox, QPushButton)
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from matchypatchy.gui.popup_individual import IndividualFillPopup
from matchypatchy.gui.widget_image import ImageWidget

from matchypatchy.algo.models import load
import matchypatchy.database.media as db_roi

class ImagePopup(QDialog):
    def __init__(self, parent, rid, crop=False):
        super().__init__(parent)
        self.setWindowTitle("View Image")
        self.setFixedSize(1000,500)
        self.mpDB = parent.mpDB
        self.rid = rid
        self.crop = crop
        # load data
        self.roi_data = self.load()

        # Layout ---------------------------------------------------------------
        container_layout = QVBoxLayout()
        # Title
        label = QLabel(self.roi_data.at[0,"filepath"])
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(label)

        layout = QHBoxLayout()

        # Image
        self.image = ImageWidget()
        self.image.setStyleSheet("border: 1px solid black;")
        self.image.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.image.load(image_path=self.roi_data.at[0,"filepath"], 
                        bbox=db_roi.get_bbox(self.roi_data.iloc[0]), crop=False)
        layout.addWidget(self.image, 1)
        
        # Metadata -------------------------------------------------------------
        border_widget = QWidget()
        border_widget.setObjectName("borderWidget")
        border_widget.setStyleSheet("""#borderWidget { border: 1px solid black; }""")
        info_layout = QVBoxLayout()

        horizontal_gap = 120
        vertical_gap = 8

        # Timestamp 
        timestamp = QHBoxLayout()
        timestamp_label = QLabel("Timestamp: ")
        timestamp_label.setFixedWidth(horizontal_gap)
        timestamp.addWidget(timestamp_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.timestamp_data = QLabel()
        timestamp.addWidget(self.timestamp_data,  1, alignment=Qt.AlignmentFlag.AlignLeft)
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

        # Survey
        survey = QHBoxLayout()
        survey_label = QLabel("Survey: ")
        survey_label.setFixedWidth(horizontal_gap)
        survey.addWidget(survey_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.survey_data = QLabel()
        survey.addWidget(self.survey_data, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        info_layout.addLayout(survey)
        info_layout.addSpacing(vertical_gap)

        # Region
        region = QHBoxLayout()
        region_label = QLabel("Region: ")
        region_label.setFixedWidth(horizontal_gap)
        region.addWidget(region_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.region_data = QLabel()
        region.addWidget(self.region_data, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        info_layout.addLayout(region)
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
        info_layout.addSpacing(int(vertical_gap/2))

        line = QFrame()
        line.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Raised)
        line.setLineWidth(2)
        info_layout.addWidget(line)
        info_layout.addSpacing(int(vertical_gap/2))

        # Name - EDITABLE
        name = QHBoxLayout()
        name_label = QLabel("Name: ")
        name_label.setFixedWidth(horizontal_gap)
        name.addWidget(name_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.name = QComboBox()
        self.name.addItems(['Unknown'])
        #self.species.setText(str(self.roi_data.at[0,"common"]))
        name.addWidget(self.name, stretch=1)
        add_individual = QPushButton("+")
        add_individual.pressed.connect(self.new_individual)
        name.addWidget(add_individual)
        info_layout.addLayout(name)
        info_layout.addSpacing(vertical_gap)

        # Sex - EDITABLE
        sex = QHBoxLayout()
        sex_label = QLabel("Sex: ")
        sex_label.setFixedWidth(horizontal_gap)
        sex.addWidget(sex_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.sex = QComboBox()
        self.sex.addItems(['Unknown', 'Male', 'Female'])
        sex.addWidget(self.sex, stretch=1)
        info_layout.addLayout(sex)
        info_layout.addSpacing(vertical_gap)

        # Species - EDITABLE
        species = QHBoxLayout()
        species_label = QLabel("Species: ")
        species_label.setFixedWidth(horizontal_gap)
        species.addWidget(species_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.species = QComboBox()
        # get species 
        self.species.addItems(['Unknown'])
        species.addWidget(self.species, stretch=1)
        add_species = QPushButton("+")
        species.addWidget(add_species)
        info_layout.addLayout(species)
        info_layout.addSpacing(vertical_gap)

        # Viewpoint - EDITABLE
        viewpoint = QHBoxLayout()
        viewpoint_label = QLabel("Viewpoint: ")
        viewpoint_label.setFixedWidth(horizontal_gap)
        viewpoint.addWidget(viewpoint_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.VIEWPOINTS = load('VIEWPOINTS')
        self.viewpoint = QComboBox()
        self.viewpoint.addItems(list(self.VIEWPOINTS.values())[1:])  # skip 'any'
        viewpoint.addWidget(self.viewpoint, 1)
        info_layout.addLayout(viewpoint)
        info_layout.addSpacing(vertical_gap)

        # Comment - EDITABLE
        comment = QHBoxLayout()
        comment_label = QLabel("Comment: ")
        comment_label.setFixedWidth(horizontal_gap)
        comment.addWidget(comment_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.comment = QTextEdit()
        self.comment.setFixedHeight(100)
        comment.addWidget(self.comment, 1)
        comment.addStretch()
        info_layout.addLayout(comment)

        border_widget.setLayout(info_layout)
        layout.addWidget(border_widget, 1)
        container_layout.addLayout(layout)

        # OK/Cancel Buttons
        button_layout = QHBoxLayout()
                # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        container_layout.addLayout(button_layout)
        self.setLayout(container_layout)

        # display data
        self.refresh_values()

    def load(self):
        data, column_names = self.mpDB.all_media(row_cond=f"roi.id={self.rid}")
        return pd.DataFrame(data, columns=column_names).replace({float('nan'): None}).reset_index(drop=True)
    
    def refresh_values(self):
        # disable comboboxes
        self.blockSignals(True)
                # MetaData
        columns = ['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
                    'reviewed', 'media_id', 'species_id', 'individual_id', 'emb_id',
                    'filepath', 'ext', 'timestamp', 'station_id', 'sequence_id', 'external_id',
                    'comment', 'favorite', 'binomen', 'common', 'name', 'sex']
        
        self.timestamp_data.setText(str(self.roi_data.at[0,"timestamp"]))
        # TODO: Convert to name, get survey and region
        self.station_data.setText(str(self.roi_data.at[0,"station_id"]))
        #self.survey_data.setText(str(self.roi_data.at[0,"station_id"]))
        #self.region_data.setText(str(self.roi_data.at[0,"station_id"]))
        self.sequence_data.setText(str(self.roi_data.at[0,"sequence_id"]))
        self.external_data.setText(str(self.roi_data.at[0,"external_id"]))

        # Editable
        # Name
        iid = self.roi_data.at[0,"individual_id"]
        if iid is None:
            self.name.setCurrentIndex(0)
        else:
            self.name.setCurrentIndex(iid)
        # Sex
        sex = self.roi_data.at[0,"sex"]
        if sex is None:
            self.sex.setCurrentIndex(0)
        else:
            self.sex.setCurrentIndex(self.sex.findText(str()))
        # Species
        current_species = self.roi_data.at[0,"common"]
        if current_species is None:
            self.species.setCurrentIndex(0)
        else:
            self.species.setCurrentIndex(self.species.findText(str(current_species)))
        # Viewpoint
        current_viewpoint = self.roi_data.at[0,"viewpoint"]
        if current_viewpoint is None:
            self.viewpoint.setCurrentIndex(0)
        else:
            self.viewpoint.setCurrentIndex(self.species.findText(self.VIEWPOINTS[int(current_viewpoint)]))

        self.comment.setText(str(self.roi_data.at[0,"comment"]))
        # renable comboboxes
        self.blockSignals(False)

    # Edits --------------------------------------------------------------------
    def change_name(self):
        iid = self.roi_data.at[0,"individual_id"]
        #self.mpDB.edit_row('roi', self.rid, {"individual_id": X})
        pass

    def change_sex(self):
        iid = self.roi_data.at[0,"individual_id"]
        #self.mpDB.edit_row('individual', self.rid, {"sex": })

    def change_species(self):
        #self.mpDB.edit_row('roi', self.rid, {"viewpoint": 1})
        pass

    def change_viewpoint(self):
        viewpoint_keys = list(self.VIEWPOINTS.keys())
        self.mpDB.edit_row('roi', self.rid, {"viewpoint": viewpoint_keys[self.viewpoint.currentIndex()]})

    def new_individual(self):
        dialog = IndividualFillPopup(self)
        if dialog.exec():
            individual_id = self.mpDB.add_individual(dialog.get_species_id(),
                                                     dialog.get_name(),
                                                     dialog.get_sex())
        #reload data
        self.roi_data = self.load()
        self.refresh_values()


    def new_species(self):
        dialog = SpeciesFillPopup(self)
        if dialog.exec():
            individual_id = self.mpDB.add_individual(dialog.get_binomen(),
                                                     dialog.get_common())
        self.roi_data = self.load()
        self.refresh_values()

