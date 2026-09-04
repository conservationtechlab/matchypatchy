"""
GUI Window for Match Comparisons

"""
import os
from pathlib import Path
import pandas as pd
from PIL import Image

from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QSlider)
from PyQt6.QtCore import Qt

from matchypatchy.gui.widgets.widget_media import MediaWidget, VideoViewer
from matchypatchy.gui.widgets.widget_image_adjustment import ImageAdjustBar
from matchypatchy.gui.dialogs.popup_alert import AlertPopup
from matchypatchy.gui.dialogs.popup_individual import IndividualFillPopup
from matchypatchy.gui.dialogs.popup_media_edit import MediaEditPopup
from matchypatchy.gui.dialogs.popup_pairx import PairXPopup
from matchypatchy.gui.widgets.gui_assets import SequenceSelector, SliderWithLabel, VerticalSeparator, StandardButton, ThreePointSlider
from matchypatchy.gui.widgets.widget_filterbar import FilterBar

from matchypatchy.gui.query import QueryContainer
from matchypatchy.gui.qc_query import QC_QueryContainer
from matchypatchy.gui.manual_query import ManualQueryContainer

from matchypatchy.database.media import VIDEO_EXT, IMAGE_EXT, fetch_individual

# TODO: recalculate matches button clears cache
# determine how long to keep cache


class DisplayCompare(QWidget):
    """GUI class for displaying and managing match comparisons."""

    MATCH_STYLE = """ QPushButton { background-color: #2e7031; color: white; }"""
    FAVORITE_STYLE = """ QPushButton { background-color: #b51b32; color: white; }"""
    VIEWPOINT_DICT = {0: 'Left', 1: 'Any', 2: 'Right'}

    def __init__(self, parent):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.parent = parent
        self.logger = parent.logger
        self.cfg = parent.cfg
        self.mpDB = parent.mpDB
        self.k = self.cfg.KNN  # default knn
        self.distance_metric = 'cosine'
        self.threshold = 50
        self.current_viewpoint = 1
        self.compare_type = 'default'  # whether 'default', 'qc' or 'manual'
        self.QueryContainer = QueryContainer(self)
        self.progress = None   # placeholder for progress popup
        self.edit_stack = []  # placeholder for media edit stack
        self.query_load_thread = None  # placeholder for image load thread
        self.match_load_thread = None  # placeholder for image load thread

        self.data = pd.DataFrame()  # placeholder for query data to be used in filters

        # Options Bar ==============================================================
        layout = QVBoxLayout()
        first_layer = QHBoxLayout()
        button_home = StandardButton("Home", width=80)
        button_home.clicked.connect(lambda: self.home(warn=False))
        first_layer.addWidget(button_home)

        button_validate = QPushButton("View Data")
        button_validate.pressed.connect(self.validate)
        first_layer.addWidget(button_validate)
        first_layer.addWidget(VerticalSeparator())

        self.threshold_slider = SliderWithLabel("Similarity Threshold", min_val=0, max_val=100, initial=self.threshold)
        self.threshold_slider.slider_value_changed.connect(self.change_threshold)
        first_layer.addWidget(self.threshold_slider, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        button_recalc = QPushButton("Recalculate Matches")
        button_recalc.clicked.connect(self.calculate_neighbors)
        first_layer.addWidget(button_recalc)

        button_recalc = QPushButton("Quality Control by Individual")
        button_recalc.clicked.connect(self.calculate_by_individual)
        first_layer.addWidget(button_recalc)

        # FILTERBAR --------------------------------------------------------------
        first_layer.addSpacing(10)
        first_layer.addWidget(VerticalSeparator())
        self.filterbar = FilterBar(self, 100)
        self.filterbar.viewpoint_visible(False)
        self.filterbar.individual_visible(False)
        self.filterbar.unidentified_visible(False)
        self.filterbar.favorites_visible(False)
        self.filterbar.no_roi_visible(False)

        first_layer.addWidget(self.filterbar)
        # get initial filters
        self.filters = self.filterbar.get_filters()
        self.valid_stations = self.filterbar.get_valid_stations()

        button_filter = QPushButton("Apply Filters")
        button_filter.clicked.connect(self.filter_neighbors)
        first_layer.addWidget(button_filter)

        first_layer.addStretch()
        layout.addLayout(first_layer)

        # IMAGE COMPARISON =====================================================
        image_layout = QHBoxLayout()
        # QUERY ----------------------------------------------------------------
        query_layout = QVBoxLayout()
        query_label = QLabel("Query")
        query_label.setStyleSheet("font-size: 18px;")
        query_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        query_layout.addWidget(query_label)
        query_layout.addSpacing(5)
        # Options
        query_options = QHBoxLayout()
        query_options.addStretch()
        # # Query Number

        # Query Selector for selecting the current query image within a sequence
        self.query_selector = SequenceSelector("Query Image:")
        query_options.addWidget(self.query_selector)
        self.query_selector.button_previous.clicked.connect(lambda: self.change_query(self.QueryContainer.current_query - 1))
        self.query_selector.button_next.clicked.connect(lambda: self.change_query(self.QueryContainer.current_query + 1))
    
        # Sequence Selector for selecting the current sequence within a set of sequences
        self.sequence_selector = SequenceSelector("Sequence:")
        self.sequence_selector.button_previous.clicked.connect(lambda: self.change_query_in_sequence(self.QueryContainer.current_query_sn - 1))
        self.sequence_selector.button_next.clicked.connect(lambda: self.change_query_in_sequence(self.QueryContainer.current_query_sn + 1))
        query_options.addWidget(self.sequence_selector)

        query_options.addStretch()
        query_layout.addLayout(query_options)
        # Query Image
        self.query_image = MediaWidget()
        self.query_image.setStyleSheet("border: 1px solid black;")
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

        self.match_counter = QLabel("/9")
        middle_column.addWidget(self.match_counter, alignment=Qt.AlignmentFlag.AlignCenter)

        self.button_match = QPushButton("Match")
        self.button_match.pressed.connect(self.press_match_button)
        self.button_match.setCheckable(True)
        self.button_match.setChecked(False)
        self.button_match.setFixedSize(50, 50)
        middle_column.addWidget(self.button_match,
                                alignment=Qt.AlignmentFlag.AlignCenter)
        middle_column.addStretch()
        image_layout.addLayout(middle_column)

        # MATCH ----------------------------------------------------------------
        match_layout = QVBoxLayout()
        match_label = QLabel("Match")
        match_label.setStyleSheet("font-size: 18px;")
        match_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        match_layout.addWidget(match_label)
        match_layout.addSpacing(5)
        # OptionsVIEWPOINT_DICT
        match_options = QHBoxLayout()
        match_options.addStretch()

        # Viewpoint Toggle
        self.button_viewpoint = ThreePointSlider(initial=1)
        self.button_viewpoint.state_changed.connect(self.toggle_viewpoint)
        match_options.addWidget(self.button_viewpoint)
        match_options.addSpacing(20)

        # # Match Number
        self.match_selector = SequenceSelector("Match Image:")
        self.match_selector.button_previous.clicked.connect(lambda: self.change_match(self.QueryContainer.current_match - 1))
        self.match_selector.button_next.clicked.connect(lambda: self.change_match(self.QueryContainer.current_match + 1))
        match_options.addWidget(self.match_selector)

        self.match_distance = QLabel("Similarity: ")
        self.match_distance.setFixedHeight(25)
        self.match_distance.setStyleSheet("border: 1px solid black;")
        match_options.addWidget(self.match_distance)

        self.button_match_favorites = QPushButton("Show ♥")
        self.button_match_favorites.setCheckable(True)
        self.button_match_favorites.setChecked(False)
        self.button_match_favorites.clicked.connect(self.toggle_match_favorites_button)
        match_options.addWidget(self.button_match_favorites)

        match_options.addStretch()
        match_layout.addLayout(match_options)

        # Match Image
        self.match_image = MediaWidget()
        self.match_image.setStyleSheet("border: 1px solid black;")
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
        # PAIRX DEACTIVATED
        # Buttons
        # bottom_layer = QHBoxLayout()
        # button_visualize = QPushButton("Visualize Match")
        # button_visualize.pressed.connect(self.press_visualize_button)
        # bottom_layer.addWidget(button_visualize)
        # layout.addLayout(bottom_layer)
        self.setLayout(layout)

        # remove focus from buttons to keep keyboard shortcuts working
        self.set_no_focus()
        # ======================================================================

    def set_no_focus(self):
        """Remove focus from all QPushButton children to keep keyboard shortcuts working."""
        for child in self.findChildren(QWidget):
            if isinstance(child, (QPushButton)):
                child.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def update_project(self, cfg, mpDB):
        """Update database object"""
        self.cfg = cfg
        self.mpDB = mpDB
        self.filterbar.update_project(mpDB)

    # ==========================================================================
    # GUI
    # ==========================================================================
    def home(self, warn=False):
        """Return to Base View"""
        if self.progress and self.progress.isVisible():
            self.progress.close()
        if warn:
            dialog = AlertPopup(self, prompt="No data to match, process images first.")
            if dialog.exec():
                del dialog
        self.parent._set_base_view()

    def validate(self):
        """Go to Media View"""
        self.parent._set_media_view()

    def warn(self, prompt):
        """Create an Alert Popup with given prompt"""
        dialog = AlertPopup(self, prompt=prompt)
        if dialog.exec():
            del dialog

    def change_threshold(self, value):
        """Handle changes to the similarity threshold slider"""
        self.threshold = value
        self.QueryContainer.set_threshold(self.threshold)

    # ==========================================================================
    # ON ENTRY
    # ==========================================================================
    def calculate_neighbors(self):
        """Calculate neighbors for all query ROIs, load first query and match"""
        # Disable individual select until feature is implemented on QC
        self.compare_type = 'default'
        # show favorite toggle and reset its state
        self.button_match_favorites.setVisible(True)
        self.button_match_favorites.setChecked(False)
        self.button_match_favorites.setStyleSheet("")
        # hide individual filter
        self.filterbar.individual_visible(False)
        # run knn thread on entry
        self.k = self.cfg.KNN  # default knn
        self.QueryContainer = QueryContainer(self)  # re-establish object
        self.QueryContainer.loaded_data.connect(self.handle_query_data_loaded)
        emb_exist = self.QueryContainer.load_data()
        if emb_exist:
            self.QueryContainer.filter(filter_dict=self.filters, valid_stations=self.valid_stations)
            self.show_progress("Matching embeddings... This may take a while.")
            self.QueryContainer.calculate_neighbors()
            self.progress.rejected.connect(self.QueryContainer.match_thread.requestInterruption)
            self.QueryContainer.thread_signal.connect(self.check_matchthread_success)
        else:
            self.home(warn=True)

    def handle_query_data_loaded(self, data):
        """Handle data loaded signal from QueryContainer, update self.data for filters"""
        self.data = data

    def show_progress(self, prompt):
        """Progress Popup for Match Thread"""
        self.progress = AlertPopup(self, prompt, progressbar=True, cancel_only=True)
        self.progress.show()

    def check_matchthread_success(self, thread_success):
        """Check if match thread was successful, load first query if so"""
        if thread_success:
            self.change_query(0)
        else:
            self.warn(prompt="No data to compare, all available data from same sequence/capture.")

    def calculate_by_individual(self):
        """Enter QC mode, recalculate matches by individual IDs"""
        # must have inviduals to enter QC mode
        if not fetch_individual(self.mpDB).empty:
            self.compare_type = 'qc'
            self.button_match_favorites.setVisible(False)  # hide favorite toggle
            self.QueryContainer = QC_QueryContainer(self)
            self.QueryContainer.loaded_data.connect(self.handle_query_data_loaded)
            self.filterbar.individual_visible(True)
            self.QueryContainer.load_data()
            filtered = self.QueryContainer.filter(filter_dict=self.filters, valid_stations=self.valid_stations)
            # no match thread, have to check success manually
            if filtered:
                self.change_query(0)
            else:
                self.warn(prompt="No data to compare within filter.")
        else:
            self.warn(prompt="No data to compare, no named individuals to analyze.")

    def compare_manual(self, selected_ids=None):
        """Enter manual comparison mode, recalculate matches manually"""
        self.compare_type = 'manual'
        self.button_match_favorites.setVisible(False)  # hide favorite toggle
        self.filterbar.individual_visible(False)
        self.QueryContainer = ManualQueryContainer(self, selected_ids=selected_ids)  # re-establish object
        self.QueryContainer.loaded_data.connect(self.handle_query_data_loaded)
        emb_exist = self.QueryContainer.load_data()
        if emb_exist:
            self.QueryContainer.filter(filter_dict=self.filters, valid_stations=self.valid_stations)
            self.QueryContainer.calculate_neighbors()
            self.change_query(0)
        else:
            self.warn(prompt="No data to compare within filter.")

    def toggle_match_favorites_button(self):
        """
        Change Match Favorites button to indicate whether it is active
        """
        if self.button_match_favorites.isChecked():
            # NEED TO ADD FOR BOTH QUERY CONTAINER
            self.button_match_favorites.setText("Show KNN")
            self.button_match_favorites.setStyleSheet(self.FAVORITE_STYLE)
            self.QueryContainer.set_match_favorites(True)
        else:
            self.button_match_favorites.setText("Show ♥")
            self.button_match_favorites.setStyleSheet("")
            self.QueryContainer.set_match_favorites(False)
        # reload the current match to reflect any changes in favorites
        self.change_match(0)

    # ==========================================================================
    # FILTERS
    # ==========================================================================
    def refresh_filters(self):
        """Clear and re-apply filters from filterbar"""
        self.filterbar.refresh_filters()
        self.filters = self.filterbar.get_filters()
        self.valid_stations = self.filterbar.get_valid_stations()

    def filter_neighbors(self):
        """Apply filters from filterbar to current neighbor dict"""
        self.filters = self.filterbar.get_filters()
        self.valid_stations = self.filterbar.get_valid_stations()

        if self.compare_type == 'qc':
            self.calculate_by_individual()
        elif self.compare_type == 'manual':
            self.compare_manual()
        else:
            self.calculate_neighbors()

    # ==========================================================================
    # MATCHING PROCESS
    # ==========================================================================
    def press_match_button(self):
        """Handle the press event for the Match button."""
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
        """If already matched, unmatch current query from IID"""
        name = self.QueryContainer.get_info(self.QueryContainer.current_match_rid, 'name')
        dialog = AlertPopup(self,
                            prompt=f"This will remove Match from individual '{name}'. Are you sure?",
                            cancel_only=False)
        if dialog.exec():
            self.QueryContainer.unmatch()
        del dialog
        # reload data
        self.QueryContainer.load_data()
        self.QueryContainer.filter()
        self.load_query()
        self.load_match()

    # ==========================================================================
    # LOAD FUNCTIONS
    # ==========================================================================
    def get_rid(self, side):
        """Get current rid for query or match side from QueryContainer"""
        if side == "query":
            return self.QueryContainer.current_query_rid
        else:
            return self.QueryContainer.current_match_rid

    def change_query(self, n):
        """Load new query to the nth sequence in the Query queue and reset match to first"""
        self.QueryContainer.set_query(n)
        # update text
        self.query_selector.set_total(self.QueryContainer.n_queries)
        self.query_selector.set_current_number(self.QueryContainer.current_query)

        self.sequence_selector.set_total(len(self.QueryContainer.current_query_rois))
        self.sequence_selector.set_current_number(self.QueryContainer.current_query_sn)

        self.match_selector.set_total(len(self.QueryContainer.current_match_rois))
        self.match_selector.set_current_number(self.QueryContainer.current_match)

        self.query_image_bar.reset()
        self.match_image_bar.reset()
        # load new images
        self.toggle_viewpoint(self.current_viewpoint)  # toggle to reset rois to current viewpoint

    def change_query_in_sequence(self, n):
        """Load nth image within the current sequence"""
        self.QueryContainer.set_within_query_sequence(n)
        self.query_image_bar.reset()
        self.sequence_selector.set_current_number(self.QueryContainer.current_query_sn)
        self.load_query()

    def change_match(self, n):
        """Load nth match within the current match queue"""
        self.QueryContainer.set_match(n)
        self.match_image_bar.reset()
        self.match_selector.set_total(len(self.QueryContainer.current_match_rois))
        self.match_selector.set_current_number(self.QueryContainer.current_match)
        self.load_match()

    def load_query(self):
        """
        Load Image and Metadata for Current Query ROI
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
        Load Image and Metadata for Current Match ROI
        """
        distance = 1 - self.QueryContainer.current_distance()
        self.match_distance.setText(f"Similarity: {distance:.2f}")

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
        self.current_viewpoint = selected_viewpoint
        viewpoints_available = self.QueryContainer.toggle_viewpoint(self.current_viewpoint)
        if not viewpoints_available:
            self.warn(prompt="No images available for this viewpoint. Showing all available images.")
            self.button_viewpoint.set_index(1)

        # update gui counts
        self.sequence_selector.set_total(len(self.QueryContainer.current_query_rois))
        self.sequence_selector.set_current_number(self.QueryContainer.current_query_sn)
        self.match_selector.set_total(len(self.QueryContainer.current_match_rois))
        self.match_selector.set_current_number(self.QueryContainer.current_match)

        # load images and data
        self.load_query()
        self.load_match()

    def format_metadata(self, info_dict, spacing=1):
        """Format metadata dictionary into an HTML string for display."""
        spacer = "&nbsp;" * 20
        html_text = f"""<div style="line-height: {spacing}; width: 100%; height: 100%;">
                            <table cellspacing="5">
                            <tr>
                                <td>Name:</td><td>{info_dict['Name']}</td>
                                <td>{spacer}</td>
                                <td>File Name:</td><td>{os.path.basename(info_dict['Filepath'])}</td>
                            </tr><tr>
                                <td>Viewpoint:</td><td>{info_dict['Viewpoint']}</td>
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
                                <td>Sequence ID:</td><td>{info_dict['Sequence ID']}</td>
                                <td>{spacer}</td>
                                <td>Station:</td><td>{info_dict['Station']}</td>
                            </tr><tr>
                                <td>Comment:</td><td>{info_dict['Comment']}</td>
                            </tr>
                            </table>
                        </div>
                    """
        return html_text

    # ==========================================================================
    # IMAGE MANIPULATION
    # ==========================================================================
    def edit_image(self, rid):
        """
        Open Image in MatchyPatchy Single Image Popup to Edit Metadata
        Note: Redraws query and match
        """
        data = self.QueryContainer.get_info(rid)
        data["id"] = rid
        data = data.to_frame().T
        dialog = MediaEditPopup(self, data, data_type=1)
        if dialog.exec():
            self.edit_stack = dialog.get_edit_stack()
            self.save_changes()
            # reload data
            self.QueryContainer.load_data()
            self.QueryContainer.filter()
            self.load_query()
            self.load_match()
        del dialog

    def save_changes(self):
        # commit all changes in self.edit_stack to database
        while len(self.edit_stack) > 0:
            edit = self.edit_stack.pop()
            id = edit['id']
            replace_dict = {edit['reference']: edit['new_value']}
            # determine table to edit based on reference column
            if edit['reference'] in {'age', 'sex'}:
                iid = self.data.loc[self.data['id'] == id, 'individual_id'].values[0]
                self.mpDB.edit_row("individual", iid, replace_dict, allow_none=False, quiet=False)
            elif edit['reference'] in {'comment'}:
                self.mpDB.edit_row("media", id, replace_dict, allow_none=True, quiet=False)
            else:
                self.mpDB.edit_row("roi", id, replace_dict, allow_none=False, quiet=False)

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
        """Open PairX Popup to visualize query and match images together"""
        query = self.QueryContainer.get_info(self.QueryContainer.current_query_rid)
        match = self.QueryContainer.get_info(self.QueryContainer.current_match_rid)
        # dialog = PairXPopup(self, query, match)
        # if dialog.exec():
        #     del dialog

    # ==========================================================================
    # FAVORITE
    # ==========================================================================
    def press_favorite_button(self, rid):
        """Toggle favorite status for given rid"""
        if self.QueryContainer.get_info(rid, "favorite"):
            # set favorite to false
            self.favorite(rid, 0)
        else:
            # set favorite to true
            self.favorite(rid, 1)

    def favorite(self, rid, value):
        """Set favorite status for given rid"""
        self.mpDB.edit_row('roi', rid, {"favorite": value})
        # reload database
        self.QueryContainer.load_data()
        self.QueryContainer.filter()
        self.load_query()
        self.load_match()

    def toggle_query_favorite(self):
        """Change Favorite button to Red when query is favorite"""
        if self.QueryContainer.get_info(self.QueryContainer.current_query_rid, "favorite"):
            self.query_image_bar.set_favorite(True)
        else:
            self.query_image_bar.set_favorite(False)

    def toggle_match_favorite(self):
        """Change Favorite button to Red when query is favorite"""
        if self.QueryContainer.get_info(self.QueryContainer.current_match_rid, "favorite"):
            self.match_image_bar.set_favorite(True)
        else:
            self.match_image_bar.set_favorite(False)

    # ==========================================================================
    # KEYBOARD HANDLER
    # ==========================================================================
    def keyPressEvent(self, event):
        """Handle key press events for navigation and actions."""
        self.setFocus()  # ensure window has focus to receive key events
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

        # A - Previous Query in Sequence
        elif key == 65:
            self.change_query_in_sequence(self.QueryContainer.current_query_sn - 1)
        # D - Next Query in Sequence
        elif key == 68:
            self.change_query_in_sequence(self.QueryContainer.current_query_sn + 1)
        # W - Previous Query
        elif key == 87:
            self.change_query(self.QueryContainer.current_query - 1)
        # S - Next Query
        elif key == 83:
            self.change_query(self.QueryContainer.current_query + 1)

        # Space - Match
        elif key == 32:
            self.confirm_match()
        # M - Match
        elif key == 77:
            self.confirm_match()
        # U - Unmatch
        elif key == 85:
            self.unmatch()

        # L - Left Viewpoint
        elif key == 76:
            self.button_viewpoint.set_index(0)
        # R - Right Viewpoint
        elif key == 82:
            self.button_viewpoint.set_index(2)
        # V - Viewpoint
        elif key == 86:
            if self.current_viewpoint == 0:
                self.button_viewpoint.set_index(2)
            else:
                self.button_viewpoint.set_index(0)

        # Escape - Home
        elif key == 16777216:
            self.home()

        else:
            print(f"Key pressed: {key_text} (Qt key code: {key})")
