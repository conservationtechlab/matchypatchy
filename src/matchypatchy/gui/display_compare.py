"""
GUI Window for Match Comparisons

"""
import os
from pathlib import Path
from PIL import Image

from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QHeaderView, QTableWidget, QTableWidgetItem)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPalette, QColor

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
from matchypatchy.gui.widgets.gui_assets import NoHoverDelegate

from matchypatchy.database.media import VIDEO_EXT, IMAGE_EXT, fetch_individual


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
        self.edit_stack = []  # placeholder for media edit stack

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
        button_recalc.clicked.connect(lambda: self.initialize(clear_cache=True))
        first_layer.addWidget(button_recalc)

        button_recalc = QPushButton("Quality Control by Individual")
        button_recalc.clicked.connect(self.compare_by_individual)
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
        query_layout.setSpacing(4)
        query_label = QLabel("Query")
        query_label.setStyleSheet("font-size: 18px;")
        query_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        query_layout.addWidget(query_label)
        # Options
        query_options = QHBoxLayout()
        query_options.setContentsMargins(0, 0, 0, 0)
        query_options.setSpacing(6)
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
        query_options_widget = QWidget()
        query_options_widget.setContentsMargins(0, 0, 0, 0)
        query_options_widget.setLayout(query_options)
        query_layout.addWidget(query_options_widget)
        # Query Image
        self.query_image = MediaWidget()
        self.query_image.setStyleSheet("border: 1px solid black;")
        query_layout.addWidget(self.query_image, 1)
        # Query Image Tools
        self.query_image_bar = ImageAdjustBar(self, self.query_image, 'query')
        query_layout.addWidget(self.query_image_bar)

        # MetaData
        self.query_info = QTableWidget()
        self._set_table(self.query_info)
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
        match_layout.setSpacing(4)
        match_label = QLabel("Match")
        match_label.setStyleSheet("font-size: 18px;")
        match_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        match_layout.addWidget(match_label)
        # OptionsVIEWPOINT_DICT
        match_options = QHBoxLayout()
        match_options.setContentsMargins(0, 0, 0, 0)
        match_options.setSpacing(6)
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

        # Similarity Label
        self.match_distance = QLabel("Similarity: ")
        self.match_distance.setFixedHeight(25)
        self.match_distance.setStyleSheet("border: 1px solid black;")
        match_options.addWidget(self.match_distance)

        # Toggle match favorites button
        self.button_match_favorites = QPushButton("Show ♥")
        self.button_match_favorites.setCheckable(True)
        self.button_match_favorites.setChecked(False)
        self.button_match_favorites.clicked.connect(self.toggle_match_favorites_button)
        match_options.addWidget(self.button_match_favorites)

        match_options.addStretch()
        match_options_widget = QWidget()
        match_options_widget.setContentsMargins(0, 0, 0, 0)
        match_options_widget.setLayout(match_options)
        match_layout.addWidget(match_options_widget)

        options_row_height = max(query_options_widget.sizeHint().height(), match_options_widget.sizeHint().height())
        query_options_widget.setFixedHeight(options_row_height)
        match_options_widget.setFixedHeight(options_row_height)

        # Match Image
        self.match_image = MediaWidget()
        self.match_image.setStyleSheet("border: 1px solid black;")
        match_layout.addWidget(self.match_image, 1)
        # Match Image Tools
        self.match_image_bar = ImageAdjustBar(self, self.match_image, 'match')
        match_layout.addWidget(self.match_image_bar)

        # MetaData
        self.match_info = QTableWidget()
        self._set_table(self.match_info)
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
        if self.alert_box and self.alert_box.isVisible():
            self.alert_box.close()
        if warn:
            dialog = AlertPopup(self, prompt="No data to match, process images first.")
            dialog.exec()
            del dialog
        self.parent._set_base_view()

    def validate(self):
        """Go to Media View"""
        self.parent._set_media_view()

    def warn(self, prompt):
        """Create an Alert Popup with given prompt"""
        dialog = AlertPopup(self, prompt=prompt)
        dialog.exec()
        del dialog

    def change_threshold(self, value):
        """Handle changes to the similarity threshold slider"""
        self.threshold = value
        self.QueryContainer.set_threshold(self.threshold)

    # ALERT POPUP MANAGER ------------------------------------------------------
    def show_alert(self, prompt):
        """Progress Popup for Match Thread"""
        if not hasattr(self, 'alert_box') or self.alert_box is None:
            self.alert_box = AlertPopup(self, prompt, progressbar=True, cancel_only=False)
        self.alert_box.update_prompt(prompt)
        self.alert_box.show()

    def update_prompt(self, prompt):
        """Update the prompt in the progress popup"""
        if hasattr(self, 'alert_box') and self.alert_box is not None:
            self.alert_box.update_prompt(prompt)
            self.alert_box.show()

    def update_progress(self, progress):
        """Update the progress bar in the progress popup"""
        if hasattr(self, 'alert_box') and self.alert_box is not None:
            self.alert_box.set_counter(progress)

    def set_progress_max(self, max_value):
        """Set the maximum value for the progress bar"""
        if hasattr(self, 'alert_box') and self.alert_box is not None:
            self.alert_box.set_max(max_value)

    def close_progress(self):
        """Close the progress popup"""
        if hasattr(self, 'alert_box') and self.alert_box is not None:
            self.alert_box.close()
            self.alert_box = None

    # ==========================================================================
    # ON ENTRY
    # ==========================================================================
    def initialize(self, clear_cache=False):
        """Calculate neighbors for all query ROIs, load first query and match"""
        # Disable individual select until feature is implemented on QC
        self.k = self.cfg.KNN  # default knn
        self.compare_type = 'default'
        # show favorite toggle and reset its state
        self.button_match_favorites.setVisible(True)
        self.button_match_favorites.setChecked(False)
        self.button_match_favorites.setStyleSheet("")
        # hide individual filter
        self.filterbar.individual_visible(False)
        self.show_alert("Initializing...")
        self.set_progress_max(0)
        # Delay the heavy work so popup can render
        QTimer.singleShot(100, lambda: self._initialize_query_container(clear_cache))

    def _initialize_query_container(self, clear_cache=False):
        """
        Create the container, load data, then hand off to cache/compute. 
        Filtering happens inside the container as the final step.
        """
        # Tear down any existing query container before creating a new one
        self._teardown_query_container()
        self._cancelled = False
        # Create a new query container instance
        self.QueryContainer = QueryContainer(self)
        self.QueryContainer.progress_update.connect(self.update_progress)
        self.QueryContainer.thread_signal.connect(self.check_matchthread_success)

        # Ensure the alert box rejection is properly connected to the handler
        box = getattr(self, "alert_box", None)
        if box is not None:
            try:
                box.rejected.disconnect(self._on_alert_rejected)
            except (TypeError, RuntimeError):
                pass                      # wasn't connected yet
            box.rejected.connect(self._on_alert_rejected)

        if clear_cache:
            self.logger.info("Clearing KNN cache")
            print("Clearing KNN cache")
            self.QueryContainer.clear_knn_cache()

        # Load raw data only. filter() now runs later, in QueryContainer.finalize()
        if not self.QueryContainer.load_data():
            self.home(warn=True)
            return

        # Store the filter; it's applied after cache load / neighbor calculation
        self.QueryContainer.set_filter(self.filters, self.valid_stations)
        self._cache_or_calculate_neighbors()

    def _teardown_query_container(self):
        """Tear down the existing query container, disconnect signals, and stop its thread."""
        qc = getattr(self, "QueryContainer", None)
        if qc is None:
            return
        # stop receiving signals from the old container
        for sig in (qc.progress_update, qc.thread_signal):
            try:
                sig.disconnect()
            except (TypeError, RuntimeError):
                pass
        qc.stop_calculation()
        # block until the worker thread really finishes
        thread = getattr(qc, "match_thread", None)  # adjust to your attribute name
        if thread is not None and thread.isRunning():
            thread.requestInterruption()
            thread.quit()
            if not thread.wait(3000):
                self.logger.warning("Query thread did not stop in time")
        qc.deleteLater()  # if QueryContainer is a QObject
        self.QueryContainer = None

    def _on_alert_rejected(self):
        """Handle the rejection of the alert box by the user."""
        self._cancelled = True
        qc = getattr(self, "QueryContainer", None)
        if qc is not None:
            qc.stop_calculation()
        box, self.alert_box = self.alert_box, None
        if box is not None:
            try:
                box.rejected.disconnect(self._on_alert_rejected)
            except (TypeError, RuntimeError):
                pass
            box.deleteLater()

    def _cache_or_calculate_neighbors(self):
        """Use cached raw KNN results if available, otherwise compute on unfiltered data."""
        if self._cancelled:
            return
        self.update_prompt("Checking cache...")
        if self.QueryContainer.load_knn_cache():
            self.logger.info("Using cached KNN results")
            # skip to finalize step
            QTimer.singleShot(100, self.QueryContainer.finalize)
        else:
            self.update_prompt("Matching embeddings...")
            self.alert_box.set_max(100)
            QTimer.singleShot(100, self.QueryContainer.calculate_neighbors)

    def check_matchthread_success(self, thread_success):
        cancelled = self._cancelled
        self.close_progress()
        if cancelled:
            return
        if thread_success:
            self.change_query(0)
        elif not self.QueryContainer.filter_matched:
            self.update_prompt("No matches found within filter.")
        else:
            self.update_prompt("No data to compare, all available data from same sequence/capture.")

    # --------------------------------------------------------------------------
    def compare_by_individual(self):
        """
        Enter QC mode, recalculate matches by individual IDs
        
        Does not require a cache
        """
        # must have inviduals to enter QC mode

        if not fetch_individual(self.mpDB).empty:
            self.compare_type = 'qc'
            self.button_match_favorites.setVisible(False)  # hide favorite toggle
            self.QueryContainer = QC_QueryContainer(self)
            self.filterbar.individual_visible(True)
            self.QueryContainer.load_data()
            filtered = self.QueryContainer.filter(filter_dict=self.filters, valid_stations=self.valid_stations)
            # no match thread, have to check success manually
            if filtered:
                self.change_query(0)
            else:
                self.update_prompt("No data to compare within filter.")
        else:
            self.update_prompt("No data to compare, no named individuals to analyze.")

    def compare_manual(self, selected_ids=None):
        """
        Enter manual comparison mode, recalculate matches manually
        
        Does not require a cache
        """
        self.compare_type = 'manual'
        self.button_match_favorites.setVisible(False)  # hide favorite toggle
        self.filterbar.individual_visible(False)
        self.QueryContainer = ManualQueryContainer(self, selected_ids=selected_ids)  # re-establish object
        emb_exist = self.QueryContainer.load_data()
        if emb_exist:
            self.QueryContainer.filter(filter_dict=self.filters, valid_stations=self.valid_stations)
            self.QueryContainer.calculate_neighbors()
            self.change_query(0)
        else:
            self.update_prompt("No data to compare within filter.")

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
            self.compare_by_individual()
        elif self.compare_type == 'manual':
            self.compare_manual()
        else:
            self.initialize()

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
        Match button was clicked, merge query sequence and current match.
        Optimized to only update affected data.
        """
        query_sequence_id = self.QueryContainer.get_query_sequence_id()
        match_sequence_id = self.QueryContainer.get_match_sequence_id()
        
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
            else:
                return  # User cancelled - don't proceed
        else:
            # Match has a name - merge sequences
            self.QueryContainer.merge()
        
        # update affected sequences
        self.QueryContainer.update_sequences_in_place(query_sequence_id, match_sequence_id)
        
        # Refresh only the current views (not all data)
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
            
            # update affected sequences
            query_sequence_id = [self.QueryContainer.get_query_sequence_id()]
            self.QueryContainer.update_partial_sequences(query_sequence_id)
            
            # reload data
            self.load_query()
            self.load_match()
        del dialog

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
        self.match_counter.setText(f"1/{len(self.QueryContainer.current_match_rois)}")

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
        self.match_counter.setText(f"{self.QueryContainer.current_match+1}/{len(self.QueryContainer.current_match_rois)}")
        self.load_match()

    def load_query(self):
        """
        Load Image and Metadata for Current Query ROI
        """
        self.query_image.load(self.QueryContainer.get_info(self.QueryContainer.current_query_rid, "filepath"),
                              frame=self.QueryContainer.get_info(self.QueryContainer.current_query_rid, "frame"),
                              bbox=self.QueryContainer.get_info(self.QueryContainer.current_query_rid, 'bbox'), crop=True)
        metadata = self.QueryContainer.get_info(self.QueryContainer.current_query_rid, "metadata")
        self.format_metadata(self.query_info, metadata)
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
        self.format_metadata(self.match_info, metadata)
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

    # METADATA TABLE
    def _set_table(self, table):
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setMouseTracking(False)
        table.setItemDelegate(NoHoverDelegate())
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setVisible(False)
        table.setShowGrid(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setRowCount(7)
        table.setColumnCount(4) 
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(0, 120)
        table.setColumnWidth(1, 150)
        table.setColumnWidth(2, 120)
        table.setMaximumHeight(250)
        for i in range(table.rowCount() - 1):
            table.setRowHeight(i, 34)  # Use consistent height for all rows
        table.setStyleSheet("""
            QTableWidget {
                border: 1px solid;
                border-radius: 4px;
                font-size: 15px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTableWidget::item {
                padding: 6px;
            }
        """)

    def format_metadata(self, table, info_dict):
        table.setAlternatingRowColors(False)  # we are doing custom row shading

        base = self.palette().color(QPalette.ColorRole.Base)
        r, g, b = base.red(), base.green(), base.blue()

        offset = 24
        # light mode
        if r + offset > 255:
            offset = -offset

        alt = QColor(
            min(255, r + offset),
            min(255, g + offset),
            min(255, b + offset),)
        alt.setAlpha(90)  # very subtle, adjust 20-40 as desired

        def make_item(text, is_label=False, italic=False, row_bg=None):
            item = QTableWidgetItem(str(text) if text is not None else "")
            if row_bg is not None:
                item.setBackground(row_bg)

            item.setForeground(self.palette().color(QPalette.ColorRole.Text) if is_label else self.palette().color(QPalette.ColorRole.WindowText))
            if is_label:
                font = item.font()
                font.setBold(True)
                item.setFont(font)

            if italic:
                font = item.font()
                font.setItalic(True)
                item.setFont(font)

            return item

        rows = [
            ("Name:",        info_dict['Name'],          "File Name",  os.path.basename(info_dict['Filepath'])),
            ("Viewpoint:",   info_dict['Viewpoint'],      "Timestamp:",  info_dict['Timestamp']),
            ("Sex:",         info_dict['Sex'],            "Region:",     info_dict['Region']),
            ("Age:",         info_dict['Age'],            "Survey:",     info_dict['Survey']),
            ("Sequence ID:", info_dict['Sequence ID'],    "Station:",    info_dict['Station']),
            ("External ID:", info_dict['External ID'],    "Camera:",     info_dict['Camera']),
            ("Comment:",     info_dict['Comment'],        None,         None),
        ]

        for i, (label1, value1, label2, value2) in enumerate(rows):
            row_bg = alt if i % 2 else base

            if label2 is None:
                table.setItem(i, 0, make_item(label1, is_label=True, row_bg=row_bg))
                table.setItem(i, 1, make_item(value1, italic=True, row_bg=row_bg))
                table.setSpan(i, 1, 1, 3)
            else:
                table.setItem(i, 0, make_item(label1, is_label=True, row_bg=row_bg))
                table.setItem(i, 1, make_item(value1, row_bg=row_bg))
                table.setItem(i, 2, make_item(label2, is_label=True, row_bg=row_bg))
                table.setItem(i, 3, make_item(value2, row_bg=row_bg))


    # ==========================================================================
    # IMAGE MANIPULATION
    # ==========================================================================
    def edit_image(self, rid):
        """
        Open Image in MatchyPatchy Single Image Popup to Edit Metadata
        Note: Redraws query and match
        """
        data = self.QueryContainer.get_info(rid).copy()
        data["id"] = rid
        data = data.to_frame().T
        dialog = MediaEditPopup(self, data, data_type=1)
        if dialog.exec():
            self.edit_stack = dialog.get_edit_stack()
            self.save_changes()
            # reload data
            # TODO: only reload the affected sequences instead of full reload
            self.QueryContainer.load_data()
            self.QueryContainer.filter()
            self.load_query()
            self.load_match()
        del dialog

    def save_changes(self):
        # commit all changes in self.edit_stack to database
        while len(self.edit_stack) > 0:
            edit = self.edit_stack.pop()
            id = edit['rid']
            replace_dict = {edit['reference']: edit['new_value']}
            # determine table to edit based on reference column
            if edit['reference'] in {'age', 'sex'}:
                iid = self.QueryContainer.get_info(id, "individual_id")
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
        # TODO: update only the affected sequences in the QueryContainer instead of full reload
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
