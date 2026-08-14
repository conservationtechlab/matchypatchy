"""
Edit The Metadata of Given Media/ROIs

"""
import pandas as pd
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel, QDialogButtonBox, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal

from matchypatchy.gui.dialogs.popup_individual import IndividualFillPopup
from matchypatchy.gui.widgets.widget_media import MediaWidget
from matchypatchy.gui.dialogs.popup_alert import AlertPopup
from matchypatchy.gui.widgets.gui_assets import HorizontalSeparator, TextEditWithSignal

from matchypatchy.threads.model_download_thread import load_model
from matchypatchy.database.media import fetch_individual, get_roi_bbox, EditObject
from matchypatchy.database.location import fetch_station_names_from_id
from matchypatchy.database.thumbnails import save_roi_thumbnail
from matchypatchy import config


class MediaEditPopup(QDialog):
    """Popup for viewing and editing media/ROI metadata"""
    roi_updated = pyqtSignal()  # Signal to notify that ROI has been updated

    def __init__(self, parent, data, data_type, current_image_index=0, crop=False):
        super().__init__(parent)
        self.parent = parent
        # image roi == 1
        if data_type == 1:
            self.setWindowTitle("View ROI")
            self.adjust_mode = 'zoom'
        # media or video == 0
        else:
            self.setWindowTitle("View Media")
            self.adjust_mode = 'bbox'
        self.setFixedSize(1000, 500)
        self.mpDB = parent.mpDB
        self.data = data
        self.data_type = data_type
        self.ids = data["id"].tolist()
        self.crop = crop
        self.current_image_index = current_image_index
        self.individuals = []
        self.new_bbox = None

        # edit stack
        self.edit_stack = []

        # Layout ---------------------------------------------------------------
        container_layout = QVBoxLayout()
        top = QHBoxLayout()
        # Filepath
        self.filepath = QLabel()
        top.addWidget(self.filepath, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        # Favorite
        self.button_favorite = QPushButton("♥")
        self.button_favorite.setFixedWidth(30)
        self.button_favorite.setCheckable(True)
        self.button_favorite.clicked.connect(self.favorite)
        if self.data_type == 1:
            top.addWidget(self.button_favorite, 0, alignment=Qt.AlignmentFlag.AlignRight)
        container_layout.addLayout(top)

        # Image ----------------------------------------------------------------
        content_layout = QHBoxLayout()
        self.image = MediaWidget(adjust_mode=self.adjust_mode)
        self.image.new_bbox.connect(self.capture_new_bbox)
        content_layout.addWidget(self.image, 1)
        # Metadata
        self.metadatapanel = MetadataPanel(self)
        self.metadatapanel.edit_signal.connect(self.on_edit_received)
        content_layout.addWidget(self.metadatapanel, 1)
        container_layout.addLayout(content_layout)
        container_layout.addStretch()

        # Bottom Buttons -------------------------------------------------------
        button_layout = QHBoxLayout()
        # previous/next buttons
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

        button_layout.addWidget(HorizontalSeparator())

        self.edit_btn = QPushButton("Edit ROI")
        self.edit_btn.clicked.connect(self.edit_roi)
        self.edit_btn.setCheckable(True)
        button_layout.addWidget(self.edit_btn)

        self.save_roi_btn = QPushButton("Save ROI")
        self.save_roi_btn.clicked.connect(self.save_roi)
        self.save_roi_btn.setEnabled(False)
        button_layout.addWidget(self.save_roi_btn)

        self.reset_btn = QPushButton("Reset Image")
        self.reset_btn.clicked.connect(self.reset)
        button_layout.addWidget(self.reset_btn)

        # Delete button
        self.delete_btn = QPushButton("Delete Image")
        self.delete_btn.clicked.connect(self.delete)
        button_layout.addWidget(self.delete_btn)

        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.save)
        buttonBox.rejected.connect(self.close_out)
        container_layout.addLayout(button_layout)
        self.setLayout(container_layout)

        # Initial Load
        self.refresh()

    def closeEvent(self, event):
        """user pressed 'x' to close window"""
        self.close_out()

    def save(self):
        """Save edits and close"""
        # stop video if playing
        self.image.player.stop()
        self.accept()

    def on_edit_received(self, edit):
        """Receive edit from MetadataPanel and append to edit_stack"""
        self.edit_stack.append(edit)

    def get_edit_stack(self):
        """Get the stack of edits made in the metadata panel"""
        # add comment change if applicable
        return self.edit_stack

    def close_out(self):
        """Close without saving"""
        # stop video if playing
        self.image.player.stop()
        self.reject()

    def refresh(self):
        """Load current image and metadata"""
        # load image
        current_filepath = self.data.iloc[self.current_image_index]["filepath"]

        self.filepath.setText(current_filepath)
        self.check_favorite()
        self.image_counter_label.setText(f"{self.current_image_index + 1} / {len(self.ids)}")

        frame = self.data.iloc[self.current_image_index]['frame'] if 'frame' in self.data.columns else None
        if pd.isna(frame):
            frame = None

        self.image.load(current_filepath,
                        bbox=get_roi_bbox(self.data.iloc[[self.current_image_index]]),
                        frame=frame,
                        crop=False)
        # display data
        self.metadatapanel.refresh_values(self.current_image_index)

    def favorite(self):
        """Toggle favorite status of current ROI"""
        rid = self.data.iloc[self.current_image_index]["id"]  # roi
        if self.button_favorite.isChecked():
            self.button_favorite.setStyleSheet(""" QPushButton { background-color: #b51b32; color: white; }""")
            self.mpDB.edit_row('roi', rid, {"favorite": 1})
        else:
            self.button_favorite.setStyleSheet("")
            self.mpDB.edit_row('roi', rid, {"favorite": 0})

    def check_favorite(self):
        """Check and update favorite button status"""
        if self.data_type != 1:
            # disable favorite button for media-only
            self.button_favorite.setDisabled(True)
            return
        favorite = self.data.iloc[self.current_image_index]["favorite"]
        if favorite == 1:
            self.button_favorite.setChecked(True)
            self.button_favorite.setStyleSheet(""" QPushButton { background-color: #b51b32; color: white; }""")
        else:
            self.button_favorite.setChecked(False)
            self.button_favorite.setStyleSheet("")

    def check_next_buttons(self):
        """Enable/disable next/previous buttons based on number of images"""
        if len(self.ids) > 1:
            self.next_btn.setEnabled(True)
            self.prev_btn.setEnabled(True)
        else:
            self.next_btn.setEnabled(False)
            self.prev_btn.setEnabled(False)

    def show_previous_image(self):
        """Show previous image in data"""
        self.current_image_index = (self.current_image_index - 1) % len(self.data)
        self.refresh()

    def show_next_image(self):
        """Show next image in data"""
        self.current_image_index = (self.current_image_index + 1) % len(self.data)
        self.refresh()

    def edit_roi(self):
        """Edit current ROI"""
        self.edit_btn.setChecked(True)
        self.image.enable_drawing_mode(True)

    def capture_new_bbox(self, bbox):
        """Capture the new bounding box from the image widget and enable save button"""
        self.new_bbox = bbox
        self.save_roi_btn.setEnabled(True)

    def save_roi(self):
        """Save the drawn ROI"""

        if self.new_bbox is not None:

            bbox_x = float(self.new_bbox['bbox_x'])
            bbox_y = float(self.new_bbox['bbox_y'])
            bbox_w = float(self.new_bbox['bbox_w'])
            bbox_h = float(self.new_bbox['bbox_h'])
            frame = int(self.new_bbox['frame'])

            # Check if the current data row has an existing ROI ID
            try: 
                media_id = self.data.iloc[self.current_image_index]["media_id"]  # roi
                rid = self.data.iloc[self.current_image_index]["id"]
                if pd.isna(rid):
                    rid = None
            except KeyError:
                media_id = self.data.iloc[self.current_image_index]["id"]  # media only

                rid = None

            if rid is not None:
                prompt = "This will update the existing ROI. You will need to rerun step 2. Process to get new embeddings."
                dialog = AlertPopup(self, prompt=prompt)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.mpDB.edit_row('roi',
                                       int(rid),
                                       {"bbox_x": bbox_x,
                                        "bbox_y": bbox_y,
                                        "bbox_w": bbox_w,
                                        "bbox_h": bbox_h,})

                    
                    # save thumbnail
                    roi_thumbnail = save_roi_thumbnail(config.load_cfg('THUMBNAIL_DIR'),
                                                       self.data.iloc[self.current_image_index]["filpath"],
                                                       self.data.iloc[self.current_image_index]["ext"], 
                                                       frame,
                                                       bbox_x, bbox_y, bbox_w, bbox_h)
                    # delete old thumbnail if exists
                    self.mpDB.delete('roi_thumbnails', f"fid={rid}")
                    # add new thumbnail
                    self.mpDB.add_thumbnail("roi", rid, roi_thumbnail)
                    
                del dialog

            else:
                prompt = "This will create a new ROI. You will need to rerun step 2. Process to get new embeddings."
                dialog = AlertPopup(self, prompt=prompt)

                if dialog.exec() == QDialog.DialogCode.Accepted:
                    # do not add emb_id, to be determined later
                    roi_id = self.mpDB.add_roi(int(media_id),
                                               int(frame),
                                               bbox_x, bbox_y, bbox_w, bbox_h)

                    # save thumbnail
                    roi_thumbnail = save_roi_thumbnail(config.load_cfg('THUMBNAIL_DIR'),
                                                       self.data.iloc[self.current_image_index]["filepath"],
                                                       self.data.iloc[self.current_image_index]["ext"],
                                                       frame, bbox_x, bbox_y, bbox_w, bbox_h)

                    self.mpDB.add_thumbnail("roi", roi_id, roi_thumbnail)


                del dialog

            # turn off drawing mode and disable save button
            self.image.enable_drawing_mode(False)
            self.edit_btn.setChecked(False)
            self.save_roi_btn.setEnabled(False)

    def reset(self):
        """Reset the image to its original state"""
        self.new_bbox = None
        self.image.reset()

    def delete(self):
        """Delete current ROI"""
        dialog = AlertPopup(self, prompt="Are you sure you want to delete this ROI? This action cannot be undone.")
        if dialog.exec():
            rid = self.data.iloc[self.current_image_index]["id"]  # roi
            self.mpDB.delete('roi', f"id={rid}")
            self.mpDB.delete_emb(id=rid)

            self.data = self.data.drop(self.data.index[self.current_image_index]).reset_index(drop=True)
            self.rids = self.data["id"].tolist()

            # close if no more images left
            if len(self.data) == 0:
                self.parent.load_table()
                self.close()
                return

            if self.current_image_index >= len(self.data):
                self.current_image_index = len(self.data) - 1

        del dialog


class MetadataPanel(QWidget):
    """Panel for displaying and editing metadata of media/ROIs"""
    edit_signal = pyqtSignal(EditObject)  # Signal to send edits to parent

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.mpDB = parent.mpDB
        self.data = parent.data
        self.ids = parent.ids
        self.data_type = parent.data_type
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
        # Viewpoint - EDITABLE
        viewpoint_layout = QHBoxLayout()
        viewpoint_label = QLabel("Viewpoint: ")
        viewpoint_label.setFixedWidth(horizontal_gap)
        viewpoint_layout.addWidget(viewpoint_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.VIEWPOINTS = load_model('VIEWPOINTS')
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
        self.comment = TextEditWithSignal()
        self.comment.setFixedHeight(60)
        self.comment.text_finished.connect(self.change_comment)
        comment.addWidget(self.comment, 1)
        comment.addStretch()
        metadata_layout.addLayout(comment)
        metadata_layout.addStretch()

        self.setLayout(metadata_layout)

    def refresh_values(self, current_image_index):
        """Refresh metadata values based on current image index"""
        # disable comboboxes
        self.name.blockSignals(True)
        self.age.blockSignals(True)
        self.sex.blockSignals(True)
        self.viewpoint.blockSignals(True)
        self.comment.blockSignals(True)

        # update lists
        self.individuals = fetch_individual(self.mpDB)
        self.name.clear()
        self.name_list = ["Unknown"] + [el for el in self.individuals["name"]]
        self.name.addItems(self.name_list)
        self.timestamp_data.setText(str(self.data.iloc[current_image_index]["timestamp"]))
        survey_info = fetch_station_names_from_id(self.mpDB, self.data.iloc[current_image_index]["station_id"])
        self.station_data.setText(str(survey_info['station_name']))
        self.survey_data.setText(str(survey_info["survey_name"]))
        self.region_data.setText(str(survey_info["region_name"]))
        self.sequence_data.setText(str(self.data.iloc[current_image_index]["sequence_id"]))
        self.external_data.setText(str(self.data.iloc[current_image_index]["external_id"]))

        if self.data_type == 1:
            # Name
            iid = self.data.iloc[current_image_index]["individual_id"] if {"individual_id"}.issubset(self.data.columns) else 0
            if iid == 0 or iid is None or pd.isna(iid):
                # media only, no individual column
                self.name.setCurrentIndex(0)
                self.age.setDisabled(True)
                self.sex.setDisabled(True)
            else:
                name_index = self.name.findText(self.individuals.loc[iid, 'name'])
                self.name.setCurrentIndex(name_index)
                self.sex.setDisabled(False)
                self.age.setDisabled(False)

            self.set_sex_combobox(current_image_index)
            self.set_age_combobox(current_image_index)
            self.set_viewpoint_combobox(current_image_index)

        # media only
        else:
            self.name.setCurrentIndex(0)
            self.name.setDisabled(True)
            self.sex.setDisabled(True)
            self.age.setDisabled(True)
            self.viewpoint.setDisabled(True)
            self.add_individual.setDisabled(True)

        # Comment
        self.comment.setText(str(self.data.iloc[current_image_index]["comment"]))

        # renable comboboxes
        self.name.blockSignals(False)
        self.age.blockSignals(False)
        self.sex.blockSignals(False)
        self.viewpoint.blockSignals(False)
        self.comment.blockSignals(False)

    def send_edit(self, edit):
        """Send edit to parent popup"""
        self.edit_signal.emit(edit)

    # Set Boxes -------------------------------------------------------------
    def set_sex_combobox(self, current_image_index):
        self.sex.clear()
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

    def set_age_combobox(self, current_image_index):
        self.age.clear()
        if len(self.ids) > 1:
            self.age.addItems(['— Mixed —', 'Unknown', 'Juvenile', 'Subadult', 'Adult'])
            unique_ages = self.data["age"].dropna().unique() if {"age"}.issubset(self.data.columns) else []
            if len(unique_ages) == 0:
                self.age.setCurrentIndex(1)  # 'Unknown'
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

    def set_viewpoint_combobox(self, current_image_index):
        self.viewpoint.clear()
        if len(self.ids) > 1:
            self.viewpoint.addItems(['— Mixed —'] + list(self.VIEWPOINTS.values())[1:])  # skip 'any'
            unique_viewpoints = self.data["viewpoint"].dropna().unique() if {"viewpoint"}.issubset(self.data.columns) else []
            if len(unique_viewpoints) == 0:
                self.viewpoint.setCurrentIndex(self.viewpoint.findText('None'))
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
                self.viewpoint.setCurrentIndex(0)
            elif viewpoint == 'None' or viewpoint is None or viewpoint == 'nan':
                self.viewpoint.setCurrentIndex(0)
            else:
                current_viewpoint = self.VIEWPOINTS[viewpoint]
                self.viewpoint.setCurrentIndex(self.viewpoint.findText(current_viewpoint))

    # Edits --------------------------------------------------------------------
    def change_name(self):
        if self.name.currentIndex() > 0:
            iid = self.individuals.loc[self.individuals["name"] == self.name_list[self.name.currentIndex()]].index.item()
            for row in self.data.itertuples():
                edit = EditObject(rid=row.id,
                                  mid=row.media_id,
                                  reference='individual_id',
                                  previous_value=row.individual_id,
                                  new_value=iid)
                self.send_edit(edit)

            self.sex.setCurrentIndex(self.sex.findText(str(self.individuals.loc[iid, 'sex'])))
            self.sex.setDisabled(False)
            self.age.setCurrentIndex(self.age.findText(str(self.individuals.loc[iid, 'age'])))
            self.age.setDisabled(False)
        else:
            dialog = AlertPopup(self, "Are you sure you want to set the name to 'Unknown'?\nThis will remove the ID assignment from the selected ROI(s).")
            if dialog.exec():
                for row in self.data.itertuples():
                    edit = EditObject(rid=row.id,
                                      mid=row.media_id,
                                      reference='individual_id',
                                      previous_value=row.individual_id,
                                      new_value=None)
                    self.send_edit(edit)
            self.sex.setCurrentIndex(0)
            self.sex.setDisabled(True)
            self.age.setCurrentIndex(0)
            self.age.setDisabled(True)

    def change_sex(self):
        """Update sex for all selected ROIs"""
        # updates individual table when transposed
        if self.name.currentIndex() > 0:
            for row in self.data.itertuples():
                edit = EditObject(rid=row.id,
                                  mid=row.media_id,
                                  reference='sex',
                                  previous_value=row.sex,
                                  new_value=self.age.currentText())
                self.send_edit(edit)

    def change_age(self):
        """Update age for all selected ROIs"""
        # updates individual table when transposed
        if self.name.currentIndex() > 0:
            for row in self.data.itertuples():
                edit = EditObject(rid=row.id,
                                  mid=row.media_id,
                                  reference='age',
                                  previous_value=row.age,
                                  new_value=self.age.currentText())
                self.send_edit(edit)

    def change_viewpoint(self):
        """Update viewpoint for all selected ROIs"""
        viewpoint_keys = list(self.VIEWPOINTS.keys())
        if len(self.ids) > 1:
            selected_viewpoint = viewpoint_keys[self.viewpoint.currentIndex()]
        else:
            selected_viewpoint = viewpoint_keys[self.viewpoint.currentIndex() + 1]

        if selected_viewpoint == 'Any':
            return
        elif selected_viewpoint == 'None':
            selected_viewpoint = None
        else:
            selected_viewpoint = int(selected_viewpoint)
    
        for row in self.data.itertuples():

            edit = EditObject(rid=row.id,
                              mid=row.media_id,
                              reference='viewpoint',
                              previous_value=row.viewpoint,
                              new_value=selected_viewpoint)
            self.send_edit(edit)

    def change_comment(self):
        """Update comment for all selected ROIS/media"""
        for row in self.data.itertuples():

            # for media-only rows, use id as media_id
            media_id = int(row.media_id) if 'media_id' in self.data.columns else int(row.id)  

            edit = EditObject(rid=None,
                              mid=media_id,
                              reference='comment',
                              previous_value=str(row.comment),
                              new_value=self.comment.toPlainText())
            self.send_edit(edit)

    def new_individual(self):
        dialog = IndividualFillPopup(self)
        if dialog.exec():
            individual_id = self.mpDB.add_individual(dialog.get_name(),
                                                     dialog.get_sex(),
                                                     dialog.get_age())
            for rid in self.ids:
                self.mpDB.edit_row('roi', rid, {"individual_id": individual_id})
        # reload data
        self.refresh_values(self.parent.current_image_index)
        self.name.setCurrentIndex(self.name.count() - 1)  # select new individual
