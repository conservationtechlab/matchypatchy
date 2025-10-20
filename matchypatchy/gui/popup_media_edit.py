"""
Edit A Single Image

"""
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel, QTextEdit, QDialogButtonBox, QPushButton)
from PyQt6.QtCore import Qt

from matchypatchy.gui.popup_species import SpeciesFillPopup
from matchypatchy.gui.popup_individual import IndividualFillPopup
from matchypatchy.gui.widget_media import MediaWidget
from matchypatchy.gui.gui_assets import HorizontalSeparator

from matchypatchy.algo.models import load
import matchypatchy.database.media as db_roi
from matchypatchy.database.species import fetch_individual
from matchypatchy.database.location import fetch_station_names_from_id


class MediaEditPopup(QDialog):
    def __init__(self, parent, data, data_type, current_image_index=0, crop=False):
        super().__init__(parent)
        self.setWindowTitle("View ROI")
        self.setFixedSize(1000, 500)
        self.mpDB = parent.mpDB
        self.data = data
        self.data_type = data_type
        self.ids = data["id"].tolist()
        self.crop = crop
        self.current_image_index = current_image_index
        self.individuals = []
        self.species_list = []

        # Layout ---------------------------------------------------------------
        container_layout = QVBoxLayout()

        # Title Bar
        top = QHBoxLayout()
        # Filepath
        self.filepath = QLabel()
        top.addWidget(self.filepath, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        # Favorite
        self.button_favorite = QPushButton("♥")
        self.button_favorite.setFixedWidth(30)
        self.button_favorite.setCheckable(True)
        self.button_favorite.clicked.connect(self.favorite)
        top.addWidget(self.button_favorite, 0, alignment=Qt.AlignmentFlag.AlignRight)
        container_layout.addLayout(top)

        # Image ----------------------------------------------------------------
        content_layout = QHBoxLayout()
        self.image = MediaWidget()
        content_layout.addWidget(self.image, 1)
        # Metadata
        self.metadatapanel = MetadataPanel(self.mpDB, self.data, self.ids)
        content_layout.addWidget(self.metadatapanel, 1)
        container_layout.addLayout(content_layout)
        container_layout.addStretch()

        # Bottom Buttons -------------------------------------------------------
        button_layout = QHBoxLayout()

        self.prev_btn = QPushButton("Previous")
        self.prev_btn.clicked.connect(self.show_previous_image)

        button_layout.addWidget(self.prev_btn)
        # Image index label (e.g., "1/32")
        self.image_counter_label = QLabel()
        button_layout.addWidget(self.image_counter_label, 0)
        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self.show_next_image)
        button_layout.addWidget(self.next_btn)
        self.check_next_buttons()

        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.save)
        buttonBox.rejected.connect(self.close_out)
        container_layout.addLayout(button_layout)
        self.setLayout(container_layout)

        self.refresh()

    def closeEvent(self, event):
        # user pressed 'x' to close window
        self.close_out()

    def save(self):
        # stop video if playing
        self.image.player.stop()
        self.accept()

    def get_edit_stack(self):
        edit_stack = self.metadatapanel.edit_stack
        # add comment change if applicable
        if self.metadatapanel.comment_changed:
            for id in self.ids:
                if self.data_type == 1:
                    media_id = self.data[self.data["id"] == id]["media_id"].item()
                else:
                    media_id = id
                edit = {'id': media_id,
                        'reference': 'comment',
                        'previous_value': self.data[self.data["id"] == id]["comment"].item(),
                        'new_value': self.metadatapanel.comment.toPlainText()}
                edit_stack.append(edit)
        return edit_stack

    def close_out(self):
        # stop video if playing
        self.image.player.stop()
        self.reject()

    def refresh(self):
        # load image
        self.filepath.setText(self.data.iloc[self.current_image_index]["filepath"])
        self.check_favorite()
        self.image_counter_label.setText(f"{self.current_image_index + 1} / {len(self.ids)}")  
        self.image.load(self.data.iloc[self.current_image_index]["filepath"],
                        bbox=db_roi.get_bbox(self.data.iloc[[self.current_image_index]]),
                        frame=db_roi.get_frame(self.data.iloc[[self.current_image_index]]),
                        crop=False)
        # display data
        self.metadatapanel.refresh_names()
        self.metadatapanel.refresh_values(self.current_image_index)

    def favorite(self):
        rid = self.data.iloc[self.current_image_index]["id"]  # roi
        if self.button_favorite.isChecked():
            self.button_favorite.setStyleSheet(""" QPushButton { background-color: #b51b32; color: white; }""")
            self.mpDB.edit_row('roi', rid, {"favorite": 1})
        else:
            self.button_favorite.setStyleSheet("")
            self.mpDB.edit_row('roi', rid, {"favorite": 0})

    def check_favorite(self):
        favorite = self.data.iloc[self.current_image_index]["favorite"]
        if favorite == 1:
            self.button_favorite.setChecked(True)
            self.button_favorite.setStyleSheet(""" QPushButton { background-color: #b51b32; color: white; }""")
        else:
            self.button_favorite.setChecked(False)
            self.button_favorite.setStyleSheet("")

    def check_next_buttons(self):
        if len(self.ids) > 1:
            self.next_btn.setEnabled(True)
            self.prev_btn.setEnabled(True)
        else:
            self.next_btn.setEnabled(False)
            self.prev_btn.setEnabled(False)

    def show_previous_image(self):
        self.current_image_index = (self.current_image_index - 1) % len(self.data)
        self.refresh()

    def show_next_image(self):
        self.current_image_index = (self.current_image_index + 1) % len(self.data)
        self.refresh()


class MetadataPanel(QWidget):
    def __init__(self, mpDB, data, ids):
        super().__init__()
        self.mpDB = mpDB
        self.data = data
        self.ids = ids
        horizontal_gap = 80
        vertical_gap = 8
        # handle comment change only after editing is done
        self.comment_changed = False
        self.edit_stack = []

        # Layout ---------------------------------------------------------------
        metadata_layout = QVBoxLayout()

        # Timestamp
        timestamp = QHBoxLayout()
        timestamp_label = QLabel("Timestamp: ")
        timestamp_label.setFixedWidth(horizontal_gap)
        timestamp.addWidget(timestamp_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.timestamp_data = QLabel()
        timestamp.addWidget(self.timestamp_data, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        metadata_layout.addLayout(timestamp)
        metadata_layout.addSpacing(vertical_gap)
        # Station
        station = QHBoxLayout()
        station_label = QLabel("Station: ")
        station_label.setFixedWidth(horizontal_gap)
        station.addWidget(station_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.station_data = QLabel()
        station.addWidget(self.station_data, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        metadata_layout.addLayout(station)
        metadata_layout.addSpacing(vertical_gap)
        # Survey
        survey = QHBoxLayout()
        survey_label = QLabel("Survey: ")
        survey_label.setFixedWidth(horizontal_gap)
        survey.addWidget(survey_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.survey_data = QLabel()
        survey.addWidget(self.survey_data, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        metadata_layout.addLayout(survey)
        metadata_layout.addSpacing(vertical_gap)
        # Region
        region = QHBoxLayout()
        region_label = QLabel("Region: ")
        region_label.setFixedWidth(horizontal_gap)
        region.addWidget(region_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.region_data = QLabel()
        region.addWidget(self.region_data, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        metadata_layout.addLayout(region)
        metadata_layout.addSpacing(vertical_gap)
        # Sequence ID
        sequence = QHBoxLayout()
        sequence_label = QLabel("Sequence ID: ")
        sequence_label.setFixedWidth(horizontal_gap)
        sequence.addWidget(sequence_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.sequence_data = QLabel()
        sequence.addWidget(self.sequence_data, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        metadata_layout.addLayout(sequence)
        metadata_layout.addSpacing(vertical_gap)
        # External ID
        external = QHBoxLayout()
        external_label = QLabel("External ID: ")
        external_label.setFixedWidth(horizontal_gap)
        external.addWidget(external_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.external_data = QLabel()
        external.addWidget(self.external_data, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        metadata_layout.addLayout(external)
        metadata_layout.addSpacing(int(vertical_gap / 2))

        # Divider
        metadata_layout.addWidget(HorizontalSeparator(linewidth=2))
        metadata_layout.addSpacing(int(vertical_gap / 2))

        # EDITABLE -------------------------------------------------------------
        # Name - EDITABLE
        name_layout = QHBoxLayout()
        name_label = QLabel("Name: ")
        name_label.setFixedWidth(horizontal_gap)
        name_layout.addWidget(name_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.name = QComboBox()
        self.name.currentIndexChanged.connect(self.change_name)
        name_layout.addWidget(self.name, stretch=1)
        self.add_individual = QPushButton("+")
        self.add_individual.pressed.connect(self.new_individual)
        name_layout.addWidget(self.add_individual)
        metadata_layout.addLayout(name_layout)
        metadata_layout.addSpacing(vertical_gap)
        # Sex - EDITABLE
        sex_layout = QHBoxLayout()
        sex_label = QLabel("Sex: ")
        sex_label.setFixedWidth(horizontal_gap)
        sex_layout.addWidget(sex_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.sex = QComboBox()
        self.sex.currentIndexChanged.connect(self.change_sex)
        sex_layout.addWidget(self.sex, stretch=1)
        metadata_layout.addLayout(sex_layout)
        metadata_layout.addSpacing(vertical_gap)
        # Age - EDITABLE
        age_layout = QHBoxLayout()
        age_label = QLabel("Age: ")
        age_label.setFixedWidth(horizontal_gap)
        age_layout.addWidget(age_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.age = QComboBox()
        self.age.currentIndexChanged.connect(self.change_age)
        age_layout.addWidget(self.age, stretch=1)
        metadata_layout.addLayout(age_layout)
        metadata_layout.addSpacing(vertical_gap)
        # Species - EDITABLE
        species_layout = QHBoxLayout()
        species_label = QLabel("Species: ")
        species_label.setFixedWidth(horizontal_gap)
        species_layout.addWidget(species_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.species = QComboBox()
        self.refresh_species()
        self.species.currentIndexChanged.connect(self.change_species)
        species_layout.addWidget(self.species, stretch=1)
        self.button_add_species = QPushButton("+")
        self.button_add_species.pressed.connect(self.new_species)
        species_layout.addWidget(self.button_add_species)
        metadata_layout.addLayout(species_layout)
        metadata_layout.addSpacing(vertical_gap)
        # Viewpoint - EDITABLE
        viewpoint_layout = QHBoxLayout()
        viewpoint_label = QLabel("Viewpoint: ")
        viewpoint_label.setFixedWidth(horizontal_gap)
        viewpoint_layout.addWidget(viewpoint_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.VIEWPOINTS = load('VIEWPOINTS')
        self.viewpoint = QComboBox()
        self.viewpoint.currentIndexChanged.connect(self.change_viewpoint)
        viewpoint_layout.addWidget(self.viewpoint, 1)
        metadata_layout.addLayout(viewpoint_layout)
        metadata_layout.addSpacing(vertical_gap)
        # Comment - EDITABLE
        comment = QHBoxLayout()
        comment_label = QLabel("Comment: ")
        comment_label.setFixedWidth(horizontal_gap)
        comment.addWidget(comment_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.comment = QTextEdit()
        self.comment.setFixedHeight(60)
        self.comment.textChanged.connect(self.change_comment)
        comment.addWidget(self.comment, 1)
        comment.addStretch()
        metadata_layout.addLayout(comment)
        metadata_layout.addStretch()

        self.setLayout(metadata_layout)

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

    def refresh_values(self, current_image_index):
        # disable comboboxes
        self.name.blockSignals(True)
        self.age.blockSignals(True)
        self.sex.blockSignals(True)
        self.species.blockSignals(True)
        self.viewpoint.blockSignals(True)

        self.timestamp_data.setText(str(self.data.iloc[current_image_index]["timestamp"]))
        survey_info = fetch_station_names_from_id(self.mpDB, self.data.iloc[current_image_index]["station_id"])
        self.station_data.setText(str(survey_info['station_name']))
        self.survey_data.setText(str(survey_info["survey_name"]))
        self.region_data.setText(str(survey_info["region_name"]))
        self.sequence_data.setText(str(self.data.iloc[current_image_index]["sequence_id"]))
        self.external_data.setText(str(self.data.iloc[current_image_index]["external_id"]))

        # Name
        iid = self.data.iloc[current_image_index]["individual_id"] if {"individual_id"}.issubset(self.data.columns) else 0
        if iid == 0:
            # media only, no individual column
            self.name.setCurrentIndex(0)
            self.name.setDisabled(True)
            self.age.setDisabled(True)
            self.sex.setDisabled(True)
        elif iid is None:
            self.name.setCurrentIndex(0)
            self.sex.setDisabled(True)
            self.age.setDisabled(True)
        else:
            self.name.setCurrentIndex(iid)
            self.sex.setDisabled(False)
            self.age.setDisabled(False)

        # Sex
        if len(self.ids) > 1:
            self.sex.addItems(['— Mixed —', 'Unknown', 'Male', 'Female'])
            unique_sexes = self.data["sex"].dropna().unique() if {"sex"}.issubset(self.data.columns) else []
            if len(unique_sexes) == 0:
                self.sex.setCurrentIndex(self.sex.findText('Unknown'))
            elif len(unique_sexes) == 1:
                sex_text = unique_sexes[0]
                self.sex.setCurrentIndex(self.sex.findText(str(sex_text)))
            else:
                self.sex.setCurrentIndex(0)  # '— Mixed —'
        else:
            self.sex.addItems(['Unknown', 'Male', 'Female'])
            current_sex = self.data.iloc[current_image_index]["sex"] if {"sex"}.issubset(self.data.columns) else None
            if current_sex is None:
                self.sex.setCurrentIndex(0)
            else:
                self.sex.setCurrentIndex(self.sex.findText(str(current_sex)))
        # Age
        if len(self.ids) > 1:
            self.age.addItems(['— Mixed —', 'Unknown', 'Juvenile', 'Subadult', 'Adult'])
            unique_ages = self.data["age"].dropna().unique() if {"age"}.issubset(self.data.columns) else []
            if len(unique_ages) == 0:
                self.age.setCurrentIndex(1) # 'Unknown'
            elif len(unique_ages) == 1:
                age_text = unique_ages[0]
                self.age.setCurrentIndex(self.age.findText(str(age_text)))
            else:
                self.age.setCurrentIndex(0)  # '— Mixed —'
        else:
            self.age.addItems(['Unknown', 'Juvenile', 'Subadult', 'Adult'])
            current_age = self.data.iloc[current_image_index]["age"] if {"age"}.issubset(self.data.columns) else None
            if current_age is None:
                self.age.setCurrentIndex(0)
            else:
                self.age.setCurrentIndex(self.age.findText(str(current_age)))

        # Species
        self.species.setDisabled(False)
        self.button_add_species.setDisabled(False)
        current_species = self.data.iloc[current_image_index]["common"] if {"common"}.issubset(self.data.columns) else 0
        if current_species == 0:
            # media only, no species column
            self.species.setCurrentIndex(0)
            self.species.setDisabled(True)
            self.button_add_species.setDisabled(True)
        elif current_species == None:
            self.species.setCurrentIndex(0)
        else:
            self.species.setCurrentIndex(self.species.findText(str(current_species)))

        # Viewpoint
        self.viewpoint.setDisabled(False)
        if len(self.ids) > 1:
            self.viewpoint.addItems(['— Mixed —'] + list(self.VIEWPOINTS.values())[1:])  # skip 'any'
            unique_viewpoints = self.data["viewpoint"].dropna().unique() if {"viewpoint"}.issubset(self.data.columns) else []
            if len(unique_viewpoints) == 0:
                # viewpoint not in columns, media only
                self.viewpoint.setCurrentIndex(self.viewpoint.findText('None'))
                self.viewpoint.setDisabled(True)
            elif len(unique_viewpoints) == 1:
                viewpoint_key = str(unique_viewpoints[0])
                viewpoint_text = self.VIEWPOINTS[viewpoint_key]
                self.viewpoint.setCurrentIndex(self.viewpoint.findText(str(viewpoint_text)))
            else:
                self.viewpoint.setCurrentIndex(0)  # '— Mixed —'
        else:
            self.viewpoint.addItems(list(self.VIEWPOINTS.values())[1:])  # skip 'any'
            viewpoint = str(self.data.iloc[current_image_index]["viewpoint"]) if {"viewpoint"}.issubset(self.data.columns) else -1
            if viewpoint == -1:
                # no viewpoint column, media only
                self.setDisabled(True)
                self.viewpoint.setCurrentIndex(0)
            elif viewpoint == 'None' or viewpoint is None or viewpoint == 'nan':
                self.viewpoint.setCurrentIndex(0)
            else:
                current_viewpoint = self.VIEWPOINTS[viewpoint]
                self.viewpoint.setCurrentIndex(self.viewpoint.findText(current_viewpoint))

        # Comment
        self.comment.setText(str(self.data.iloc[current_image_index]["comment"]))

        # renable comboboxes
        self.name.blockSignals(False)
        self.age.blockSignals(False)
        self.sex.blockSignals(False)
        self.species.blockSignals(False)
        self.viewpoint.blockSignals(False)


    # Edits --------------------------------------------------------------------
    def change_name(self):
        if self.name.currentIndex() > 0:
            selected_individual = self.individuals[self.individuals["name" ] == self.name_list[self.name.currentIndex()]]
            print(selected_individual)

            for id in self.ids:
                previous_value = self.data[self.data["id"] == id]["individual_id"].item()
                edit = {'id': id,
                        'reference': 'individual_id',
                        'previous_value': previous_value,
                        'new_value': selected_individual['id'].item()}
                self.edit_stack.append(edit)
            self.sex.setCurrentIndex(self.sex.findText(str(selected_individual['sex'].values[0])))
            self.sex.setDisabled(False)
            self.age.setCurrentIndex(self.age.findText(str(selected_individual['age'].values[0])))
            self.age.setDisabled(False)
        else:
            self.sex.setCurrentIndex(0)
            self.sex.setDisabled(True)
            self.age.setCurrentIndex(0)
            self.age.setDisabled(True)

    def change_sex(self):
        if self.name.currentIndex() > 0:
            iid = self.individuals.loc[self.individuals["name" ] == self.name_list[self.name.currentIndex()], 'id'].item()
            for id in self.ids:
                previous_value = self.data[self.data["id"] == id]["sex"].item()
                edit = {'id': id,
                        'reference': 'sex',
                        'previous_value': previous_value,
                        'new_value': self.sex.currentText()}
                print(edit)
                self.edit_stack.append(edit)

    def change_age(self):
        # updates individual table
        if self.name.currentIndex() > 0:
            iid = self.individuals.loc[self.individuals["name" ] == self.name_list[self.name.currentIndex()], 'id'].values[0]
            for id in self.ids:
                previous_value = self.data[self.data["id"] == id]["age"].item()
                edit = {'id': id,
                        'reference': 'age',
                        'previous_value': previous_value,
                        'new_value': self.age.currentText()}
                print(edit)
                self.edit_stack.append(edit)

    def change_species(self):
        selected_species = self.species_list[self.species.currentIndex()]
        if selected_species[0] > 0:
            for id in self.ids:
                edit = {'id': id,
                        'reference': 'species_id',
                        'previous_value': self.data[self.data["id"] == id]["species_id"].item(),
                        'new_value': selected_species[0]}
                print(edit)
                self.edit_stack.append(edit)

    def change_viewpoint(self):
        viewpoint_keys = list(self.VIEWPOINTS.keys())
        selected_viewpoint = viewpoint_keys[self.viewpoint.currentIndex() + 1]
        for id in self.ids:
            if selected_viewpoint == 'None':
                edit = {'id': id,
                        'reference': 'viewpoint',
                        'previous_value': self.data[self.data["id"] == id]["viewpoint"].item(),
                        'new_value': None}
            else:
                edit = {'id': id,
                        'reference': 'viewpoint',
                        'previous_value': self.data[self.data["id"] == id]["viewpoint"].item(),
                        'new_value': int(selected_viewpoint)}
            print(edit)
            self.edit_stack.append(edit)

    def change_comment(self):
        self.comment_changed = True

    def new_individual(self):
        dialog = IndividualFillPopup(self)
        if dialog.exec():
            individual_id = self.mpDB.add_individual(dialog.get_name(),
                                                     dialog.get_species_id(),
                                                     dialog.get_sex(),
                                                     dialog.get_age())
            for rid in self.ids:
                self.mpDB.edit_row('roi', rid, {"individual_id": individual_id})
        # reload data
        self.refresh_names()
        self.refresh_values()

    def new_species(self):
        dialog = SpeciesFillPopup(self)
        if dialog.exec():
            species_id = self.mpDB.add_species(dialog.get_binomen(),
                                               dialog.get_common())
            for rid in self.ids:
                self.mpDB.edit_row('roi', rid, {"species_id": species_id})
        # reload data
        self.refresh_species()
        self.refresh_values()