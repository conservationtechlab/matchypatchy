"""
Edit A Single Image

"""
import pandas as pd
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QFrame,
                             QLabel, QTextEdit, QDialogButtonBox, QPushButton)
from PyQt6.QtCore import Qt

from matchypatchy.gui.popup_species import SpeciesFillPopup
from matchypatchy.gui.popup_individual import IndividualFillPopup
from matchypatchy.gui.widget_image import ImageWidget

from matchypatchy.algo.models import load
import matchypatchy.database.media as db_roi
from matchypatchy.database.species import fetch_individual
from matchypatchy.database.location import fetch_station_names_from_id


class ROIPopup(QDialog):
    def __init__(self, parent, rid, crop=False):
        super().__init__(parent)
        self.setWindowTitle("View Image")
        self.setFixedSize(1000, 500)
        self.mpDB = parent.mpDB
        self.rid = rid
        self.crop = crop
        # load data
        self.roi_data = self.load()
        self.individuals = []
        self.species_list = []

        # Layout ---------------------------------------------------------------
        container_layout = QVBoxLayout()
        # Title
        top = QHBoxLayout()
        top.addWidget(QLabel(self.roi_data.at[0, "filepath"]), 1, alignment=Qt.AlignmentFlag.AlignCenter)
        # Favorite
        self.button_favorite = QPushButton("♥")
        self.button_favorite.setFixedWidth(30)
        self.button_favorite.setCheckable(True)
        self.button_favorite.clicked.connect(self.favorite)
        top.addWidget(self.button_favorite, 0, alignment=Qt.AlignmentFlag.AlignRight)
        container_layout.addLayout(top)

        layout = QHBoxLayout()
        # Image
        self.image = ImageWidget()
        self.image.setStyleSheet("border: 1px solid black;")
        self.image.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.image.load(image_path=self.roi_data.at[0, "filepath"],
                        bbox=db_roi.get_bbox(self.roi_data.iloc[0]), crop=False)
        layout.addWidget(self.image, 1)

        # Metadata -------------------------------------------------------------
        border_widget = QWidget()
        border_widget.setObjectName("borderWidget")
        border_widget.setStyleSheet("""#borderWidget { border: 1px solid black; }""")
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
        info_layout.addSpacing(int(vertical_gap / 2))

        line = QFrame()
        line.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Raised)
        line.setLineWidth(2)
        info_layout.addWidget(line)
        info_layout.addSpacing(int(vertical_gap / 2))

        # EDITABLE -------------------------------------------------------------
        # Name - EDITABLE
        name_layout = QHBoxLayout()
        name_label = QLabel("Name: ")
        name_label.setFixedWidth(horizontal_gap)
        name_layout.addWidget(name_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.name = QComboBox()
        self.name.currentIndexChanged.connect(self.change_name)
        name_layout.addWidget(self.name, stretch=1)
        add_individual = QPushButton("+")
        add_individual.pressed.connect(self.new_individual)
        name_layout.addWidget(add_individual)
        info_layout.addLayout(name_layout)
        info_layout.addSpacing(vertical_gap)
        # Sex - EDITABLE
        sex_layout = QHBoxLayout()
        sex_label = QLabel("Sex: ")
        sex_label.setFixedWidth(horizontal_gap)
        sex_layout.addWidget(sex_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.sex = QComboBox()
        self.sex.addItems(['Unknown', 'Male', 'Female'])
        self.sex.currentIndexChanged.connect(self.change_sex)
        sex_layout.addWidget(self.sex, stretch=1)
        info_layout.addLayout(sex_layout)
        info_layout.addSpacing(vertical_gap)
        # Species - EDITABLE
        species_layout = QHBoxLayout()
        species_label = QLabel("Species: ")
        species_label.setFixedWidth(horizontal_gap)
        species_layout.addWidget(species_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.species = QComboBox()
        self.refresh_species()
        self.species.currentIndexChanged.connect(self.change_species)
        species_layout.addWidget(self.species, stretch=1)
        button_add_species = QPushButton("+")
        button_add_species.pressed.connect(self.new_species)
        species_layout.addWidget(button_add_species)
        info_layout.addLayout(species_layout)
        info_layout.addSpacing(vertical_gap)
        # Viewpoint - EDITABLE
        viewpoint_layout = QHBoxLayout()
        viewpoint_label = QLabel("Viewpoint: ")
        viewpoint_label.setFixedWidth(horizontal_gap)
        viewpoint_layout.addWidget(viewpoint_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.VIEWPOINTS = load('VIEWPOINTS')
        self.viewpoint = QComboBox()
        self.viewpoint.addItems(list(self.VIEWPOINTS.values())[1:])  # skip 'any'
        self.viewpoint.currentIndexChanged.connect(self.change_viewpoint)
        viewpoint_layout.addWidget(self.viewpoint, 1)
        info_layout.addLayout(viewpoint_layout)
        info_layout.addSpacing(vertical_gap)
        # Comment - EDITABLE
        comment = QHBoxLayout()
        comment_label = QLabel("Comment: ")
        comment_label.setFixedWidth(horizontal_gap)
        comment.addWidget(comment_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.comment = QTextEdit()
        self.comment.setFixedHeight(60)
        comment.addWidget(self.comment, 1)
        comment.addStretch()
        info_layout.addLayout(comment)
        info_layout.addStretch()

        border_widget.setLayout(info_layout)
        layout.addWidget(border_widget, 1)
        container_layout.addLayout(layout)

        # Bottom Buttons
        button_layout = QHBoxLayout()
        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        container_layout.addLayout(button_layout)
        self.setLayout(container_layout)

        # display data
        self.refresh_names()
        self.refresh_values()

    def refresh_names(self):
        self.name.blockSignals(True)
        self.name.clear()
        self.individuals = fetch_individual(self.mpDB)
        self.name_list = ["Unknown"] + [el for el in self.individuals["name"]]
        self.name.addItems(self.name_list)
        self.name.blockSignals(False)

    def refresh_species(self):
        self.species.blockSignals(True)
        self.species.clear()
        species = self.mpDB.select("species", "id, common")
        self.species_list = [(0, 'Unknown')] + species
        self.species.addItems([el[1] for el in self.species_list])
        self.species.blockSignals(False)

    def load(self):
        data, column_names = self.mpDB.all_media(row_cond=f"roi.id={self.rid}")
        return pd.DataFrame(data, columns=column_names).replace({float('nan'): None}).reset_index(drop=True)

    def refresh_values(self):
        # disable comboboxes
        self.blockSignals(True)

        self.timestamp_data.setText(str(self.roi_data.at[0, "timestamp"]))
        survey_info = fetch_station_names_from_id(self.mpDB, self.roi_data.at[0, "station_id"])
        self.station_data.setText(str(survey_info['station_name']))
        self.survey_data.setText(str(survey_info["survey_name"]))
        self.region_data.setText(str(survey_info["region_name"]))
        self.sequence_data.setText(str(self.roi_data.at[0, "sequence_id"]))
        self.external_data.setText(str(self.roi_data.at[0, "external_id"]))

        # Editable -------------------------------------------------------------
        # Name
        self.iid = self.roi_data.at[0, "individual_id"]

        if self.iid is None:
            self.name.setCurrentIndex(0)
            self.sex.setDisabled(True)
        else:
            self.name.setCurrentIndex(self.iid)
            self.sex.setDisabled(False)

        # Sex
        current_sex = self.roi_data.at[0, "sex"]
        if current_sex is None:
            self.sex.setCurrentIndex(0)
        else:
            self.sex.setCurrentIndex(self.sex.findText(str(current_sex)))
        # Species
        current_species = self.roi_data.at[0, "common"]
        if current_species is None:
            self.species.setCurrentIndex(0)
        else:
            self.species.setCurrentIndex(self.species.findText(str(current_species)))
        # Viewpoint
        current_viewpoint = self.VIEWPOINTS[str(self.roi_data.at[0, "viewpoint"])]
        if current_viewpoint == 'None':
            self.viewpoint.setCurrentIndex(0)
        else:
            self.viewpoint.setCurrentIndex(self.viewpoint.findText(current_viewpoint))
        # Comment
        self.comment.setText(str(self.roi_data.at[0, "comment"]))
        # renable comboboxes
        self.blockSignals(False)

    # Edits --------------------------------------------------------------------
    def change_name(self):
        if self.name.currentIndex() > 0:
            selected_individual = self.individuals["name" == self.name_list[self.name.currentIndex()]]
            print(f"→ Assigning individual_id={selected_individual[0]} to ROI {self.rid}")
            self.mpDB.edit_row('roi', self.rid, {"individual_id": selected_individual[0]})
            self.sex.setCurrentIndex(self.sex.findText(str(selected_individual[2])))
            self.sex.setDisabled(False)
        else:
            print("→ Setting to Unknown")
            self.sex.setCurrentIndex(0)
            self.sex.setDisabled(True)

    def change_sex(self):
        if self.name.currentIndex() > 0:
            iid = self.individuals["name" == self.name_list[self.name.currentIndex()]]['id']
            sex_val = self.sex.currentText()
            print(f"\n=== CHANGING SEX ===")
            print(f"Setting sex of individual_id={iid} to '{sex_val}'")
            self.mpDB.edit_row('individual', iid, {"sex": f"'{self.sex.currentText()}'"})

    def change_species(self):
        selected_species = self.species_list[self.species.currentIndex()]
        if selected_species[0] > 0:
            self.mpDB.edit_row('roi', self.rid, {"species_id": f"'{selected_species[0]}'"})

    def change_viewpoint(self):
        viewpoint_keys = list(self.VIEWPOINTS.keys())
        print(viewpoint_keys)
        selected_vewpoint = viewpoint_keys[self.viewpoint.currentIndex() + 1]
        print(self.viewpoint.currentIndex())
        print(selected_vewpoint)
        if selected_vewpoint == 'None':
            self.mpDB.edit_row('roi', self.rid, {"viewpoint": None}, quiet=False)
        else:
            self.mpDB.edit_row('roi', self.rid, {"viewpoint": int(selected_vewpoint)})

    def favorite(self):
        media_id = self.roi_data.at[0, "media_id"]
        if self.button_favorite.isChecked():
            self.button_favorite.setStyleSheet(""" QPushButton { background-color: #b51b32; color: white; }""")
            self.mpDB.edit_row('media', media_id, {"favorite": 1})
        else:
            self.button_favorite.setStyleSheet("")
            self.mpDB.edit_row('media', media_id, {"favorite": 0})

    def new_individual(self):
        dialog = IndividualFillPopup(self)
        if dialog.exec():
            individual_id = self.mpDB.add_individual(dialog.get_name(),
                                                     dialog.get_species_id(),
                                                     dialog.get_sex(),
                                                     dialog.get_age())
            self.mpDB.edit_row('roi', self.rid, {"individual_id": individual_id})
        # reload data
        self.refresh_names()
        self.roi_data = self.load()
        self.refresh_values()

    def new_species(self):
        dialog = SpeciesFillPopup(self)
        if dialog.exec():
            species_id = self.mpDB.add_species(dialog.get_binomen(),
                                               dialog.get_common())
            self.mpDB.edit_row('roi', self.rid, {"species_id": species_id})
        # reload data
        self.refresh_species()
        self.roi_data = self.load()
        self.refresh_values()
