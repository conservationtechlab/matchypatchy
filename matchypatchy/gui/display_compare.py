"""
GUI Window for Match Comparisons

"""
import os
from pathlib import Path
from PIL import Image

from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QLineEdit, QSlider)
from PyQt6.QtCore import Qt, QPoint

from matchypatchy.gui.widget_media import MediaWidget, VideoViewer
from matchypatchy.gui.widget_image_adjustment import ImageAdjustBar
from matchypatchy.gui.popup_alert import AlertPopup
from matchypatchy.gui.popup_individual import IndividualFillPopup
from matchypatchy.gui.popup_media_edit import MediaEditPopup
from matchypatchy.gui.popup_pairx import PairXPopup
from matchypatchy.gui.gui_assets import *
from matchypatchy.gui.widget_filterbar import FilterBar

from matchypatchy.algo.query import QueryContainer
from matchypatchy.algo.qc_query import QC_QueryContainer

from matchypatchy.database.species import fetch_individual
from matchypatchy.database.media import VIDEO_EXT, IMAGE_EXT
from matchypatchy import config


class DisplayCompare(QWidget):

    MATCH_STYLE = """ QPushButton { background-color: #2e7031; color: white; }"""

    def __init__(self, parent):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus) 
        self.parent = parent
        self.mpDB = parent.mpDB
        self.k = config.load('KNN')  # default knn
        self.distance_metric = 'cosine'
        self.threshold = 50
        self.current_viewpoint = 'Any'
        self.qc = False  # whether in QC mode
        
        # CREATE QUERY CONTAINER ==============================================
        self.QueryContainer = QueryContainer(self)
        self.progress = None

        # FIRST LAYER ==========================================================
        layout = QVBoxLayout()
        first_layer = QHBoxLayout()
        button_home = StandardButton("Home")
        button_home.clicked.connect(lambda: self.home(warn=False))
        first_layer.addWidget(button_home)
        first_layer.addWidget(VerticalSeparator()) 

        # OPTIONS
        first_layer.addWidget(QLabel("Distance Metric:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.option_distance_metric = QComboBox()
        self.option_distance_metric.addItems(['Cosine','L2'])
        self.option_distance_metric.currentIndexChanged.connect(self.change_metric)
        first_layer.addWidget(self.option_distance_metric, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        first_layer.addWidget(QLabel("Distance Threshold:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)  # Set range from 1 to 100
        self.threshold_slider.setValue(self.threshold)  # Set initial value
        self.threshold_slider.valueChanged.connect(self.change_threshold_slider)
        first_layer.addWidget(self.threshold_slider, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.threshold_label = QLineEdit(f"{self.threshold / 100:.2f}")
        self.threshold_label.setFixedWidth(60)
        self.threshold_label.textChanged.connect(self.change_threshold_manual)
        first_layer.addWidget(self.threshold_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        button_recalc = QPushButton("Recalculate Matches")
        button_recalc.clicked.connect(self.calculate_neighbors)
        first_layer.addWidget(button_recalc)

        button_recalc = QPushButton("Query by Individual")
        button_recalc.clicked.connect(self.recalculate_by_individual)
        first_layer.addWidget(button_recalc)

        # FILTERBAR --------------------------------------------------------------
        first_layer.addSpacing(10)
        first_layer.addWidget(VerticalSeparator()) 
        first_layer.addSpacing(10)
        self.filterbar = FilterBar(self, 140)
        self.filterbar.viewpoint_visible(False)
        self.filterbar.individual_visible(False)
        self.filterbar.unidentified_visible(False)
        self.filterbar.favorites_visible(False)

        first_layer.addWidget(self.filterbar)
        # get initial filters
        self.filters = self.filterbar.get_filters()
        self.valid_stations = self.filterbar.get_valid_stations()

        button_filter = QPushButton("Filter Images")
        button_filter.clicked.connect(self.filter_neighbors)
        first_layer.addWidget(button_filter)

        first_layer.addStretch()
        layout.addLayout(first_layer)

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
        self.query_number.setFixedWidth(50)
        query_options.addWidget(self.query_number)
        self.query_n = QLabel("/9")
        query_options.addWidget(self.query_n)
        self.button_next_query = QPushButton(">>")
        self.button_next_query.setMaximumWidth(40)
        self.button_next_query.clicked.connect(lambda: self.change_query(self.QueryContainer.current_query + 1))
        query_options.addWidget(self.button_next_query)
        query_options.addSpacing(20)
        # # Sequence Number
        query_options.addWidget(QLabel("Sequence:"))
        self.button_previous_query_seq = QPushButton("<<")
        self.button_previous_query_seq.setMaximumWidth(40)
        self.button_previous_query_seq.clicked.connect(lambda: self.change_query_in_sequence(self.QueryContainer.current_query_sn - 1))
        query_options.addWidget(self.button_previous_query_seq)
        self.query_seq_number = QLineEdit(str(self.QueryContainer.current_query_sn + 1))
        self.query_seq_number.setFixedWidth(50)
        query_options.addWidget(self.query_seq_number)
        self.query_sequence_n = QLabel("/ 3")
        query_options.addWidget(self.query_sequence_n)
        self.button_next_query_seq = QPushButton(">>")
        self.button_next_query_seq.setMaximumWidth(40)
        self.button_next_query_seq.clicked.connect(lambda: self.change_query_in_sequence(self.QueryContainer.current_query_sn + 1))
        query_options.addWidget(self.button_next_query_seq)

        query_options.addStretch()
        query_layout.addLayout(query_options)
        # Query Image
        self.query_image = MediaWidget()
        self.query_image.setStyleSheet("border: 1px solid black;")
        #self.query_image.setAlignment(Qt.AlignmentFlag.AlignTop)
        query_layout.addWidget(self.query_image, 1)
        # Query Image Tools
        self.query_image_bar = ImageAdjustBar(self, self.query_image, 'query')
        query_layout.addWidget(self.query_image_bar)

        # MetaData
        self.query_info = QLabel("Image Metadata")
        self.query_info.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.query_info.setContentsMargins(5, 10, 5, 10)
        self.query_info.setMaximumHeight(200)
        self.query_info.setStyleSheet("border: 1px solid black; font-size: 16px;")
        query_layout.addWidget(self.query_info, 1)
        image_layout.addLayout(query_layout)

        # MIDDLE COLUMN --------------------------------------------------------
        middle_column = QVBoxLayout()
        middle_column.addStretch()
        self.button_match = QPushButton("Match")
        self.button_match.setCheckable(True)
        self.button_match.setChecked(False)
        self.button_match.blockSignals(True)
        self.button_match.pressed.connect(self.press_match_button)
        self.button_match.blockSignals(False)
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
        # OptionsVIEWPOINT_DICT
        match_options = QHBoxLayout()
        match_options.addStretch()

        # Viewpoint Toggle
        match_options.addWidget(QLabel("Viewpoint: "))
        self.button_viewpoint = ThreePointSlider(initial=1)
        self.button_viewpoint.state_changed.connect(self.toggle_viewpoint)
        match_options.addWidget(self.button_viewpoint)
        match_options.addSpacing(20)

        # # Match Number
        match_options.addWidget(QLabel("Match Image:"))
        self.button_previous_match = QPushButton("<<")
        self.button_previous_match.setMaximumWidth(40)
        self.button_previous_match.clicked.connect(lambda: self.change_match(self.QueryContainer.current_match - 1))
        match_options.addWidget(self.button_previous_match)
        self.match_number = QLineEdit(str(self.QueryContainer.current_match + 1))
        self.match_number.setFixedWidth(50)
        match_options.addWidget(self.match_number)
        self.match_n = QLabel("/ 9")
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
        self.match_image = MediaWidget()
        self.match_image.setStyleSheet("border: 1px solid black;")
        #self.match_image.setAlignment(Qt.AlignmentFlag.AlignTop)
        match_layout.addWidget(self.match_image, 1)
        # Match Image Tools
        self.match_image_bar = ImageAdjustBar(self, self.match_image, 'match')
        match_layout.addWidget(self.match_image_bar)

        # MetaData
        self.match_info = QLabel("Image Metadata")
        self.match_info.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.match_info.setContentsMargins(5, 10, 5, 10)
        self.match_info.setMaximumHeight(200)
        self.match_info.setStyleSheet("border: 1px solid black; font-size: 16px;")

        match_layout.addWidget(self.match_info, 1)
        image_layout.addLayout(match_layout)
        # Add image block to layout
        layout.addLayout(image_layout)

        # BOTTOM LAYER =========================================================
        # Buttons
        bottom_layer = QHBoxLayout()
        button_validate = QPushButton("View Data")
        button_validate.pressed.connect(self.validate)

        button_visualize = QPushButton("Visualize Match")
        button_visualize.pressed.connect(self.press_visualize_button)

        # Add buttons to the layout
        bottom_layer.addWidget(button_validate)
        bottom_layer.addWidget(button_visualize)
        layout.addLayout(bottom_layer)
        self.setLayout(layout)

        # remove focus from buttons to keep keyboard shortcuts working
        self.set_no_focus()
        # ======================================================================

    def set_no_focus(self):
        for child in self.findChildren(QWidget):
            if isinstance(child, (QPushButton)):
                child.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    # ==========================================================================
    # GUI
    # ==========================================================================
    # RETURN HOME
    def home(self, warn=False):
        if self.progress and self.progress.isVisible():
            self.progress.close()
        if warn:
            dialog = AlertPopup(self, prompt="No data to match, process images first.")
            if dialog.exec():
                del dialog
        self.parent._set_base_view()

    # MEDIA VIEW
    def validate(self):
        self.parent._set_media_view()

    # Alert Popup
    def warn(self, prompt):
        dialog = AlertPopup(self, prompt=prompt)
        if dialog.exec():
            del dialog

    def change_metric(self):
        """
        Select L2 or Cosine distance metric, update threshold slider appropriately
        """
        self.distance_metric = self.option_distance_metric.currentText().lower()
        if self.distance_metric == 'l2':
            self.threshold_slider.setValue(70)
        else:
            self.threshold_slider.setValue(50)

    def change_threshold_slider(self):
        # set new threshold value
        # Must recalculate neighbors to activate
        self.threshold = self.threshold_slider.value()
        if self.distance_metric == 'cosine':
            self.threshold_label.setText(f"{self.threshold / 100:.2f}")
        else:
            self.threshold_label.setText(f"{self.threshold:d}")

    def change_threshold_manual(self):
        try:
            if self.distance_metric == 'cosine':
                val = float(self.threshold_label.text())
                if 0.0 <= val <= 1.0:
                    self.threshold = int(val * 100)
                    self.threshold_slider.setValue(self.threshold)
            else:
                val = int(self.threshold_label.text())
                if 0 <= val <= 100:
                    self.threshold = val
                    self.threshold_slider.setValue(self.threshold)
        except ValueError:
            pass  # ignore invalid input

    # ON ENTRY
    def calculate_neighbors(self):
        # Disable individual select until feature is implemented on QC
        self.qc = False
        self.filterbar.individual_visible(False)
        self.k = config.load('KNN')  # can be changed in configuration
        self.QueryContainer = QueryContainer(self)  #re-establish object
        emb_exist = self.QueryContainer.load_data()
        if emb_exist:
            self.QueryContainer.filter(filter_dict=self.filters, valid_stations=self.valid_stations)
            self.show_progress("Matching embeddings... This may take a while.")
            self.QueryContainer.calculate_neighbors()
            self.progress.rejected.connect(self.QueryContainer.match_thread.requestInterruption)
            self.QueryContainer.thread_signal.connect(self.check_matchthread_success)
        else:
            self.home(warn=True)    

        # progress popup
    def show_progress(self, prompt):
        self.progress = AlertPopup(self, prompt, progressbar=True, cancel_only=True)
        self.progress.show()

    def check_matchthread_success(self, thread_success):
        if thread_success:
            self.change_query(0)
        else:
            self.warn(prompt="No data to compare, all available data from same sequence/capture.")

    def recalculate_by_individual(self):
        if not fetch_individual(self.mpDB).empty:
            self.QueryContainer = QC_QueryContainer(self)
            self.qc = True
            self.filterbar.individual_visible(True)
            self.QueryContainer.load_data()
            self.QueryContainer.filter(filter_dict=self.filters, valid_stations=self.valid_stations)
            self.change_query(0)
        else:
            self.warn(prompt="No data to compare, all available data from same sequence/capture.")

    # ==========================================================================
    # MATCHING PROCESS
    # ==========================================================================
    def press_match_button(self):
        # already a match
        if self.QueryContainer.is_existing_match():
            self.unmatch()
        # new match
        else:
            self.confirm_match()

    def toggle_match_button(self):
        """
        Change Match button to Green when query and match are same iid,
        normal button when not
        """
        if self.QueryContainer.is_existing_match():
            self.button_match.setChecked(True)
        else:
            self.button_match.setChecked(False)

        if self.button_match.isChecked():
            self.button_match.setStyleSheet(self.MATCH_STYLE)
        else:
            self.button_match.setStyleSheet("")

    def confirm_match(self):
        """
        Match button was clicked, merge query sequence and current match
        """
        # Both individual_ids are None
        if self.QueryContainer.both_unnamed():
            # make new individual
            dialog = IndividualFillPopup(self)
            if dialog.exec():
                individual_id = self.mpDB.add_individual(dialog.get_name(),
                                                         dialog.get_species_id(),
                                                         dialog.get_sex(),
                                                         dialog.get_age())
                # update query and match
                self.QueryContainer.new_iid(individual_id)
            del dialog

        # Match has a name
        else:
            self.QueryContainer.merge()
            # update data
        self.QueryContainer.load_data()
        self.QueryContainer.filter()
        self.load_query()
        self.load_match()

    def unmatch(self):
        name = self.QueryContainer.get_info(self.QueryContainer.current_match_rid, 'name')
        dialog = AlertPopup(self, prompt=f"This will remove Match from individual '{name}'")
        if dialog.exec():
            self.QueryContainer.unmatch()
            del dialog

        self.QueryContainer.load_data()
        self.QueryContainer.filter()
        self.load_query()
        self.load_match()

    # ==========================================================================
    # LOAD FUNCTIONS
    # ==========================================================================
    def get_rid(self, side):    
        if side == "query":
            return self.QueryContainer.current_query_rid
        else:
            return self.QueryContainer.current_match_rid

    def change_query(self, n):
        self.QueryContainer.set_query(n)
        # update text
        self.query_n.setText("/ " + str(self.QueryContainer.n_queries))
        self.query_number.setText(str(self.QueryContainer.current_query + 1))

        self.query_sequence_n.setText("/ " + str(len(self.QueryContainer.current_query_rois)))
        self.query_seq_number.setText(str(self.QueryContainer.current_query_sn + 1))

        self.match_n.setText("/ " + str(len(self.QueryContainer.current_match_rois)))
        self.match_number.setText(str(self.QueryContainer.current_match + 1))

        self.QueryContainer.toggle_viewpoint(self.current_viewpoint)

        self.query_image_bar.reset_sliders()
        self.match_image_bar.reset_sliders()
        # load new images
        self.load_query()
        self.load_match()

    def change_query_in_sequence(self, n):
        self.QueryContainer.set_within_query_sequence(n)
        self.query_image_bar.reset_sliders()
        self.query_seq_number.setText(str(self.QueryContainer.current_query_sn + 1))
        self.load_query()

    def change_match(self, n):
        # load new images
        self.QueryContainer.set_match(n)
        self.match_image_bar.reset_sliders()
        self.match_number.setText(str(self.QueryContainer.current_match + 1))
        self.load_match()

    def load_query(self):
        """
        Load Images for Current Query ROI
        """
        self.query_image.load(self.QueryContainer.get_info(self.QueryContainer.current_query_rid, "filepath"),
                              frame=self.QueryContainer.get_info(self.QueryContainer.current_query_rid, "frame"),
                              bbox=self.QueryContainer.get_info(self.QueryContainer.current_query_rid, 'bbox'), crop=True)
        
        metadata = self.QueryContainer.get_info(self.QueryContainer.current_query_rid, "metadata")
        self.query_info.setText(self.format_metadata(metadata))
        self.query_info.adjustSize()
        self.toggle_match_button()
        self.toggle_query_favorite()

    def load_match(self):
        """
        Load MetaData for Current Match ROI
        """
        distance = self.QueryContainer.current_distance()
        self.match_distance.setText(f"Distance: {distance:.2f}")

        self.match_image.load(self.QueryContainer.get_info(self.QueryContainer.current_match_rid, "filepath"),
                              frame=self.QueryContainer.get_info(self.QueryContainer.current_match_rid, "frame"),
                              bbox=self.QueryContainer.get_info(self.QueryContainer.current_match_rid, "bbox"), crop=True)

        metadata = self.QueryContainer.get_info(self.QueryContainer.current_match_rid, "metadata")
        self.match_info.setText(self.format_metadata(metadata))
        self.match_info.adjustSize()
        self.toggle_match_button()
        self.toggle_match_favorite()

    def toggle_viewpoint(self, selected_viewpoint):
        """
        Flip between viewpoints in paired images within a sequence
        """
        if selected_viewpoint == 0:
            selected_viewpoint = 'Left'
        elif selected_viewpoint == 1:
            selected_viewpoint = 'Any'
        else:
            selected_viewpoint = 'Right'
        
        self.current_viewpoint = selected_viewpoint
        self.QueryContainer.toggle_viewpoint(self.current_viewpoint)
        # either query or match has no examples with selected viewpoint, defaults to all viewpoints
        if (self.QueryContainer.empty_query is True or self.QueryContainer.empty_match is True):
            self.warn(f'No query image with {self.current_viewpoint} viewpoint in the current sequence.')
            self.button_viewpoint.set_index(1)
        self.query_sequence_n.setText('/ ' + str(len(self.QueryContainer.current_query_rois)))
        self.match_n.setText('/ ' + str(len(self.QueryContainer.current_match_rois)))
        self.query_seq_number.setText('1')
        self.match_number.setText('1')
        self.load_query()
        self.load_match()

    def format_metadata(self, info_dict, spacing=1):
        spacer = "&nbsp;" * 20
        html_text = f"""<div style="line-height: {spacing}; width: 100%; height: 100%;">
                            <table cellspacing="5">
                            <tr>
                                <td>Name:</td><td>{info_dict['Name']}</td>
                                <td>{spacer}</td>
                                <td>File Name:</td><td>{os.path.basename(info_dict['File Path'])}</td>
                            </tr><tr>
                                <td>Species:</td><td>{info_dict['Species']}</td>
                                <td>{spacer}</td>
                                <td>Timestamp:</td><td>{info_dict['Timestamp']}</td>
                            </tr><tr>
                                <td>Sex:</td><td>{info_dict['Sex']}</td>
                                <td>{spacer}</td>
                                <td>Region:</td><td>{info_dict['Region']}</td>
                            </tr><tr>
                                <td>Age:</td><td>{info_dict['Age']}</td>
                                <td>{spacer}</td>
                                <td>Survey:</td><td>{info_dict['Survey']}</td>
                            </tr><tr>                                
                                <td>Viewpoint:</td><td>{info_dict['Viewpoint']}</td>
                                <td>{spacer}</td>
                                <td>Station:</td><td>{info_dict['Station']}</td>
                            </tr><tr>
                                <td>Sequence ID:</td><td>{info_dict['Sequence ID']}</td>
                                <td>{spacer}</td>
                                <td>Comment:</td><td>{info_dict['Comment']}</td>
                            </tr>
                            </table>
                        </div>
                    """
        return html_text

    # ==========================================================================
    # FILTERS
    # ==========================================================================
    def refresh_filters(self):
        self.filterbar.refresh_filters()

    def filter_neighbors(self):
        self.filters = self.filterbar.get_filters()
        self.valid_stations = self.filterbar.get_valid_stations()

        if self.qc:
            self.recalculate_by_individual()
        else:
            self.calculate_neighbors()

    # ==========================================================================
    # IMAGE MANIPULATION
    # ==========================================================================
    def edit_image(self, rid):
        """
        Open Image in MatchyPatchy Single Image Popup

        NOTE: Redraws query and match
        """
        dialog = MediaEditPopup(self, rid)
        if dialog.exec():
            del dialog
            # reload data
            self.QueryContainer.load_data()
            self.QueryContainer.filter()
            self.load_query()
            self.load_match()

    def open_image(self, rid):
        """
        Open Image in OS Default Image Viewer

        Currently only supports one image at a time
        """
        filepath = self.QueryContainer.get_info(rid, "filepath")
        if Path(filepath).suffix.lower() in IMAGE_EXT:
            img = Image.open(filepath)
            img.show()
        elif Path(filepath).suffix.lower() in VIDEO_EXT:
            dialog = VideoViewer(self, filepath)
            if dialog.exec():
                del dialog

    def press_visualize_button(self):
        query = self.QueryContainer.get_info(self.QueryContainer.current_query_rid)
        match = self.QueryContainer.get_info(self.QueryContainer.current_match_rid)
        dialog = PairXPopup(self, query, match)
        if dialog.exec():
            del dialog

    # ==========================================================================
    # FAVORITE
    # ==========================================================================
    def press_favorite_button(self, rid):
        if self.QueryContainer.get_info(rid, "favorite"):
            self.unfavorite(rid)
        else:
            self.favorite(rid)

    def favorite(self, rid):
        self.mpDB.edit_row('roi', rid, {"favorite": 1})
        # reload database
        self.QueryContainer.load_data()
        self.QueryContainer.filter()
        self.load_query()
        self.load_match()

    def unfavorite(self, rid):
        self.mpDB.edit_row('roi', rid, {"favorite": 0})
        # reload database
        self.QueryContainer.load_data()
        self.QueryContainer.filter()
        self.load_query()
        self.load_match()

    def toggle_query_favorite(self):
        """
        Change Match button to Green when query and match are same iid,
        normal button when not
        """
        if self.QueryContainer.get_info(self.QueryContainer.current_query_rid, "favorite"):
            self.query_image_bar.set_favorite(True)
        else:
            self.query_image_bar.set_favorite(False)

    def toggle_match_favorite(self):
        """
        Change Match button to Green when query and match are same iid,
        normal button when not
        """
        if self.QueryContainer.get_info(self.QueryContainer.current_match_rid, "favorite"):
            self.match_image_bar.set_favorite(True)
        else:
            self.match_image_bar.set_favorite(False)

    # ==========================================================================
    # KEYBOARD HANDLER
    # ==========================================================================
    def keyPressEvent(self, event):
        key = event.key()
        key_text = event.text()
        # Left Arrow
        if key == 16777234:
            self.change_match(self.QueryContainer.current_match - 1)
        # Right Arrow
        elif key == 16777236:
            self.change_match(self.QueryContainer.current_match + 1)
        # Up Arrow
        elif key == 16777235:
            self.change_query(self.QueryContainer.current_query - 1)
        # Down Arrow
        elif key == 16777237:
            self.change_query(self.QueryContainer.current_query + 1)

        # Space - Match
        elif key == 32:
            self.button_match.click()
        # M - Match
        elif key == 77:
            self.button_match.click()
            
        # L - Left Viewpoint
        elif key == 76:
            self.button_viewpoint.set_index(0)
        # R - Right Viewpoint
        elif key == 82:
            self.button_viewpoint.set_index(2)
        # V - Viewpoint
        elif key == 86:
            if self.current_viewpoint == 'Left':
                self.button_viewpoint.set_index(2)
            else:
                self.button_viewpoint.set_index(0)

        # Escape - Home
        elif key ==16777216:
            self.home()

        else:
            print(f"Key pressed: {key_text} (Qt key code: {key})")
