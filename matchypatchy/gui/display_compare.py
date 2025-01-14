"""
GUI Window for Match Comparisons

TODO:
 - Add new individual ID to all rois in query sequence and all rois in match sequence
 - Likewise if merging
 - enable merge
 - ENABLE VIEWPOINT
"""
from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QLineEdit, QSlider, QToolTip)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QKeyEvent, QIntValidator

from matchypatchy.gui.widget_image import ImageWidget
from matchypatchy.gui.popup_alert import AlertPopup
from matchypatchy.gui.popup_individual import IndividualFillPopup
from matchypatchy.gui.popup_single_image import ImagePopup

from matchypatchy.algo.query import QueryContainer

MATCH_STYLE = """ QPushButton { background-color: #2e7031; color: white; }"""


class DisplayCompare(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.mpDB = parent.mpDB
        self.k = 3  # default knn
        self.threshold = 80

        ## CREATE QUERY CONTAINER ==============================================
        self.QueryContainer = QueryContainer(self)

        # FIRST LAYER ==========================================================
        layout = QVBoxLayout()
        first_layer = QHBoxLayout()
        button_home = QPushButton("Home")
        button_home.clicked.connect(lambda: self.home(warn=False))
        first_layer.addWidget(button_home)
        first_layer.addSpacing(10)

        # OPTIONS
        first_layer.addWidget(QLabel("Max # of Matches:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.knn_number = QLineEdit(str(self.k))
        self.knn_number.setValidator(QIntValidator(0, 1000))
        self.knn_number.setToolTip('Maximum number of matches allowed per ROI (not per sequence)')
        self.knn_number.textChanged.connect(self.change_k)
        self.knn_number.setMaximumWidth(50)
        first_layer.addWidget(self.knn_number, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        first_layer.addWidget(QLabel("Distance Threshold:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(1, 100)  # Set range from 1 to 100
        self.threshold_slider.setValue(self.threshold)  # Set initial value
        self.threshold_slider.valueChanged.connect(self.change_threshold)
        first_layer.addWidget(self.threshold_slider, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        button_recalc = QPushButton("Recalculate Matches")
        button_recalc.clicked.connect(self.recalculate)
        first_layer.addWidget(button_recalc)

        button_recalc = QPushButton("Query by Individual")
        button_recalc.clicked.connect(self.recalculate_by_individual)
        first_layer.addWidget(button_recalc)


        # FILTERS --------------------------------------------------------------
        first_layer.addSpacing(20)
        first_layer.addWidget(QLabel("Filter:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # Region
        self.region_select = QComboBox()
        self.region_select.setFixedWidth(200)
        self.region_select.currentIndexChanged.connect(self.select_region)
        first_layer.addWidget(self.region_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Survey
        self.survey_select = QComboBox()
        self.survey_select.setFixedWidth(200)
        self.survey_select.currentIndexChanged.connect(self.select_survey)
        first_layer.addWidget(self.survey_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # station
        self.station_select = QComboBox()
        self.station_select.setFixedWidth(200)
        self.station_select.currentIndexChanged.connect(self.select_station)
        first_layer.addWidget(self.station_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        first_layer.addStretch()
        layout.addLayout(first_layer)

        self.refresh_filters()

        # IMAGE COMPARISON =====================================================
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
        self.button_previous_query.clicked.connect(lambda: self.change_query(self.QueryContainer.current_query - 1))
        query_options.addWidget(self.button_previous_query)
        self.query_number = QLineEdit(str(self.QueryContainer.current_query + 1))
        self.query_number.setMaximumWidth(100)
        query_options.addWidget(self.query_number)
        self.query_n = QLabel("/9")
        query_options.addWidget(self.query_n)
        self.button_next_query = QPushButton(">>")
        self.button_next_query.setMaximumWidth(40)
        self.button_next_query.clicked.connect(lambda: self.change_query(self.QueryContainer.current_query + 1))
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
        self.button_previous_query_seq.clicked.connect(lambda: self.change_query_in_sequence(self.QueryContainer.current_query_sn - 1))
        query_options.addWidget(self.button_previous_query_seq)
        self.query_seq_number = QLineEdit(str(self.QueryContainer.current_query_sn + 1))
        self.query_seq_number.setMaximumWidth(100)
        query_options.addWidget(self.query_seq_number)
        self.query_sequence_n = QLabel("/3")
        query_options.addWidget(self.query_sequence_n)
        self.button_next_query_seq = QPushButton(">>")
        self.button_next_query_seq.setMaximumWidth(40)
        self.button_next_query_seq.clicked.connect(lambda: self.change_query_in_sequence(self.QueryContainer.current_query_sn + 1))
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
        button_query_image_view.clicked.connect(lambda: self.view_image(self.QueryContainer.current_query_rid))
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
        self.button_match.setChecked(False)
        self.button_match.pressed.connect(self.press_match_button)
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
        self.button_previous_match.clicked.connect(lambda: self.change_match(self.QueryContainer.current_match - 1))
        match_options.addWidget(self.button_previous_match)
        self.match_number = QLineEdit(str(self.QueryContainer.current_match + 1))
        self.match_number.setMaximumWidth(100)
        match_options.addWidget(self.match_number)
        self.match_n = QLabel("/9")
        match_options.addWidget(self.match_n)
        self.button_next_match = QPushButton(">>")
        self.button_next_match.setMaximumWidth(40)
        self.button_next_match.clicked.connect(lambda: self.change_match(self.QueryContainer.current_match + 1))
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
        button_match_image_view.clicked.connect(lambda: self.view_image(self.QueryContainer.current_match_rid))
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
        # ======================================================================

    # GUI ----------------------------------------------------------------------

    # RETURN HOME
    def home(self, warn=False):
        if warn:
            dialog = AlertPopup(self, prompt="No data to match, process images first.")
            if dialog.exec():
                del dialog
        self.parent._set_base_view()

    # MEDIA VIEW
    def validate(self):
        self.parent._set_media_view()    

    def warn(self, prompt):
        dialog = AlertPopup(self, prompt=prompt)
        if dialog.exec():
            del dialog

    # MATCHING PROCESS ---------------------------------------------------------
    def press_match_button(self):
        self.button_match.setChecked(not self.button_match.isChecked())
        # check button, create match
        if self.button_match.isChecked():
            self.confirm_match()
        # uncheck button, undo match
        else:
            self.undo_match()
        self.toggle_match_button()

    def toggle_match_button(self):
        """
        Change Match button to Green when query and match are same iid,
        normal button when not
        """
        if self.QueryContainer.is_existing_match():
            self.button_match.setStyleSheet(MATCH_STYLE)
            self.button_match.setChecked(True)
        else:
            self.button_match.setStyleSheet("")
            self.button_match.setChecked(False)
            
    def confirm_match(self):
        """
        Match button was clicked, merge query sequence and current match
        """
        # Both individual_ids are None
        if self.QueryContainer.both_unnamed():
            # make new individual
            dialog = IndividualFillPopup(self)
            if dialog.exec():
                individual_id = self.mpDB.add_individual(dialog.get_species_id(), 
                                                         dialog.get_name(), 
                                                         dialog.get_sex())
                # update query and match
                # TODO: add stack to undo 
                self.QueryContainer.new_iid(individual_id)   
            del dialog
             
            # update data  
            self.QueryContainer.load_data()
            self.QueryContainer.filter(reset=False)
            self.load_query()
            self.load_match()
            self.toggle_match_button()

        # Match has a name
        else:
            self.QueryContainer.merge()   
            # update data  
            self.QueryContainer.load_data()
            self.QueryContainer.filter(reset=False)
            self.load_query()
            self.load_match()
            self.toggle_match_button()

    def undo_match(self):
        # TODO: Undoable Match stack
        pass


    # LOAD FUNCTIONS -----------------------------------------------------------

    def change_query(self, n):
        self.QueryContainer.set_query(n)
        # update text
        self.query_n.setText("/" + str(self.QueryContainer.n_queries))
        self.query_number.setText(str(self.QueryContainer.current_query + 1))
        self.query_sequence_n.setText(str(len(self.QueryContainer.current_query_rois)))
        self.query_seq_number.setText(str(self.QueryContainer.current_query_sn + 1))
        self.match_n.setText("/" + str(len(self.QueryContainer.current_match_rois)))
        self.match_number.setText(str(self.QueryContainer.current_match + 1))
        # load new images
        self.load_query()
        self.load_match()
        self.toggle_match_button()


    def change_query_in_sequence(self, n):
        self.QueryContainer.set_within_query_sequence(n)
        self.query_seq_number.setText(str(self.QueryContainer.current_query_sn + 1))
        self.load_query()


    def change_match(self, n):
        # load new images
        self.QueryContainer.set_match(n)
        self.match_number.setText(str(self.QueryContainer.current_match + 1))
        self.load_match()
        self.toggle_match_button()

    def load_query(self):
        """
        Load Images for Current Query ROI
        """
        self.query_image.load(self.QueryContainer.get_query_info("filepath"),
                              bbox=self.QueryContainer.get_query_info('bbox'))
        self.query_info.setText(self.QueryContainer.get_query_info("metadata"))

    def load_match(self):
        """
        Load MetaData for Current Match ROI
        """
        distance = self.QueryContainer.current_distance()
        self.match_distance.setText(f"Distance: {distance:.2f}")

        self.match_image.load(self.QueryContainer.get_match_info("filepath"),
                              bbox=self.QueryContainer.get_match_info("bbox"))
        self.match_info.setText(self.QueryContainer.get_match_info("metadata"))

    def toggle_viewpoint(self):
        """
        Flip between viewpoints in paired images within a sequence
        """
        # TODO
        pass

    # GUI HANDLERS =============================================================
    def change_k(self):
        # Set new k value
        # Must recalculate neighbors to activate
        if self.knn_number.text() != '':
            self.k = int(self.knn_number.text())

    def change_threshold(self):
        # set new threshold value 
        # Must recalculate neighbors to activate
        self.threshold = self.threshold_slider.value()
        slider_handle_position = self.threshold_slider.mapToGlobal(QPoint(self.threshold_slider.width() * (self.threshold - self.threshold_slider.minimum()) //
                                                                         (self.threshold_slider.maximum() - self.threshold_slider.minimum()), 0))
        QToolTip.showText(slider_handle_position, f"{self.threshold:d}", self.threshold_slider)

    def recalculate(self):
        self.QueryContainer.calculate_neighbors()
        self.change_query(0)

    def recalculate_by_individual(self):
        # TODO
        pass

    # FILTERS ------------------------------------------------------------------
    def refresh_filters(self):
        """
        Clear and Refresh Filters on Re-entry
        """
        self.region_select.blockSignals(True)
        self.survey_select.blockSignals(True)

        self.region_select.clear()
        self.region_list_ordered = [(0, 'Region')] + list(self.mpDB.select('region', columns='id, name'))
        self.region_select.addItems([el[1] for el in self.region_list_ordered])

        self.survey_select.clear()
        self.survey_list_ordered = [(0, 'Survey')] + list(self.mpDB.select('survey', columns='id, name'))
        self.survey_select.addItems([el[1] for el in self.survey_list_ordered])    

        self.filter_stations()    

        self.filters = {'active_region': self.region_list_ordered[self.region_select.currentIndex()],
                        'active_survey': self.survey_list_ordered[self.survey_select.currentIndex()],
                        'active_station': self.station_list_ordered[self.station_select.currentIndex()],}

        self.region_select.blockSignals(False)
        self.survey_select.blockSignals(False)

    def select_region(self):
        self.filters['active_region'] = self.region_list_ordered[self.region_select.currentIndex()]
        self.filter_surveys()
        self.filter_stations(survey_ids=list(self.valid_surveys.items()))
        self.QueryContainer.filter(filter_dict=self.filters, valid_stations=self.valid_stations)

    def select_survey(self):
        self.filters['active_survey'] = self.survey_list_ordered[self.survey_select.currentIndex()]
        self.filter_stations(survey_ids=[self.filters['active_survey']])
        self.QueryContainer.filter(filter_dict=self.filters, valid_stations=self.valid_stations)

    def select_station(self):
        self.filters['active_station'] = self.station_list_ordered[self.station_select.currentIndex()]
        self.QueryContainer.filter(filter_dict=self.filters, valid_stations=self.valid_stations)

    def filter_surveys(self):
        # block signals while updating combobox
        self.survey_select.blockSignals(True)
        self.survey_select.clear()
        if self.region_select.currentIndex() > 0:
            # get surveys in selected region
            region_id = self.filters['active_region'][0]
            self.valid_surveys = dict(self.mpDB.select("survey", columns="id, name", row_cond=f'region_id={region_id}'))
        else:
            # get all surveys
            self.valid_surveys = dict(self.mpDB.select("survey", columns="id, name"))
        # Update survey list to reflect active region
        self.survey_list_ordered = [(0, 'Survey')] + [(k, v) for k, v in self.valid_surveys.items()]
        self.survey_select.addItems([el[1] for el in self.survey_list_ordered])
        self.survey_select.blockSignals(False)

    def filter_stations(self, survey_ids=None):
        # block signals while updating combobox
        self.station_select.blockSignals(True)
        self.station_select.clear()
        if survey_ids:
            survey_list = ",".join([str(s[0]) for s in survey_ids])
            selection = f'survey_id IN ({survey_list})'

            self.valid_stations = dict(self.mpDB.select("station", columns="id, name", row_cond=selection, quiet=False))
        else:
            self.valid_stations = dict(self.mpDB.select("station", columns="id, name"))

        # Update station list to reflect active survey
        self.station_list_ordered = [(0, 'station')] + [(k, v) for k, v in self.valid_stations.items()]
        self.station_select.addItems([el[1] for el in self.station_list_ordered])
        self.station_select.blockSignals(False)        

    # IMAGE MANIPULATION -------------------------------------------------------
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
