"""
GUI Window for Match Comparisons

"""
import logging
import math
import os
from pathlib import Path
from PIL import Image

from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
                             QHeaderView, QTableWidget, QTableWidgetItem, QComboBox, QProgressBar)
from PyQt6.QtCore import Qt, QEvent, QTimer
from PyQt6.QtGui import QPalette, QColor

from matchypatchy.gui.widgets.widget_media import MediaWidget, VideoViewer
from matchypatchy.gui.widgets.widget_image_adjustment import ImageAdjustBar
from matchypatchy.gui.dialogs.popup_alert import AlertPopup
from matchypatchy.gui.dialogs.popup_individual import IndividualFillPopup
from matchypatchy.gui.dialogs.popup_media_edit import MediaEditPopup
from matchypatchy.gui.dialogs.popup_pairx import PairXPopup
from matchypatchy.gui.widgets.gui_assets import SliderWithLabel, CounterNav, ViewpointToggle
from matchypatchy.gui.widgets.widget_candidates import CandidateStrip
from matchypatchy.gui.widgets.styles import (ACCENT, ACCENT_SOFT, ACCENT_INK, IMAGE_WELL, icon, label,
                                             set_variant, set_role)
from matchypatchy.database.thumbnails import fetch_roi_thumbnails
from matchypatchy.gui.widgets.widget_filterbar import FilterBar

from matchypatchy.gui.query_base import QueryContainer
from matchypatchy.gui.query_qc import QC_QueryContainer
from matchypatchy.gui.query_manual import ManualQueryContainer
from matchypatchy.gui.widgets.gui_assets import NoHoverDelegate

from matchypatchy.database.media import VIDEO_EXT, IMAGE_EXT, fetch_individual, set_favorite, save_edits
from matchypatchy.project import UsesProject


logger = logging.getLogger(__name__)


class DisplayCompare(UsesProject, QWidget):
    """GUI class for displaying and managing match comparisons."""

    MATCH_STYLE = """ QPushButton { background-color: #2e7031; color: white; }"""
    MODES = {'default': 0, 'qc': 1, 'manual': 2}
    # Match button once query and candidate are the same individual
    MATCHED_STYLE = f""" QPushButton {{ background-color: {ACCENT_SOFT}; color: {ACCENT_INK}; border-color: {ACCENT_SOFT}; }}"""
    FAVORITE_STYLE = """ QPushButton { background-color: #b51b32; color: white; }"""
    VIEWPOINT_DICT = {0: 'Left', 1: 'Any', 2: 'Right'}

    def __init__(self, parent):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.parent = parent
        self.project = parent.project
        self.k = self.cfg.KNN  # default knn
        self.distance_metric = 'cosine'
        self.threshold = 50
        self.current_viewpoint = 1
        self.compare_type = 'default'  # whether 'default', 'qc' or 'manual'
        self.alert_box = None  # progress popup, set by show_alert
        self.QueryContainer = QueryContainer(self)
        self.edit_stack = []  # placeholder for media edit stack

        # TOP BAR ==============================================================
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        top = QFrame()
        top.setObjectName("TopBar")
        first_layer = QHBoxLayout(top)
        first_layer.setContentsMargins(20, 10, 20, 10)
        first_layer.setSpacing(14)
        title = QLabel("Match")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        first_layer.addWidget(title)

        # Query Selector: previous/next query, W S or up/down
        self.query_selector = CounterNav("Query")
        self.query_selector.button_previous.setToolTip("Previous query (W / ↑)")
        self.query_selector.button_next.setToolTip("Next query (S / ↓)")
        self.query_selector.button_previous.clicked.connect(lambda: self.change_query(self.QueryContainer.current_query - 1))
        self.query_selector.button_next.clicked.connect(lambda: self.change_query(self.QueryContainer.current_query + 1))
        query_nav = QVBoxLayout()
        query_nav.setSpacing(4)
        query_nav.addWidget(self.query_selector)
        self.query_progress = QProgressBar()
        self.query_progress.setTextVisible(False)
        self.query_progress.setFixedHeight(4)
        self.query_progress.setStyleSheet(f"QProgressBar {{ border: 0px; background: palette(midlight); border-radius: 2px; }}"
                                          f"QProgressBar::chunk {{ background: {ACCENT}; border-radius: 2px; }}")
        query_nav.addWidget(self.query_progress)
        first_layer.addLayout(query_nav)

        # Mode: ranked candidates, quality control by individual, or the rois picked in the media view
        first_layer.addWidget(label("Mode", "muted"))
        self.mode_select = QComboBox()
        self.mode_select.addItems(["Ranked candidates", "QC by individual", "Manual selection"])
        self.mode_select.setItemData(2, 0, Qt.ItemDataRole.UserRole - 1)  # only entered from the media view
        self.mode_select.activated.connect(self.change_mode)
        self.mode_select.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        first_layer.addWidget(self.mode_select)

        # Viewpoint Toggle, L R V
        self.button_viewpoint = ViewpointToggle(initial=1)
        self.button_viewpoint.state_changed.connect(self.toggle_viewpoint)
        first_layer.addWidget(self.button_viewpoint)

        self.threshold_slider = SliderWithLabel("Similarity ≥", min_val=0, max_val=100, initial=self.threshold)
        self.threshold_slider.label.setText("Similarity ≥")
        self.threshold_slider.slider_value_changed.connect(self.change_threshold)
        first_layer.addWidget(self.threshold_slider, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        first_layer.addStretch()

        # FILTERBAR: rematches as a filter changes
        self.filterbar = FilterBar(self, 120)
        self.filterbar.viewpoint_visible(False)
        self.filterbar.individual_visible(False)
        self.filterbar.unidentified_visible(False)
        self.filterbar.favorites_visible(False)
        self.filterbar.no_roi_visible(False)
        for combo in (self.filterbar.region_select, self.filterbar.survey_select,
                      self.filterbar.station_select, self.filterbar.individual_select):
            combo.activated.connect(lambda _i: QTimer.singleShot(0, self.filter_neighbors))
        first_layer.addWidget(self.filterbar)
        # get initial filters
        self.filters = self.filterbar.get_filters()
        self.valid_stations = self.filterbar.get_valid_stations()

        button_recalc = QPushButton()
        button_recalc.setIcon(icon("recalc", "#7A807B"))
        button_recalc.setToolTip("Recalculate matches")
        button_recalc.clicked.connect(lambda: self.initialize(clear_cache=True))
        first_layer.addWidget(button_recalc)
        layout.addWidget(top)

        # IMAGE COMPARISON =====================================================
        image_layout = QHBoxLayout()
        image_layout.setContentsMargins(20, 12, 20, 0)
        image_layout.setSpacing(16)
        # QUERY ----------------------------------------------------------------
        query_layout = QVBoxLayout()
        query_layout.setSpacing(6)
        query_options = QHBoxLayout()
        query_options.setSpacing(10)
        query_options.addWidget(label("QUERY", "eyebrow"))
        self.query_name = QLabel("")
        self.query_name.setStyleSheet("font-weight: 600;")
        self.query_name.setMinimumWidth(40)
        query_options.addWidget(self.query_name, 1)
        self.query_status = label("Unidentified", "pill-warn")
        query_options.addWidget(self.query_status)
        # Sequence Selector for the query image within its sequence, A D
        self.sequence_selector = CounterNav("Sequence")
        self.sequence_selector.button_previous.setToolTip("Previous image in sequence (A)")
        self.sequence_selector.button_next.setToolTip("Next image in sequence (D)")
        self.sequence_selector.button_previous.clicked.connect(lambda: self.change_query_in_sequence(self.QueryContainer.current_query_sn - 1))
        self.sequence_selector.button_next.clicked.connect(lambda: self.change_query_in_sequence(self.QueryContainer.current_query_sn + 1))
        query_options.addWidget(self.sequence_selector)
        query_layout.addLayout(query_options)
        # Query Image, with its toolbar floating over it
        self.query_image = MediaWidget()
        self.query_image.setMinimumHeight(300)
        self.query_image.setStyleSheet(f"background: {IMAGE_WELL};")
        query_layout.addWidget(self.query_image, 1)
        self.query_image_bar = ImageAdjustBar(self, self.query_image, 'query')

        # MetaData
        self.query_info = QTableWidget()
        self._set_table(self.query_info)
        query_layout.addWidget(self.query_info)
        image_layout.addLayout(query_layout, 1)

        # MATCH ----------------------------------------------------------------
        match_layout = QVBoxLayout()
        match_layout.setSpacing(6)
        match_options = QHBoxLayout()
        match_options.setSpacing(10)
        # # Match Number, left/right arrows
        self.match_selector = CounterNav("CANDIDATE", buttons=False)
        self.match_selector.label.setStyleSheet("color: palette(placeholder-text); font-size: 11px; font-weight: 600;")
        self.match_selector.button_previous.clicked.connect(lambda: self.change_match(self.QueryContainer.current_match - 1))
        self.match_selector.button_next.clicked.connect(lambda: self.change_match(self.QueryContainer.current_match + 1))
        match_options.addWidget(self.match_selector)
        self.match_name = label("", "pill-ok")
        match_options.addWidget(self.match_name)
        match_options.addStretch()
        # Similarity
        self.similarity_bar = QProgressBar()
        self.similarity_bar.setRange(0, 100)
        self.similarity_bar.setTextVisible(False)
        self.similarity_bar.setFixedSize(110, 8)
        self.similarity_bar.setStyleSheet(f"QProgressBar {{ border: 0px; background: palette(midlight); border-radius: 4px; }}"
                                          f"QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}")
        match_options.addWidget(self.similarity_bar)
        self.match_distance = QLabel("Similarity: ")
        self.match_distance.setStyleSheet("font-weight: 600;")
        match_options.addWidget(self.match_distance)
        match_layout.addLayout(match_options)

        # Match Image, with its toolbar floating over it
        self.match_image = MediaWidget()
        self.match_image.setMinimumHeight(300)
        self.match_image.setStyleSheet(f"background: {IMAGE_WELL};")
        match_layout.addWidget(self.match_image, 1)
        self.match_image_bar = ImageAdjustBar(self, self.match_image, 'match')

        # MetaData
        self.match_info = QTableWidget()
        self._set_table(self.match_info)
        match_layout.addWidget(self.match_info)
        image_layout.addLayout(match_layout, 1)
        # Add image block to layout
        layout.addLayout(image_layout, 1)

        # RANKED CANDIDATES ====================================================
        strip_header = QHBoxLayout()
        strip_header.setContentsMargins(20, 10, 20, 4)
        strip_header.setSpacing(12)
        strip_title = QLabel("Ranked candidates")
        strip_title.setStyleSheet("font-weight: 600;")
        strip_header.addWidget(strip_title)
        strip_header.addWidget(label("← → to browse", "muted"))
        self.match_counter = label("", "muted")
        strip_header.addWidget(self.match_counter)
        strip_header.addStretch()
        # Toggle match favorites button
        self.button_match_favorites = QPushButton("Show ♥")
        self.button_match_favorites.setCheckable(True)
        self.button_match_favorites.setChecked(False)
        self.button_match_favorites.setToolTip("Show the query's favorite candidates instead of its nearest neighbors")
        self.button_match_favorites.clicked.connect(self.toggle_match_favorites_button)
        strip_header.addWidget(self.button_match_favorites)
        layout.addLayout(strip_header)
        self.candidates = CandidateStrip()
        self.candidates.candidate_clicked.connect(self.change_match)
        strip_box = QHBoxLayout()
        strip_box.setContentsMargins(20, 0, 20, 0)
        strip_box.addWidget(self.candidates)
        layout.addLayout(strip_box)

        # DECISION BAR =========================================================
        bottom = QFrame()
        bottom.setObjectName("DecisionBar")
        bottom_layer = QGridLayout(bottom)
        bottom_layer.setContentsMargins(20, 12, 20, 12)
        hints = QHBoxLayout()
        hints.setSpacing(12)
        for keys, what in (("← →", "candidate"), ("↑ ↓", "query"), ("A D", "sequence"), ("L R V", "viewpoint")):
            hint = QHBoxLayout()
            hint.setSpacing(4)
            kbd = QLabel(keys)
            kbd.setObjectName("Kbd")
            kbd.setFixedHeight(22)
            hint.addWidget(kbd, 0, Qt.AlignmentFlag.AlignVCenter)
            hint.addWidget(label(what, "muted"))
            hints.addLayout(hint)
        hints.addStretch()
        self.button_unmatch = QPushButton("Unmatch (U)")
        self.button_unmatch.setMinimumHeight(44)
        self.button_unmatch.clicked.connect(self.unmatch)
        hints.addWidget(self.button_unmatch)
        bottom_layer.addLayout(hints, 0, 0)
        # Match: names a new individual when neither side has one
        self.button_match = QPushButton("Match (M)")
        self.button_match.clicked.connect(self.press_match_button)
        self.button_match.setCheckable(True)
        self.button_match.setChecked(False)
        self.button_match.setMinimumSize(220, 48)
        set_variant(self.button_match, "primary")
        bottom_layer.addWidget(self.button_match, 0, 1)
        bottom_layer.addWidget(QWidget(), 0, 2)
        # Match stays centered between equal side columns
        bottom_layer.setColumnStretch(0, 1)
        bottom_layer.setColumnStretch(2, 1)
        layout.addWidget(bottom)
        self.setLayout(layout)

        # remove focus from buttons to keep keyboard shortcuts working
        self.set_no_focus()
        self.project.changed.connect(self.drop_queries)
        # ======================================================================

    def set_no_focus(self):
        """Remove focus from all QPushButton children to keep keyboard shortcuts working."""
        for child in self.findChildren(QWidget):
            if isinstance(child, (QPushButton)):
                child.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def drop_queries(self):
        """
        Discard the query container when another project is opened

        Connected to project.changed in __init__. The container holds the previous
        project's rois and database, so a match made through it would write to
        that project. A new one is built the next time compare is entered.
        """
        self._teardown_query_container()
        self.QueryContainer = QueryContainer(self)

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

    def has_query(self):
        """Whether a query is loaded, so navigation and match actions have something to act on"""
        qc = getattr(self, "QueryContainer", None)
        return qc is not None and qc.n_queries > 0 and bool(qc.current_query_rois)

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

    def notify(self, prompt):
        """
        Show a result message in the open progress popup, replacing its text, so the
        user dismisses one popup. Without a progress popup, show a single alert.
        """
        box = self.alert_box
        if box is None:
            self.warn(prompt=prompt)
            return
        box.update_prompt(prompt)
        # stop the busy indicator
        box.set_max(1)
        box.set_value(1)
        box.finished.connect(lambda _result: self.close_progress())
        box.show()

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
        self._sync_mode()
        # thumbnails and candidates are looked up again, rois may have changed
        self._roi_thumbnails = None
        self._candidate_key = None
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
            logger.info("Clearing KNN cache")
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
        # stop receiving signals from the old container (QC/manual containers have none)
        for name in ("progress_update", "thread_signal"):
            sig = getattr(qc, name, None)
            if sig is None:
                continue
            try:
                sig.disconnect()
            except (TypeError, RuntimeError):
                pass
        if hasattr(qc, "stop_calculation"):
            qc.stop_calculation()
        # block until the worker thread really finishes
        thread = getattr(qc, "match_thread", None)  # adjust to your attribute name
        if thread is not None and thread.isRunning():
            thread.requestInterruption()
            thread.quit()
            if not thread.wait(3000):
                logger.warning("Query thread did not stop in time")
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
            logger.info("Using cached KNN results")
            # skip to finalize step
            QTimer.singleShot(100, self.QueryContainer.finalize)
        else:
            self.update_prompt("Matching embeddings...")
            self.alert_box.set_max(100)
            QTimer.singleShot(100, self.QueryContainer.calculate_neighbors)

    def check_matchthread_success(self, thread_success):
        if self._cancelled:
            self.close_progress()
            return
        if thread_success:
            self.close_progress()
            self.change_query(0)
        # on failure keep the progress popup open and show the result in it
        elif not self.QueryContainer.filter_matched:
            self.notify("No matches found within filter.")
        else:
            self.notify("No data to compare, all available data from same sequence/capture.")

    # --------------------------------------------------------------------------
    def compare_by_individual(self):
        """
        Enter QC mode, recalculate matches by individual IDs
        
        Does not require a cache
        """
        # must have inviduals to enter QC mode

        if not fetch_individual(self.mpDB).empty:
            self.compare_type = 'qc'
            self._sync_mode()
            self.button_match_favorites.setVisible(False)  # hide favorite toggle
            self._teardown_query_container()
            self.QueryContainer = QC_QueryContainer(self)
            self.filterbar.individual_visible(True)
            self.QueryContainer.load_data()
            filtered = self.QueryContainer.filter(filter_dict=self.filters, valid_stations=self.valid_stations)
            # no match thread, have to check success manually
            if filtered:
                self.change_query(0)
            else:
                self.notify("No data to compare within filter.")
        else:
            self.notify("No data to compare, no named individuals to analyze.")

    def compare_manual(self, selected_ids=None):
        """
        Enter manual comparison mode, recalculate matches manually
        
        Does not require a cache
        """
        self.compare_type = 'manual'
        self._sync_mode()
        self.button_match_favorites.setVisible(False)  # hide favorite toggle
        self.filterbar.individual_visible(False)
        self._teardown_query_container()
        self.QueryContainer = ManualQueryContainer(self, selected_ids=selected_ids)  # re-establish object
        emb_exist = self.QueryContainer.load_data()
        if emb_exist and self.QueryContainer.filter(filter_dict=self.filters, valid_stations=self.valid_stations):
            self.QueryContainer.calculate_neighbors()
            self.change_query(0)
        else:
            self.notify("No data to compare within filter.")

    def change_mode(self, index):
        """Switch between ranked candidates and QC by individual from the Mode dropdown"""
        mode = {v: k for k, v in self.MODES.items()}.get(index)
        if mode == self.compare_type:
            return
        if mode == 'default':
            self.initialize()
        elif mode == 'qc':
            self.compare_by_individual()
        else:
            # manual compares the rois ticked in the media view, it can't be entered from here
            self._sync_mode()

    def _sync_mode(self):
        """Show the current comparison type in the Mode dropdown"""
        select = getattr(self, "mode_select", None)
        if select is None:
            return
        select.blockSignals(True)
        select.setCurrentIndex(self.MODES.get(self.compare_type, 0))
        select.blockSignals(False)

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
            # keep the rois selected in the media view
            self.compare_manual(selected_ids=self.QueryContainer.selected_ids)
        else:
            self.initialize()

    # ==========================================================================
    # MATCHING PROCESS
    # ==========================================================================
    def press_match_button(self):
        """Handle the press event for the Match button."""
        if not self.has_query():
            return
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

        name = (self.QueryContainer.get_info(self.QueryContainer.current_match_rid, 'name')
                or self.QueryContainer.get_info(self.QueryContainer.current_query_rid, 'name'))
        name = name if isinstance(name, str) and name else None
        if self.button_match.isChecked():
            # already the same individual, pressing again unmatches
            self.button_match.setText(f"Matched to {name}" if name else "Matched")
            self.button_match.setStyleSheet(self.MATCHED_STYLE)
        else:
            self.button_match.setText(f"Match to {name} (M)" if name else "Match as new individual (M)")
            self.button_match.setStyleSheet("")
        self.button_unmatch.setEnabled(self.button_match.isChecked())

    def confirm_match(self):
        """
        Match button was clicked, merge query sequence and current match.
        Optimized to only update affected data.
        """
        if not self.has_query():
            return
        query_sequence_id = self.QueryContainer.get_query_sequence_id()
        match_sequence_id = self.QueryContainer.get_match_sequence_id()
        
        # Both individual_ids are None
        if self.QueryContainer.both_unnamed():
            # make new individual
            dialog = IndividualFillPopup(self)
            if not dialog.exec():
                return  # User cancelled - don't proceed
            individual_id = self.mpDB.add_individual(dialog.get_name(), dialog.get_sex())
            del dialog
            if individual_id is None:
                self.warn(prompt="Could not create the new individual, see the log for details.")
                return
            # update query and match
            self.QueryContainer.new_iid(individual_id)
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
        # only an existing match can be unmatched (U key bypasses the button's check)
        if not self.has_query() or not self.QueryContainer.is_existing_match():
            return
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
        qc = getattr(self, "QueryContainer", None)
        if qc is None or qc.n_queries == 0:
            return
        self.QueryContainer.set_query(n)
        # keep showing favorites for the new query if the toggle is on
        if self.compare_type == 'default' and self.button_match_favorites.isChecked():
            self.QueryContainer.set_match_favorites(True)
        # update text
        self.query_selector.set_total(self.QueryContainer.n_queries)
        self.query_selector.set_current_number(self.QueryContainer.current_query)
        n_queries = self.QueryContainer.n_queries
        if isinstance(n_queries, int):
            self.query_progress.setRange(0, max(1, n_queries))
            self.query_progress.setValue(self.QueryContainer.current_query + 1)

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
        if not self.has_query():
            return
        self.QueryContainer.set_within_query_sequence(n)
        self.query_image_bar.reset()
        self.sequence_selector.set_current_number(self.QueryContainer.current_query_sn)
        self.load_query()
        # in QC / manual the match moves on if it was the new query roi
        if self.compare_type != 'default':
            self.change_match(self.QueryContainer.current_match)

    def change_match(self, n):
        """Load nth match within the current match queue"""
        if not self.has_query():
            return
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
        self.query_name.setText(self.display_path(self.QueryContainer.current_query_rid, metadata))
        self.query_name.setToolTip(str(metadata.get('Filepath', '')))
        name = metadata.get('Name')
        self.query_status.setText(name if name else "Unidentified")
        set_role(self.query_status, "pill-ok" if name else "pill-warn")
        self.toggle_match_button()
        self.toggle_query_favorite()

    def load_match(self):
        """
        Load Image and Metadata for Current Match ROI
        """
        distance = self.QueryContainer.current_distance()
        # missing embedding (None/NaN) or no match (inf) has no similarity to show
        if distance is None or not math.isfinite(distance):
            self.match_distance.setText("Similarity: N/A")
            self.similarity_bar.setValue(0)
        else:
            self.match_distance.setText(f"Similarity: {1 - distance:.2f}")
            self.similarity_bar.setValue(max(0, min(100, round(100 * (1 - distance)))))

        self.match_image.load(self.QueryContainer.get_info(self.QueryContainer.current_match_rid, "filepath"),
                              frame=self.QueryContainer.get_info(self.QueryContainer.current_match_rid, "frame"),
                              bbox=self.QueryContainer.get_info(self.QueryContainer.current_match_rid, "bbox"), crop=True)
        metadata = self.QueryContainer.get_info(self.QueryContainer.current_match_rid, "metadata")
        self.format_metadata(self.match_info, metadata)
        name = metadata.get('Name')
        self.match_name.setText(name if name else "Unnamed")
        set_role(self.match_name, "pill-ok" if name else "pill-muted")
        self.match_selector.set_total(len(self.QueryContainer.current_match_rois))
        self.match_selector.set_current_number(self.QueryContainer.current_match)
        self.update_candidates()
        self.toggle_match_button()
        self.toggle_match_favorite()

    def toggle_viewpoint(self, selected_viewpoint):
        """
        Flip between viewpoints in paired images within a sequence
        """
        self.current_viewpoint = selected_viewpoint
        if not self.has_query():
            return
        viewpoints_available = self.QueryContainer.toggle_viewpoint(self.current_viewpoint)
        if not viewpoints_available:
            self.warn(prompt="No images available for this viewpoint. Showing all available images.")
            self.button_viewpoint.set_index(1)

        # update gui counts
        self.sequence_selector.set_total(len(self.QueryContainer.current_query_rois))
        self.sequence_selector.set_current_number(self.QueryContainer.current_query_sn)
        self.match_selector.set_total(len(self.QueryContainer.current_match_rois))
        self.match_selector.set_current_number(self.QueryContainer.current_match)
        self.match_counter.setText(f"{self.QueryContainer.current_match+1}/{len(self.QueryContainer.current_match_rois)}")

        # load images and data
        self.load_query()
        self.load_match()

    def display_path(self, rid, metadata):
        """
        The roi's file as shown above its image: the path within its station folder

        relative_path is relative to the imported folder, which often starts with
        the station's folder; that is dropped since the station is in the metadata.
        """
        relative = self.QueryContainer.get_info(rid, "relative_path")
        if not isinstance(relative, str) or not relative:
            return os.path.basename(str(metadata.get('Filepath', '')))
        parts = Path(relative.replace("\\", "/")).parts
        if len(parts) > 1 and parts[0] == str(metadata.get('Station', '')):
            parts = parts[1:]
        return "/".join(parts)

    def update_candidates(self):
        """Rebuild the candidate strip when the match list changes, then mark the shown candidate"""
        rois = list(self.QueryContainer.current_match_rois)
        key = (self.compare_type, self.QueryContainer.current_query_rid, tuple(rois))
        if key != getattr(self, "_candidate_key", None):
            self._candidate_key = key
            if not hasattr(self, "_roi_thumbnails") or self._roi_thumbnails is None:
                thumbnails = fetch_roi_thumbnails(self.mpDB)
                self._roi_thumbnails = dict(zip(thumbnails['id'], thumbnails['thumbnail_path']))
            ranked = {}
            match_object = getattr(self.QueryContainer, "current_match_object", None)
            if self.compare_type == 'default' and match_object is not None:
                ranked = dict(match_object.get_ranked_matches())
            candidates = []
            for rid in rois:
                path = self._roi_thumbnails.get(rid)
                path = str(self.cfg.THUMBNAIL_DIR / path) if path else None
                name = self.QueryContainer.get_info(rid, 'name')
                distance = ranked.get(rid)
                similarity = f"{1 - distance:.2f}" if distance is not None and math.isfinite(distance) else ""
                candidates.append((path, name if isinstance(name, str) else None, similarity))
            self.candidates.set_candidates(candidates)
        self.candidates.set_current(self.QueryContainer.current_match)

    # METADATA TABLE
    def _set_table(self, table):
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setMouseTracking(False)
        table.setItemDelegate(NoHoverDelegate())
        # remove headers, grid, and scrollbars
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setVisible(False)
        table.setShowGrid(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setRowCount(6)
        table.setColumnCount(4) 
        # label columns are fixed, the two value columns (1 and 3) stretch to share the rest equally
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.setMaximumHeight(200)
        table.setMinimumHeight(170)

        table.setColumnWidth(0, 120)
        table.setColumnWidth(2, 120)
        # stretch rows evenly to fill the table height
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet("""
            QTableWidget {
                border: 1px solid palette(mid);
                border-radius: 10px;
                font-size: 13px;
                background: palette(base);
            }
            QTableWidget::item {
                padding: 2px 6px;
            }
        """)

    def changeEvent(self, event):
        """
        Recolor the metadata tables when the palette changes, eg. a theme picked in the config

        Qt override, called on the widget for any state change. format_metadata copies
        the palette's colors into each cell, so without this the tables keep the old
        theme's colors until the next query or match loads.
        """
        if event.type() == QEvent.Type.PaletteChange:
            for table, info_dict in getattr(self, "_shown_metadata", {}).items():
                self.format_metadata(table, info_dict)
        super().changeEvent(event)

    def format_metadata(self, table, info_dict):
        # kept to redraw in the new colors if the theme changes, see changeEvent
        if not hasattr(self, "_shown_metadata"):
            self._shown_metadata = {}
        self._shown_metadata[table] = info_dict
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
            ("Viewpoint:",   info_dict['Viewpoint'],     "Timestamp:",  info_dict['Timestamp']),
            ("Sex:",         info_dict['Sex'],           "Region:",     info_dict['Region']),
            ("Sequence ID:", info_dict['Sequence ID'],   "Survey:",     info_dict['Survey']),
            ("External ID:", info_dict['External ID'],   "Station:",    info_dict['Station']),
            ("Comment:",     info_dict['Comment'],       "Camera:",     info_dict['Camera']),
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
        if not self.has_query():
            return
        data = self.QueryContainer.get_info(rid).copy()
        data["id"] = rid
        data = data.to_frame().T
        dialog = MediaEditPopup(self, data, data_type=1)
        accepted = dialog.exec()
        if accepted:
            self.edit_stack = dialog.get_edit_stack()
            self.save_changes()
        roi_updated = dialog.roi_updated
        # free the popup (and its media player), it is parented to this view
        dialog.deleteLater()
        del dialog
        # rois deleted or redrawn in the popup (even if then cancelled): rebuild matches
        if roi_updated:
            self.filter_neighbors()
            return
        if accepted:
            # reload the shown rows, keeping the active filter
            self.QueryContainer.refresh_data()
            self.load_query()
            self.load_match()

    def save_changes(self):
        """Commit all EditObjects in self.edit_stack to the database, oldest first"""
        failed = save_edits(self.mpDB, self.edit_stack,
                            lambda rid: self.QueryContainer.get_info(rid, "individual_id"))
        # keep unsaved edits so they are not silently lost, like the media view
        self.edit_stack = failed
        if failed:
            self.warn(f"{len(failed)} change(s) could not be saved, see the log for details.")

    def open_image(self, rid):
        """
        Open Image in OS Default Image Viewer

        Currently only supports one image at a time
        """
        if not self.has_query():
            return
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
        if not self.has_query():
            return
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
        if not self.has_query():
            return
        if self.QueryContainer.get_info(rid, "favorite"):
            # set favorite to false
            self.favorite(rid, 0)
        else:
            # set favorite to true
            self.favorite(rid, 1)

    def favorite(self, rid, value):
        """Set favorite status for given rid"""
        set_favorite(self.mpDB, rid, value)
        # reload the shown rows, keeping the active filter
        self.QueryContainer.refresh_data()
        # rebuild the favorites list if it is showing
        if self.compare_type == 'default' and self.button_match_favorites.isChecked():
            self.QueryContainer.set_match_favorites(True)
            self.change_match(0)
            self.load_query()
            return
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
