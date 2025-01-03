"""
GUI Window for Match Comparisons

TODO:
 - Add new individual ID to all rois in query sequence and all rois in match sequence
 - Likewise if merging
 - enable merge
 - ENABLE VIEWPOINT
 - image manipulation
"""
import pandas as pd
from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QLineEdit, QSlider, QToolTip)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QKeyEvent, QIntValidator

import matchypatchy.database.roi as db_roi
from matchypatchy.database.individual import merge

from matchypatchy.gui.widget_image import ImageWidget
from matchypatchy.gui.popup_alert import AlertPopup, ProgressPopup
from matchypatchy.gui.popup_individual import IndividualFillPopup
from matchypatchy.gui.popup_single_image import ImagePopup

from matchypatchy.ml.match_thread import MatchEmbeddingThread

MATCH_STYLE = """ QPushButton { background-color: #2e7031; color: white; }"""


class DisplayCompare(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.k = 3  # default knn
        self.threshold = 80
        self.mpDB = parent.mpDB

        self.neighbor_dict = dict()
        self.nearest_dict = dict()

        self.current_query = 0
        self.current_match = 0
        self.current_query_sn = 0

        # ROI REFERENCE
        self.current_query_rid = 0
        self.current_match_rid = 0

        layout = QVBoxLayout()

        # FIRST LAYER ----------------------------------------------------------
        first_layer = QHBoxLayout()
        button_home = QPushButton("Home")
        button_home.clicked.connect(self.home)
        first_layer.addWidget(button_home)
        first_layer.addSpacing(10)

        # Match Options
        first_layer.addWidget(QLabel("Max # of Matches:"), 0,
                              alignment=Qt.AlignmentFlag.AlignLeft)
        self.knn_number = QLineEdit(str(self.k))
        self.knn_number.setValidator(QIntValidator(0, 1000))
        self.knn_number.setToolTip('Maximum number of matches allowed per ROI (not per sequence)')
        self.knn_number.textChanged.connect(self.change_k)
        self.knn_number.setMaximumWidth(50)
        first_layer.addWidget(self.knn_number, 0,
                              alignment=Qt.AlignmentFlag.AlignLeft)

        first_layer.addWidget(QLabel("Distance Threshold:"), 0,
                              alignment=Qt.AlignmentFlag.AlignLeft)
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(1, 100)  # Set range from 1 to 100
        self.threshold_slider.setValue(self.threshold)  # Set initial value
        self.threshold_slider.valueChanged.connect(self.change_threshold)
        first_layer.addWidget(self.threshold_slider, 0,
                              alignment=Qt.AlignmentFlag.AlignLeft)

        button_recalc = QPushButton("Recalculate Matches")
        button_recalc.clicked.connect(self.calculate_neighbors)
        first_layer.addWidget(button_recalc)

        # Filters
        first_layer.addSpacing(20)
        first_layer.addWidget(QLabel("Filter:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # REGION
        self.region_select = QComboBox()
        self.region_select.setFixedWidth(200)
        # filter out null entries, duplicates, dict will be {Name: [surveyids]}
        self.region_list_ordered = [(0, 'Region')] + list(self.mpDB.select('region', columns='id, name'))
        self.region_select.addItems([el[1] for el in self.region_list_ordered])
        self.region_select.currentIndexChanged.connect(self.filter_region)
        first_layer.addWidget(self.region_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # SURVEY
        self.survey_select = QComboBox()
        self.survey_select.setFixedWidth(200)
        self.survey_list_ordered = [(0, 'Survey')] + list(self.mpDB.select('survey', columns='id, name'))
        self.survey_select.addItems([el[1] for el in self.survey_list_ordered])
        self.survey_select.currentIndexChanged.connect(self.filter_survey)
        first_layer.addWidget(self.survey_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # Site
        self.site_select = QComboBox()
        self.site_select.setFixedWidth(200)
        self.set_sites()
        self.site_select.currentIndexChanged.connect(self.filter_site)
        first_layer.addWidget(self.site_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        first_layer.addStretch()
        layout.addLayout(first_layer)


        # Image Comparison =====================================================
        layout.addSpacing(20)
        image_layout = QHBoxLayout()

        # QUERY ----------------------------------------------------------------
        query_layout = QVBoxLayout()
        query_label = QLabel("Query")
        query_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        query_layout.addWidget(query_label)
        # Options
        query_options = QHBoxLayout()
        query_options.addStretch()
        # # Query Number
        query_options.addWidget(QLabel("Query Image:"))
        self.button_previous_query = QPushButton("<<")
        self.button_previous_query.setMaximumWidth(40)
        self.button_previous_query.clicked.connect(lambda: self.set_query(self.current_query - 1))
        query_options.addWidget(self.button_previous_query)
        self.query_number = QLineEdit(str(self.current_query + 1))
        self.query_number.setMaximumWidth(100)
        query_options.addWidget(self.query_number)
        self.query_n = QLabel("/9")
        query_options.addWidget(self.query_n)
        self.button_next_query = QPushButton(">>")
        self.button_next_query.setMaximumWidth(40)
        self.button_next_query.clicked.connect(lambda: self.set_query(self.current_query + 1))
        query_options.addWidget(self.button_next_query)
        # Viewpoint Toggle
        self.button_viewpoint = QPushButton("L/R")
        self.button_viewpoint.clicked.connect(self.toggle_viewpoint)
        self.button_viewpoint.setMaximumWidth(50)
        query_options.addWidget(self.button_viewpoint)
        # # Sequence Number
        query_options.addWidget(QLabel("Sequence:"))
        self.button_previous_query_seq = QPushButton("<<")
        self.button_previous_query_seq.setMaximumWidth(40)
        self.button_previous_query_seq.clicked.connect(lambda: self.set_within_query_sequence(self.current_query_sn - 1))
        query_options.addWidget(self.button_previous_query_seq)
        self.query_seq_number = QLineEdit(str(self.current_query_sn + 1))
        self.query_seq_number.setMaximumWidth(100)
        query_options.addWidget(self.query_seq_number)
        self.query_sequence_n = QLabel("/3")
        query_options.addWidget(self.query_sequence_n)
        self.button_next_query_seq = QPushButton(">>")
        self.button_next_query_seq.setMaximumWidth(40)
        self.button_next_query_seq.clicked.connect(lambda: self.set_within_query_sequence(self.current_query_sn + 1))
        query_options.addWidget(self.button_next_query_seq)
        query_options.addStretch()
        query_layout.addLayout(query_options)

        # Query Image
        self.query_image = ImageWidget()
        self.query_image.setStyleSheet("border: 1px solid black;")
        self.query_image.setAlignment(Qt.AlignmentFlag.AlignTop)
        query_layout.addWidget(self.query_image, 1)
        # Query Image Tools
        query_image_buttons = QHBoxLayout()
        # Brightness
        query_image_buttons.addWidget(QLabel("Brightness:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.slider_query_brightness = QSlider(Qt.Orientation.Horizontal)
        self.slider_query_brightness.setRange(25, 75)  # Set range from 1 to 100
        self.slider_query_brightness.setValue(50)  # Set initial value
        self.slider_query_brightness.valueChanged.connect(self.query_image.adjust_brightness)
        query_image_buttons.addWidget(self.slider_query_brightness, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Contrast
        query_image_buttons.addWidget(QLabel("Contrast:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.slider_query_contrast = QSlider(Qt.Orientation.Horizontal)
        self.slider_query_contrast.setRange(25, 75)  # Set range from 1 to 100
        self.slider_query_contrast.setValue(50)  # Set initial value
        self.slider_query_contrast.valueChanged.connect(self.query_image.adjust_contrast)
        query_image_buttons.addWidget(self.slider_query_contrast, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Sharpness
        query_image_buttons.addWidget(QLabel("Sharpness:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.slider_query_sharpness = QSlider(Qt.Orientation.Horizontal)
        self.slider_query_sharpness.setRange(25, 75)  # Set range from 1 to 100
        self.slider_query_sharpness.setValue(50)  # Set initial value
        self.slider_query_sharpness.valueChanged.connect(self.query_image.adjust_sharpness)
        query_image_buttons.addWidget(self.slider_query_sharpness, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Reset
        button_query_image_reset = QPushButton("Reset") 
        button_query_image_reset.clicked.connect(self.query_image_reset)
        query_image_buttons.addWidget(button_query_image_reset, 0, alignment=Qt.AlignmentFlag.AlignLeft)
         # View Image
        button_query_image_view = QPushButton("View Image") 
        button_query_image_view.clicked.connect(lambda: self.view_image(self.current_query_rid))
        query_image_buttons.addWidget(button_query_image_view, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        query_image_buttons.addStretch()
        query_layout.addLayout(query_image_buttons)

        # MetaData
        self.query_info = QLabel("Image Metadata")
        self.query_info.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.query_info.setContentsMargins(10, 20, 10, 20)
        self.query_info.setMaximumHeight(200)
        self.query_info.setStyleSheet("border: 1px solid black;")
        query_layout.addWidget(self.query_info, 1)
        image_layout.addLayout(query_layout)

        # MIDDLE COLUMN --------------------------------------------------------
        middle_column = QVBoxLayout()
        middle_column.addStretch()
        self.button_match = QPushButton("Match")
        self.button_match.setCheckable(True)
        self.button_match.clicked.connect(self.press_match_button)
        self.button_match.setFixedHeight(50)
        self.button_match.setMaximumWidth(50)
        middle_column.addWidget(self.button_match,
                                alignment=Qt.AlignmentFlag.AlignCenter)
        middle_column.addStretch()
        image_layout.addLayout(middle_column)

        # MATCH ----------------------------------------------------------------
        match_layout = QVBoxLayout()
        match_label = QLabel("Match")
        match_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        match_layout.addWidget(match_label)
        # Options
        match_options = QHBoxLayout()
        match_options.addStretch()
        # # Match Number
        match_options.addWidget(QLabel("Match Image:"))
        self.button_previous_match = QPushButton("<<")
        self.button_previous_match.setMaximumWidth(40)
        self.button_previous_match.clicked.connect(lambda: self.set_match(self.current_match - 1))
        match_options.addWidget(self.button_previous_match)
        self.match_number = QLineEdit(str(self.current_match + 1))
        self.match_number.setMaximumWidth(100)
        match_options.addWidget(self.match_number)
        self.match_n = QLabel("/9")
        match_options.addWidget(self.match_n)
        self.button_next_match = QPushButton(">>")
        self.button_next_match.setMaximumWidth(40)
        self.button_next_match.clicked.connect(lambda: self.set_match(self.current_match + 1))
        match_options.addWidget(self.button_next_match)

        self.match_distance = QLabel("Distance: ")
        self.match_distance.setStyleSheet("border: 1px solid black;")
        match_options.addWidget(self.match_distance)

        match_options.addStretch()
        match_layout.addLayout(match_options)

        # Match Image
        self.match_image = ImageWidget()
        self.match_image.setStyleSheet("border: 1px solid black;")
        self.match_image.setAlignment(Qt.AlignmentFlag.AlignTop)
        match_layout.addWidget(self.match_image, 1)
        # Match Image Tools
        match_image_buttons = QHBoxLayout()
        # Brightness
        match_image_buttons.addWidget(QLabel("Brightness:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.slider_match_brightness = QSlider(Qt.Orientation.Horizontal)
        self.slider_match_brightness.setRange(25, 75)  # Set range from 1 to 100
        self.slider_match_brightness.setValue(50)  # Set initial value
        self.slider_match_brightness.valueChanged.connect(self.match_image.adjust_brightness)
        match_image_buttons.addWidget(self.slider_match_brightness, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Contrast
        match_image_buttons.addWidget(QLabel("Contrast:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.slider_match_contrast = QSlider(Qt.Orientation.Horizontal)
        self.slider_match_contrast.setRange(25, 75)  # Set range from 1 to 100
        self.slider_match_contrast.setValue(50)  # Set initial value
        self.slider_match_contrast.valueChanged.connect(self.match_image.adjust_contrast)
        match_image_buttons.addWidget(self.slider_match_contrast, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Sharpness
        match_image_buttons.addWidget(QLabel("Sharpness:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.slider_match_sharpness = QSlider(Qt.Orientation.Horizontal)
        self.slider_match_sharpness.setRange(25, 75)  # Set range from 1 to 100
        self.slider_match_sharpness.setValue(50)  # Set initial value
        self.slider_match_sharpness.valueChanged.connect(self.match_image.adjust_sharpness)
        match_image_buttons.addWidget(self.slider_match_sharpness, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Reset
        button_match_image_reset = QPushButton("Reset") 
        button_match_image_reset.clicked.connect(self.match_image_reset)
        match_image_buttons.addWidget(button_match_image_reset, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # View Image
        button_match_image_view = QPushButton("View Image") 
        button_match_image_view.clicked.connect(lambda: self.view_image(self.current_match_rid))
        match_image_buttons.addWidget(button_match_image_view, 0, alignment=Qt.AlignmentFlag.AlignLeft)


        match_image_buttons.addStretch()
        match_layout.addLayout(match_image_buttons)

        # MetaData
        self.match_info = QLabel("Image Metadata")
        self.match_info.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.match_info.setContentsMargins(10, 20, 10, 20)
        self.match_info.setMaximumHeight(200)
        self.match_info.setStyleSheet("border: 1px solid black;")

        match_layout.addWidget(self.match_info, 1)
        image_layout.addLayout(match_layout)
        # Add image block to layout
        layout.addLayout(image_layout)

        # BOTTOM LAYER =========================================================
        # Buttons
        bottom_layer = QHBoxLayout()
        button_validate = QPushButton("View Data")
        button_validate.pressed.connect(self.validate)

        # Add buttons to the layout
        bottom_layer.addWidget(button_validate)
        layout.addLayout(bottom_layer)
        self.setLayout(layout)

    # RETURN HOME
    def home(self):
        self.parent._set_base_view()

    # MEDIA VIEW
    def validate(self):
        self.parent._set_media_view()

    # RUN ON ENTRY =============================================================
    def calculate_neighbors(self):
        """
        Calculates knn for all unvalidated images, ranks by smallest distance to NN
        """
        self.data = db_roi.fetch_roi_media(self.mpDB)
        if self.data.empty:
            self.home()
            return

        self.sequences = db_roi.sequence_roi_dict(self.data)

        # create backups for filtering
        self.data_raw = self.data.copy()
        self.sequences_raw = self.sequences

        # must have embeddings to continue
        if not (self.data["emb_id"] == 0).all():

            dialog = ProgressPopup(self, "Matching embeddings...")
            dialog.set_max(len(self.sequences))
            dialog.show()

            info = "roi.id, media_id, reviewed, species_id, individual_id, emb_id, timestamp, site_id, sequence_id"
            # need sequence and capture ids from media to restrict comparisons shown to
            rois, columns = self.mpDB.select_join("roi", "media", 'roi.media_id = media.id', columns=info)
            self.rois = pd.DataFrame(rois, columns=columns)


            self.match_thread = MatchEmbeddingThread(self.mpDB, self.rois, self.sequences,
                                                     k=self.k, threshold=self.threshold)
            self.match_thread.progress_update.connect(dialog.set_counter)
            self.match_thread.neighbor_dict_return.connect(self.capture_neighbor_dict)
            self.match_thread.nearest_dict_return.connect(self.capture_nearest_dict)
            self.match_thread.finished.connect(self.establish_queries)  # do not continue until finished
            self.match_thread.start()

        else:
            dialog = AlertPopup(self, prompt="No data to match, process images first.")
            if dialog.exec():
                del dialog
            self.parent._set_base_view()

    def capture_neighbor_dict(self, neighbor_dict):
        # capture neighbor_dict from MatchEmbeddingThread
        self.neighbor_dict = neighbor_dict

    def capture_nearest_dict(self, nearest_dict):
        # capture neighbor_dict from MatchEmbeddingThread
        self.nearest_dict = nearest_dict
    # ==========================================================================

    def establish_queries(self):
        # must have valid matches to continue
        if self.neighbor_dict:
            self.ranked_sequences = sorted(self.nearest_dict.items(), key=lambda x: x[1])
            # set number of queries to validate
            self.n_queries = len(self.neighbor_dict)
            self.query_n.setText("/" + str(self.n_queries))
            # set first query to highest ranking sequence
            self.set_query(0)

        # filtered neighbor dict returns empty, all existing data must be from same individual
        else:
            dialog = AlertPopup(self, prompt="No data to compare, all available data from same sequence/capture.")
            if dialog.exec():
                del dialog
            self.parent._set_base_view()

    def set_query(self, n):
        """
        Set the Query side to a particular (n) image in the list
        """
        # wrap around
        if n < 0: n = self.n_queries - 1
        if n > self.n_queries - 1: n = 0

        # set current query
        self.current_query = n
        self.query_number.setText(str(self.current_query + 1))

        # get corresponding sequence_id and rois
        self.current_sequence_id = self.ranked_sequences[self.current_query][0]
        self.current_query_rois = self.sequences[self.current_sequence_id]
        print("query rois:", self.current_query_rois)

        # get viewpoints
        self.current_query_viewpoints = self.data.loc[self.current_query_rois, 'viewpoint']
        print(self.current_query_viewpoints)

        # set view to first in sequence
        self.query_sequence_n.setText(str(len(self.current_query_rois)))
        self.set_within_query_sequence(0)

        # update matches
        self.update_matches()

    def set_within_query_sequence(self, n):
        """
        If the query sequence contains more than one image,
        set the display to the nth element in the sequence
        """
        # wrap around
        if n < 0: n = len(self.current_query_rois) - 1
        if n > len(self.current_query_rois) - 1: n = 0

        self.current_query_sn = n  # number within sequence
        self.current_query_rid = self.current_query_rois[self.current_query_sn]
        self.query_seq_number.setText(str(self.current_query_sn + 1))

        # load new images
        self.load_query()

    # refresh match list
    def update_matches(self):
        """
        Update match list if current_query changes
        """
        # get all matches for query
        full_match_set = self.neighbor_dict[self.current_sequence_id]
        print(full_match_set)
        self.current_match_rois = [x[0] for x in full_match_set]
        self.match_n.setText("/" + str(len(self.current_match_rois)))

        print("match rois:", self.current_match_rois)
        # set to top of matches
        self.set_match(0)

    def set_match(self, n):
        """
        Set the curent match index and id 
        """
        # wrap around
        if n < 0: n = len(self.current_match_rois) - 1
        if n > len(self.current_match_rois) - 1: n = 0

        self.current_match = n
        self.current_match_rid = self.current_match_rois[self.current_match]
        self.match_number.setText(str(self.current_match + 1))

        # load new images
        self.load_match()
        self.toggle_match_button()

    # VIEWPOINT TOGGLE
    def toggle_viewpoint(self):
        """
        Flip between viewpoints in paired images within a sequence
        """
        pass

    # MATCHING PROCESS ---------------------------------------------------------
    def press_match_button(self):
        if self.button_match.isChecked():
            self.toggle_match_button(set=True)
            self.new_match()
        else:
            self.toggle_match_button(set=False)

    def toggle_match_button(self, set=''):
        # already a match
        if self.data.loc[self.current_query_rid, "individual_id"] == self.data.loc[self.current_match_rid, "individual_id"] and \
           self.data.loc[self.current_query_rid, "individual_id"] is not None:
            self.button_match.setStyleSheet(MATCH_STYLE)
        # force set
        elif set is True:
            self.button_match.setStyleSheet(MATCH_STYLE)
        elif set is False:
            self.button_match.setStyleSheet("")
        # not a match
        else:
            self.button_match.setStyleSheet("")

    def new_match(self):
        """
        Match button was clicked, merge query sequence and current match
        """
        # Both individual_ids are None
        if self.data.loc[self.current_query_rid, "individual_id"] == self.data.loc[self.current_match_rid, "individual_id"] and \
           self.data.loc[self.current_query_rid, "individual_id"] is None:
            # make new individual
            dialog = IndividualFillPopup(self)
            if dialog.exec():
                individual_id = self.mpDB.add_individual(dialog.get_species_id(), dialog.get_name(), dialog.get_sex())
                # update query and match
                self.mpDB.edit_row('roi', self.current_query_rid, {"individual_id": individual_id})
                self.mpDB.edit_row('roi', self.current_match_rid, {"individual_id": individual_id})
            del dialog
            # update data  
            self.data = db_roi.fetch_roi_media(self.mpDB)
            self.load_query()
            self.load_match()

        # Match has a name
        else:
            merge(self.mpDB, self.data, self.current_query_rois, self.current_match_rid)
            # update data  
            self.data = db_roi.fetch_roi_media(self.mpDB)
            self.load_query()
            self.load_match()

    # LOAD FUNCTIONS -----------------------------------------------------------
    def load_query(self):
        """
        Load Images for Current Query ROI
        """
        self.query_image.load(self.data.loc[self.current_query_rid, "filepath"],
                                       bbox=db_roi.get_bbox(self.data.loc[self.current_query_rid]))
        self.query_info.setText(db_roi.roi_metadata(self.data.loc[self.current_query_rid]))

    def load_match(self):
        """
        Load MetaData for Current Match ROI
        """
        distance = self.neighbor_dict[self.current_sequence_id][self.current_match][1]
        self.match_distance.setText(f"Distance: {distance:.2f}")

        self.match_image.load(self.data.loc[self.current_match_rid, "filepath"],
                                       bbox=db_roi.get_bbox(self.data.loc[self.current_match_rid]))
        self.match_info.setText(db_roi.roi_metadata(self.data.loc[self.current_match_rid]))

    # GUI HANDLERS =============================================================
    def change_k(self):
        # Set new k value and recalculate neighbors
        if self.knn_number.text() != '':
            self.k = int(self.knn_number.text())

    def change_threshold(self):
        # set new threshold value and recalculate neighbors
        self.threshold = self.threshold_slider.value()
        slider_handle_position = self.threshold_slider.mapToGlobal(QPoint(self.threshold_slider.width() * (self.threshold - self.threshold_slider.minimum()) //
                                                                         (self.threshold_slider.maximum() - self.threshold_slider.minimum()), 0))
        QToolTip.showText(slider_handle_position, f"{self.threshold:d}", self.threshold_slider)

    # TODO
    def filter_region(self):
        #create query for all rois connected to media connected to sites connected to surveys 
        pass

    def filter_survey(self):
        pass

    def filter_site(self):
        active_site = self.site_list_ordered[self.site_select.currentIndex()]
        print(active_site)

    def set_sites(self):
        # set sites to active survey
        self.site_select.clear()
        if self.survey_select.currentIndex() > 0:
            self.valid_sites = dict(self.mpDB.select("site", columns="id, name", row_cond=f'survey_id={self.active_survey[0]}'))
        else:
            self.valid_sites = dict(self.mpDB.select("site", columns="id, name"))
        self.site_list_ordered = [(0, 'Site')] + [(k, v) for k, v in self.valid_sites.items()]
        self.site_select.addItems([el[1] for el in self.site_list_ordered])

    # Image Manipulations ------------------------------------------------------

    def query_image_reset(self):
        self.query_image.reset()
        self.slider_query_brightness.setValue(50)
        self.slider_query_contrast.setValue(50)
        self.slider_query_sharpness.setValue(50)

    def match_image_reset(self):
        self.match_image.reset()
        self.slider_match_brightness.setValue(50)
        self.slider_match_contrast.setValue(50)
        self.slider_match_sharpness.setValue(50)

    # TODO
    def view_image(self, rid):
        dialog = ImagePopup(self, rid)
        if dialog.exec():
            del dialog

    # Keyboard Handler ---------------------------------------------------------
    def keyPressEvent(self, event):
        key = event.key()
        key_text = event.text()

        # Right Arrow
        if key == 16777236:
            self.set_query(self.current_query + 1)
        # Left Arrow
        elif key == 16777234:
            self.set_query(self.current_query - 1)
        # Up Arrow
        elif key == 16777235:
            self.set_match(self.current_match - 1)
        # Down Arrow
        elif key == 16777237:
            self.set_match(self.current_match + 1)

        # M - Match
        elif key == 77:
            self.button_match.click()
        else:
            print(f"Key pressed: {key_text} (Qt key code: {key})")
