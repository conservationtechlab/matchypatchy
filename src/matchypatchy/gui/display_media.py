"""
GUI Window for viewing images
"""
import logging
from pathlib import Path
import pandas as pd
from PyQt6.QtWidgets import (QHeaderView, QPushButton, QTableView, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QDialog, QFrame, QLineEdit, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from matchypatchy.database.media import (IMAGE_EXT, fetch_individual, delete_media, delete_rois, save_edits,
                                         media_without_rois)
from matchypatchy.database.location import camera_names
from matchypatchy.database.thumbnails import THUMBNAIL_SIZE
from matchypatchy.gui.media_table import MediaTable
from matchypatchy.gui.dialogs.popup_alert import AlertPopup
from matchypatchy.gui.dialogs.popup_media_edit import MediaEditPopup
from matchypatchy.gui.widgets.gui_assets import VerticalSeparator, ComboBoxDelegate, SegmentedControl
from matchypatchy.gui.widgets.styles import ACCENT, label, set_variant, icon
from matchypatchy.gui.widgets.widget_filterbar import FilterBar
from matchypatchy.threads.table_thread import FetchTableThread
from matchypatchy.threads.model_download_thread import load_model
from matchypatchy.threads.match_object import viewpoint_value
from matchypatchy.project import UsesProject


logger = logging.getLogger(__name__)


class DisplayMedia(UsesProject, QWidget):
    """GUI class for displaying and managing media content."""

    # Save turns green while there are unsaved edits
    SAVE_STYLE = f""" QPushButton {{ background-color: {ACCENT}; color: white; border-color: {ACCENT}; font-weight: 600; }}"""
    # columns that share the width left over by the others, by column name
    STRETCH_COLUMNS = ("filepath", "comment")
    # widths of the columns that don't use the default, by column name
    COLUMN_WIDTHS = {"select": 50,
                     "thumbnail_path": THUMBNAIL_SIZE + 10,
                     "filepath": 50,  # stretches to fill the rest
                     "ext": 80,
                     "timestamp": 180,
                     "individual_id": 110,
                     "viewpoint": 100,
                     "favorite": 72,
                     "sex": 80,
                     "camera_id": 90}
    edit_stack_signal = pyqtSignal(list)  # Signal to send edit stack to main GUI

    def __init__(self, parent, data_type=1):
        super().__init__()
        self.parent = parent
        self.project = parent.project
        self.VIEWPOINTS = load_model('VIEWPOINTS')
        # 0 for Media, 1 for ROI
        self.data_type = data_type
        self.valid_stations = []
        self.selected_rows = []
        # whether Missing/Unspecified ROI was applied when a # of Rois was clicked, for Back
        self._back_to_no_roi = False
        # table loads, a newer load supersedes older ones still running
        self._load_id = 0
        self._loaders = []

        # data and edit stack
        self._data_raw = pd.DataFrame()
        self._data_filtered = pd.DataFrame()
        self.edit_stack = []
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # TOOLBAR --------------------------------------------------------------
        toolbar = QFrame()
        toolbar.setObjectName("TopBar")
        first_layer = QHBoxLayout(toolbar)
        first_layer.setContentsMargins(20, 12, 20, 12)
        first_layer.setSpacing(10)
        title = QLabel("Media")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        first_layer.addWidget(title)
        # Save
        self.button_save = QPushButton("Save")
        self.button_save.clicked.connect(self.save)
        first_layer.addWidget(self.button_save)
        # Undo
        self.button_undo = QPushButton("Undo")
        self.button_undo.clicked.connect(self.undo)
        self.button_undo.setEnabled(False)
        first_layer.addWidget(self.button_undo)
        self.unsaved_label = QLabel("")
        self.unsaved_label.setObjectName("UnsavedNotice")
        self.unsaved_label.setVisible(False)
        first_layer.addWidget(self.unsaved_label)
        first_layer.addWidget(VerticalSeparator())

        # Show Type, with how many of each there are
        self.show_type = SegmentedControl(["Full Images", "ROIs"])
        self.show_type.setCurrentIndex(self.data_type)
        self.show_type.currentIndexChanged.connect(self.change_type)
        first_layer.addWidget(self.show_type)
        first_layer.addStretch()

        # Search filepath, individual and comment as you type
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search filepath, individual, comment…")
        self.search.setClearButtonEnabled(True)
        self.search.addAction(icon("search", "#8A8F8B"), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setMinimumWidth(280)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self.refresh_table)
        self.search.textChanged.connect(lambda _text: self._search_timer.start())
        first_layer.addWidget(self.search)
        layout.addWidget(toolbar)

        # FILTERS: apply as they change ----------------------------------------
        second_layer = QHBoxLayout()
        second_layer.setContentsMargins(20, 8, 20, 8)
        self.filterbar = FilterBar(self, 150)
        second_layer.addWidget(self.filterbar, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.filters = self.filterbar.get_filters()  # get initial filters
        self._connect_filter_changes()
        button_clear_filter = QPushButton("Clear Filters")
        button_clear_filter.clicked.connect(self.clear_filters)
        second_layer.addWidget(button_clear_filter, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # leaves the rois of a clicked # of Rois, only shown there
        self.button_back = QPushButton("Back to All Media")
        self.button_back.clicked.connect(self.back_to_media)
        self.button_back.setVisible(False)
        second_layer.addWidget(self.button_back, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        second_layer.addStretch()
        layout.addLayout(second_layer)

        # SELECTION ACTIONS: only shown while rows are ticked -------------------
        self.selection_bar = QFrame()
        self.selection_bar.setObjectName("SelectionBar")
        selection_layout = QHBoxLayout(self.selection_bar)
        selection_layout.setContentsMargins(20, 6, 20, 6)
        selection_layout.setSpacing(8)
        self.selection_label = QLabel("")
        selection_layout.addWidget(self.selection_label)
        selection_layout.addSpacing(8)
        # Edit Rows
        self.button_edit = QPushButton("Edit Rows…")
        self.button_edit.clicked.connect(self.edit_row_multiple)
        self.button_edit.setEnabled(False)
        # Compare the ticked rois against each other
        self.button_compare_selected = QPushButton("Compare Selected")
        self.button_compare_selected.clicked.connect(self.compare)
        # Duplicate
        self.button_duplicate = QPushButton("Duplicate Rows")
        self.button_duplicate.clicked.connect(self.duplicate)
        self.button_duplicate.setEnabled(False)
        for button in (self.button_edit, self.button_compare_selected, self.button_duplicate):
            set_variant(button, "selbar")
            selection_layout.addWidget(button)
        selection_layout.addStretch()
        # Delete
        self.button_delete = QPushButton("Delete Rows")
        self.button_delete.clicked.connect(self.delete)
        self.button_delete.setEnabled(False)
        set_variant(self.button_delete, "danger")
        selection_layout.addWidget(self.button_delete)
        self.selection_bar.setVisible(False)

        # display rois or media
        self._data_raw = pd.DataFrame()
        self.view = QTableView()
        self.media_table = MediaTable(self, self._get_headers())
        self.view.setModel(self.media_table)
        self.view.setSortingEnabled(True)
        self.view.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.view.horizontalHeader().setSortIndicatorShown(True)
        # clicking a header cycles ascending, descending, then back to unsorted
        self.view.horizontalHeader().setSortIndicatorClearable(True)
        self.view.horizontalHeader().setSectionsClickable(True)
        self.view.verticalHeader().setDefaultSectionSize(THUMBNAIL_SIZE + 10)  # row size = thumbnail with
        self.view.horizontalHeader().setDefaultSectionSize(100)
        self.view.verticalHeader().sectionDoubleClicked.connect(self.edit_row)
        self.view.setShowGrid(False)
        # one line per cell, long paths are shortened in the middle (hover shows them whole)
        self.view.setWordWrap(False)
        self.view.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.view.setAlternatingRowColors(True)
        self.view.doubleClicked.connect(self.edit_thumbnail)
        self.view.clicked.connect(self.show_media_rois)
        self._set_column_widths()

        # Connect the selection changed signal from the media table to a handler
        self.media_table.user_edit.connect(self.add_edit_to_stack)
        table_box = QVBoxLayout()
        table_box.setContentsMargins(20, 0, 20, 0)
        table_box.setSpacing(0)
        table_box.addWidget(self.selection_bar)
        table_box.addWidget(self.view, stretch=1)
        layout.addLayout(table_box, stretch=1)

        # Count and Select All at Bottom
        bottom = QHBoxLayout()
        bottom.setContentsMargins(20, 6, 20, 10)
        # Select All
        self.button_select = QPushButton("Select All")
        self.button_select.setCheckable(True)
        self.button_select.pressed.connect(self.set_button_select)
        bottom.addWidget(self.button_select)
        self.count_label = label("", "muted")
        bottom.addWidget(self.count_label)
        bottom.addStretch()
        layout.addLayout(bottom)

        self.setLayout(layout)
        self.project.changed.connect(self.drop_edits)

    def drop_edits(self):
        """
        Discard unsaved edits when another project is opened

        Connected to project.changed in __init__. The edits refer to rois of the
        previous project, so saving them would write to the wrong rows.
        """
        self.edit_stack = []
        self.check_undo_button()

    # ==========================================================================
    # NAVIGATION
    # ==========================================================================

    def confirm_leave(self):
        """
        Whether the user is fine leaving the view, asking if there are unsaved edits

        Called by the main window before the sidebar switches to another page.
        """
        if len(self.edit_stack) == 0:
            return True
        dialog = AlertPopup(self, prompt="There are unsaved changes. Are you sure you want to leave this page?")
        leave = dialog.exec() == QDialog.DialogCode.Accepted
        del dialog
        return leave

    def home(self):
        """Return to Base View"""
        if len(self.edit_stack) > 0:
            dialog = AlertPopup(self, prompt="There are unsaved changes. Are you sure you want to return home?")
            if dialog.exec():
                self.parent._set_base_view()
                del dialog
            else:
                return
        else:
            self.parent._set_base_view()

    def compare(self):
        """Go to Compare View"""
        if len(self.edit_stack) > 0:
            dialog = AlertPopup(self, prompt="There are unsaved changes. Please save before matching.")
            if dialog.exec():
                del dialog
            return
        else:
            rois = None
            if self.data_type == 1:
                # rows ticked in the Select column, not the highlighted rows
                rois = self.media_table.selectedIds()
                if len(rois) > 1:
                    dialog = AlertPopup(self, prompt=f"Would you like to compare the {len(rois)} selected ROIs?")
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        print("Comparing rois:", rois)
                        self.parent._set_manual_view(selected_ids=rois)
                    del dialog
                else:
                    print("Not enough ROIs selected for comparison. Defaulting to full compare view.")
                    self.parent._set_compare_view()
            # if data type is media go to default compare view
            else:
                self.parent._set_compare_view()
        return

    # ALERT POPUP MANAGER ------------------------------------------------------
    def show_alert(self, prompt):
        """Progress Popup for Match Thread"""
        if not hasattr(self, 'alert_box') or self.alert_box is None:
            self.alert_box = AlertPopup(self, prompt, progressbar=True, cancel_only=True)
        self.alert_box.update_prompt(prompt)
        self.alert_box.show()

    def update_prompt(self, prompt):
        """Update the prompt in the progress popup"""
        if hasattr(self, 'alert_box') and self.alert_box is not None:
            self.alert_box.update_prompt(prompt)

    def update_progress(self, progress):
        """Update the progress bar in the progress popup"""
        # set_value, not set_counter, which closes the popup once the bar is full
        # while the table is still being built
        if hasattr(self, 'alert_box') and self.alert_box is not None:
            self.alert_box.set_value(progress)

    def set_progress_max(self, max_value):
        """Set the maximum value for the progress bar, 0 shows a busy bar"""
        # connects to FetchTableThread's progress_max signal
        if hasattr(self, 'alert_box') and self.alert_box is not None:
            self.alert_box.set_min(0)
            self.alert_box.set_max(max_value)
            self.alert_box.reset_counter()
            self.alert_box.progress_bar.setFormat("%v/%m")   # shows count, e.g. 42/100

    def close_alert(self):
        """Close the alert popup"""
        if hasattr(self, 'alert_box') and self.alert_box is not None:
            self.alert_box.close()
            self.alert_box = None

    # =========================================================================
    # FILTERS
    # =========================================================================
    def refresh_filters(self, prefilter=None):
        """
        Update Dropdown Lists, Fill Filter Dict
        Allows refresh of dropdowns if re-entry into media view after updating database
        """
        # wipe previous selections
        self.filterbar.refresh_filters(prefilter=prefilter)
        # individual, unidentified and clicked media filters only apply to rois
        if prefilter and ('individual_id' in prefilter or prefilter.get('unidentified_only')
                          or prefilter.get('media_ids')):
            if self.data_type != 1:
                self.data_type = 1
                # change_type would load the table again
                self.show_type.blockSignals(True)
                self.show_type.setCurrentIndex(self.data_type)
                self.show_type.blockSignals(False)
        # get current filters
        self.filters = self.filterbar.get_filters()
        self.valid_stations = self.filterbar.get_valid_stations()
        self.toggle_filterbar_datatype()

    def _connect_filter_changes(self):
        """
        Refilter when the user changes a filter, so there is no Apply button

        Uses activated and clicked, which only fire for the user's own changes,
        not when refresh_filters resets the filters on entering the view.
        """
        bar = self.filterbar
        for combo in (bar.region_select, bar.survey_select, bar.station_select,
                      bar.viewpoint_select, bar.individual_select):
            # after the filterbar's own slot has narrowed the dependent lists
            combo.activated.connect(lambda _i: QTimer.singleShot(0, self.filter_table))
        for checkbox in (bar.unidentified, bar.favorites, bar.no_roi, bar.media_only):
            checkbox.clicked.connect(lambda _c: QTimer.singleShot(0, self.filter_table))

    def filter_table(self):
        """
        Filter the media table based on the selected options
        Run after any setting is changed and filter button is pressed
        """
        self.filters = self.filterbar.get_filters()
        self.valid_stations = self.filterbar.get_valid_stations()
        self.toggle_filterbar_datatype()
        self.refresh_table()

    def toggle_filterbar_datatype(self):
        """Toggle visibility of filter bar elements based on data type"""
        self.filterbar.individual_visible(self.data_type == 1)
        self.filterbar.unidentified_visible(self.data_type == 1)
        self.filterbar.favorites_visible(self.data_type == 1)
        self.filterbar.viewpoint_visible(self.data_type == 1)
        self.filterbar.no_roi_visible(self.data_type == 0)
        self.filterbar.media_only_visible(self.data_type == 1)
        self.button_back.setVisible(self.data_type == 1 and self.filters['media_ids'] is not False)

    def clear_filters(self):
        """Clear all filters and refresh the table"""
        self.refresh_filters()
        self.refresh_table()

    # =========================================================================
    # MEDIA TABLE HANDLERS
    # =========================================================================

    # CHANGE VIEW TYPE (FULL IMAGE / ROI)
    def _drop_edits_to_change_view(self):
        """
        Ask before discarding unsaved edits for a change of view, False if the user declines

        Called by change_type and show_media_rois, which both reload the table as the other
        data type, so the edit stack's rows no longer apply. Kept separate so both ask the
        same question and clear the undo button the same way.
        """
        if len(self.edit_stack) > 0:
            dialog = AlertPopup(self, prompt="Are you sure you want to change view? There are unsaved changes that will be lost.")
            cont = dialog.exec()
            del dialog
            if cont == QDialog.DialogCode.Rejected:
                return False
        # Clear unsaved edits since user confirmed they want to change view
        self.edit_stack.clear()
        self.check_undo_button()
        return True

    def change_type(self):
        """Change between full image and ROI view"""
        if not self._drop_edits_to_change_view():
            self.show_type.blockSignals(True)
            self.show_type.setCurrentIndex(self.data_type)
            self.show_type.blockSignals(False)
            return

        # change type to selected
        self.data_type = self.show_type.currentIndex()
        # reload table
        self.toggle_filterbar_datatype()
        self.load_table()

    def show_media_rois(self, index):
        """
        Show the rois of the media whose # of Rois cell was clicked

        Connected to the view's clicked signal; other cells, the roi view and media
        without rois are ignored. The other filters are cleared so every roi shows.
        """
        if self.data_type != 0 or self.media_table._columns[index.column()] != "roi_count":
            return
        row = self.media_table._data_filtered.iloc[index.row()]
        if pd.isna(row["roi_count"]) or int(row["roi_count"]) == 0:
            return
        if not self._drop_edits_to_change_view():
            return
        self._back_to_no_roi = self.filters['no_roi_mids'] is not False
        # switches the view to rois
        self.refresh_filters(prefilter={'media_ids': [int(row["id"])]})
        self.load_table()

    def back_to_media(self):
        """
        Leave a clicked media's rois for all media

        Missing/Unspecified ROI is put back on if it was applied when the count was
        clicked, its media looked up again since rois may have been drawn; the other
        filters stay cleared
        """
        if not self._drop_edits_to_change_view():
            return
        self.data_type = 0
        self.show_type.blockSignals(True)
        self.show_type.setCurrentIndex(self.data_type)
        self.show_type.blockSignals(False)
        self.refresh_filters(prefilter={'no_roi_mids': True} if self._back_to_no_roi else None)
        self.load_table()

    # 1. RUN ON ENTRY
    def load_table(self):
        """Load media/roi data into table based on current data_type"""
        # check if there are rois first
        self.show_alert("Loading media...")
        # nothing measurable until the loader starts generating thumbnails
        self.set_progress_max(0)
        roi_n = self.mpDB.count('roi')
        media_n = self.mpDB.count('media')
        self.update_type_counts()

        if media_n == 0:
            self.close_alert()
            # no media at all
           # self.media_table.clear_and_load_contents(self.data_type)
            dialog = AlertPopup(self, prompt="No images found! Please import media.")
            if dialog.exec():
                self.home()
            del dialog
            return False
        else:
            # kept above the loader's stage text so it is not overwritten
            note = ""
            if self.data_type == 1 and roi_n == 0:
                # no rois, default to full images
                self.data_type = 0
                note = "No rois found, defaulting to full images.\n"
                self.update_prompt(note)

                self.show_type.blockSignals(True)
                self.show_type.setCurrentIndex(self.data_type)
                self.show_type.blockSignals(False)

            # load table with current data type
            self.individual_list = fetch_individual(self.mpDB)
            # a previous load still running is for the old view type or filters
            self._stop_loader()
            self._load_id += 1
            load_id = self._load_id
            self.dataloader = FetchTableThread(self)
            # keep a reference until the thread finishes so it is not garbage collected
            self._loaders.append(self.dataloader)
            self.dataloader.finished.connect(lambda loader=self.dataloader: self._forget_loader(loader))
            self.dataloader.loaded_data.connect(lambda data, load_id=load_id: self.handle_data_loaded(data, load_id))
            self.dataloader.progress_max.connect(lambda n_missing: self.set_progress_max(n_missing))
            self.dataloader.progress_update.connect(lambda progress: self.update_progress(progress))
            self.dataloader.progress_prompt.connect(lambda prompt, note=note: self.update_prompt(note + prompt))
            # Connect the progress popup's rejected signal to stop the query container's calculation
            if hasattr(self, 'alert_box') and self.alert_box:
                self.alert_box.rejected.connect(self.dataloader.requestInterruption)
            # Close the progress dialog when done
            self.dataloader.done.connect(lambda load_id=load_id: self._loader_done(load_id))
            self.dataloader.start()
            return True

    def _stop_loader(self):
        """Interrupt and disconnect the running FetchTableThread, if any"""
        loader = getattr(self, 'dataloader', None)
        if loader is None or not loader.isRunning():
            return
        loader.requestInterruption()
        for signal in (loader.loaded_data, loader.progress_max, loader.progress_update,
                       loader.progress_prompt, loader.done):
            try:
                signal.disconnect()
            except TypeError:
                pass  # nothing connected

    def _forget_loader(self, loader):
        """Drop the reference to a finished FetchTableThread"""
        if loader in self._loaders:
            self._loaders.remove(loader)

    def _loader_done(self, load_id):
        """Close the progress popup when the current load finishes"""
        if load_id == self._load_id:
            self.close_alert()

    def handle_data_loaded(self, data=None, load_id=None):
        """Handle data loaded from the FetchTableThread"""
        # ignore results from a load that was superseded, eg. by changing view type,
        # they do not match the current headers
        if load_id is not None and load_id != self._load_id:
            return
        self._data_raw = data
        self.apply_edits()  # Apply any pending edits to the raw data before filtering
        self.filter_data()  # Apply filters to the raw data to get the filtered data
        headers = self._get_headers()
        # widths set by hand are kept until the view type swaps the columns
        columns_changed = self.media_table._columns != [h[0] for h in headers.values()]
        self.media_table.receiveData(self._data_filtered, headers=headers) # Send the filtered data to the media table for display
        # reloaded rows come back unticked
        self.button_select.setChecked(False)
        self._apply_sort()
        if columns_changed:
            self._set_column_widths()
        self._set_delegates()
        self.update_count_label()
        self.update_edd_buttons()

    def refresh_table(self, reload=False):
        """Refresh the table by reapplying edits and filters"""
        if reload:
            # rois may have been added or removed, so the No ROI list is out of date
            # (keeps self.filters otherwise as last applied, not the unapplied filterbar choices)
            if self.filters['no_roi_mids'] is not False:
                self.filters['no_roi_mids'] = media_without_rois(self.mpDB)
            self.load_table()
        else:
            # keep ticked rows by id, their positions change when re-filtered and sorted
            selected_ids = self.media_table.selectedIds()
            self.apply_edits()
            self.filter_data()
            self.media_table.receiveData(self._data_filtered, selected_ids=selected_ids)
            self._apply_sort()
            self.update_count_label()
            self.update_edd_buttons()

    def apply_edits(self):
        """Apply any user edits from the filtered data back to the raw data before filtering"""
        # Start with a fresh copy of the raw data for filtering and applying edits
        self._data_filtered = self._data_raw.copy()
        # If there are no edits, skip processing
        if len(self.edit_stack) < 1:
            return

        for edit in self.edit_stack:
            print("Processing edit:", edit)
            # skip edits for wrong dataview
            if not edit.reference in self._data_filtered.columns:
                continue

            # get the correct id based on the data type
            if self.data_type == 1:
        #        print("Applying edit for RID:", edit.rid)
                self._data_filtered.loc[self._data_filtered["id"] == edit.rid, edit.reference] = edit.new_value
         #       print(self._data_filtered[self._data_filtered["id"] == edit.rid])
            else:
                self._data_filtered.loc[self._data_filtered["id"] == edit.mid, edit.reference] = edit.new_value
            
    def filter_data(self):
        """Filter the data based on the provided filters"""
        # if no media, skip
        if self._data_filtered.empty:
            return
        # self.valid_cameras =  # select all cameras for now
        self.valid_cameras = dict(camera_names(self.mpDB))
        # Location Filter (depends on prefilterd stations from MediaDisplay)
        if self.valid_stations:
            self._data_filtered = self._data_filtered[self._data_filtered['station_id'].isin(list(self.valid_stations.keys()))]
            # Single station Filter
            if self.filters['active_station'][0] > 0:
                self._data_filtered = self._data_filtered[self._data_filtered['station_id'] == self.filters['active_station'][0]]
            self._data_filtered['station'] = self._data_filtered['station_id'].map(self.valid_stations)
        else:
            # no valid stations, empty dataframe
            self._data_filtered.drop(self._data_filtered.index, inplace=True)

        # ROI-only filters
        if self.data_type == 1:
            # Viewpoint Filter
            if self.filters['active_viewpoint'][0] > 0:
                # filter by the stored value labelled with the selected side
                value = viewpoint_value(self.filters['active_viewpoint'][1])
                self._data_filtered = self._data_filtered[self._data_filtered['viewpoint'] == value]
            elif self.filters['active_viewpoint'][0] is None:
                self._data_filtered = self._data_filtered[self._data_filtered['viewpoint'].isna()]
            # Individual Filter
            if self.filters['active_individual'][0] > 0:
                self._data_filtered = self._data_filtered[self._data_filtered['individual_id'] == self.filters['active_individual'][0]]
            elif self.filters['active_individual'][0] is None:
                self._data_filtered = self._data_filtered[self._data_filtered['individual_id'].isna()]
            # Unidentified Filter
            if self.filters['unidentified_only']:
                self._data_filtered = self._data_filtered[self._data_filtered['individual_id'].isna()]
            # Favorites Filter
            if self.filters['favorites_only']:
                self._data_filtered = self._data_filtered[self._data_filtered['favorite'] == 1]
            # Clicked Media Filter
            if self.filters['media_ids'] is not False:
                self._data_filtered = self._data_filtered[self._data_filtered['media_id'].isin(self.filters['media_ids'])]
        else:
            if self.filters['no_roi_mids'] is not False:
                self._data_filtered = self._data_filtered[self._data_filtered['id'].isin(self.filters['no_roi_mids'])]

        # Search box: filepath, comment or individual name contains the text
        text = self.search.text().strip().lower() if hasattr(self, 'search') else ""
        if text:
            match = pd.Series(False, index=self._data_filtered.index)
            for column in ("filepath", "comment", "name"):
                if column in self._data_filtered.columns:
                    match |= self._data_filtered[column].astype(str).str.lower().str.contains(text, regex=False)
            self._data_filtered = self._data_filtered[match]

        # no valid stations, empty dataframe
        self._data_filtered.reset_index(drop=True, inplace=True)
        # ensure the index is reset after filtering

    def update_count_label(self):
        """Set count label at bottom of media table"""
        self.selected_rows = self.media_table.selectedRows()
        self.update_selection_bar()
        if len(self.selected_rows) > 0:
            self.count_label.setText(f"Selected: {len(self.selected_rows)} / {self.media_table.rowCount()}")
        else:
            self.count_label.setText(f"Total Media: {self.media_table.rowCount()}")

    def _apply_sort(self):
        """Reapply the current sort order to the media table"""
        header = self.view.horizontalHeader()
        col = header.sortIndicatorSection()
        if 0 <= col < self.media_table.columnCount():
            self.media_table.sort(col, header.sortIndicatorOrder())

    def add_edit_to_stack(self, edit):
        """Slot to receive updates from QTableWidget to add edit to stack"""
        # handle select edits
        if edit.reference == "select":
            self.handle_selection_change()
            self.update_edd_buttons()
        # everything else, just append the edit to the stack
        else:
            self.edit_stack.append(edit)
            self.check_undo_button()

    def handle_selection_change(self):
        """Slot to handle selection changes in the media table"""
        selected_rows = self.media_table.selectedRows()
        if len(selected_rows) > 0:
            self.button_edit.setEnabled(True)
            # self.button_duplicate.setEnabled(True)
            self.button_delete.setEnabled(True)
            self.update_count_label()
        else:
            self.button_edit.setEnabled(False)
            self.button_duplicate.setEnabled(False)
            self.button_delete.setEnabled(False)
            self.update_count_label()

    # ==========================================================================
    # BUTTONS
    # ==========================================================================

    def update_selection_bar(self):
        """Show the selection actions while rows are ticked, with how many"""
        bar = getattr(self, 'selection_bar', None)
        if bar is None:
            return
        n = len(self.media_table.selectedRows())
        self.selection_label.setText(f"{n:,} selected")
        # comparing needs at least two rois
        self.button_compare_selected.setVisible(self.data_type == 1)
        self.button_compare_selected.setEnabled(n > 1)
        bar.setVisible(n > 0)

    def update_type_counts(self):
        """Show how many media and rois there are on the Full Images / ROIs toggle"""
        if self.mpDB is None:
            return
        self.show_type.setItemText(0, f"Full Images · {self.mpDB.count('media'):,}")
        self.show_type.setItemText(1, f"ROIs · {self.mpDB.count('roi'):,}")

    def update_edd_buttons(self):
        """Enable/Disable Edit, Duplicate, Delete buttons based on selection and mode"""
        has_selection = len(self.media_table.selectedRows()) > 0
        self.update_selection_bar()
        # Only allow edit in ROI mode
        self.button_edit.setEnabled(has_selection)
        # self.button_duplicate.setEnabled(has_selection)
        self.button_delete.setEnabled(has_selection)

    def check_undo_button(self):
        """Enable/Disable Undo button based on edit stack"""
        if len(self.edit_stack) > 0:
            self.button_undo.setEnabled(True)
            self.button_save.setStyleSheet(self.SAVE_STYLE)
        else:
            self.button_undo.setEnabled(False)
            self.button_save.setStyleSheet("")
        notice = getattr(self, 'unsaved_label', None)
        if notice is not None:
            n = len(self.edit_stack)
            notice.setText(f"{n} unsaved edit{'s' if n != 1 else ''}")
            notice.setVisible(n > 0)

    def set_button_select(self):
        """Handle Select All button press, invert selection"""
        if self.button_select.isChecked():
            self.media_table.selectAll(select=False)
        else:
            self.media_table.selectAll(select=True)
        self.handle_selection_change()

    def undo(self):
        """Undo last edit"""
        if len(self.edit_stack) > 0:
            print("Undoing last edit:", self.edit_stack[-1])
            self.edit_stack.pop()
            self.check_undo_button()
            self.refresh_table()

    # EDIT POPUP ---------------------------------------------------------------

    def save(self):
        """Save changes to the database in the order they were made"""
        failed = save_edits(self.mpDB, self.edit_stack, self._individual_of, media_only=self.data_type == 0)

        # keep unsaved edits so they are not silently lost
        self.edit_stack = failed
        self.check_undo_button()
        if failed:
            dialog = AlertPopup(self, prompt=f"{len(failed)} change(s) could not be saved, see the log for details.")
            dialog.exec()
            del dialog
        # reload so filters and undo work from the saved values
        self.refresh_table(reload=True)

    def _individual_of(self, rid):
        """
        A roi's individual as loaded, for save_edits to apply sex edits to

        Looks in the unfiltered data, the roi may be hidden by the current filter.
        """
        rows = self._data_raw.loc[self._data_raw['id'] == rid, 'individual_id']
        return rows.iloc[0] if len(rows) else None

    def edit_row(self, row):
        """Edit a single row"""
        data = self.media_table._data_filtered.iloc[[row]].reset_index(drop=True)
        current_image_index = 0

        # EDIT ROI
        if self.data_type == 1:
            ext = self.media_table._data_filtered.at[row, "ext"]
            data = self.media_table._data_filtered.iloc[[row]]
            # display the video for frame rois for context
            if ext not in IMAGE_EXT:
                mid = int(self.media_table._data_filtered.at[row, "media_id"])
                video = self.media_table._data_filtered[self.media_table._data_filtered['media_id'] == mid]
                video_row = video.iloc[[0]].copy().reset_index(drop=True)
                video_row['media_id'] = mid
                # clear out roi columns for video row so mediawidget behaves correctly
                video_row[['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h',
                           'viewpoint', 'individual_id', 'sex']] = pd.NA
                data = pd.concat([data, video_row], ignore_index=True)  # add video row

        # Launch Media Edit Popup
        if not self._media_found(data):
            return
        dialog = MediaEditPopup(self, data, self.data_type, current_image_index=current_image_index)
        if dialog.exec():
            edit_stack = dialog.get_edit_stack()
            self.edit_stack.extend(edit_stack)  # send to media table
            self.check_undo_button()
        # rows deleted or rois redrawn in the popup need a reload, even after Cancel
        roi_updated = dialog.roi_updated
        # free the popup (and its media player), it is parented to this view
        dialog.deleteLater()
        del dialog
        # reload data and update buttons
        self.refresh_table(reload=roi_updated)

    def edit_thumbnail(self, index):
        """
        Edit a single row when its thumbnail is double-clicked.

        Connected to the view's doubleClicked signal. Only the thumbnail column opens the
        popup, double-clicking the editable columns edits them in place instead.
        """
        if self.media_table._columns[index.column()] == "thumbnail_path":
            self.edit_row(index.row())

    def edit_row_multiple(self):
        """Edit multiple selected rows"""
        self.selected_rows = self.media_table.selectedRows()
        data = self.media_table._data_filtered.iloc[self.selected_rows].reset_index(drop=True)
        current_image_index = 0
        # Launch Media Edit Popup
        if not self._media_found(data):
            return
        dialog = MediaEditPopup(self, data, self.data_type, current_image_index=current_image_index)
        if dialog.exec():
            edit_stack = dialog.get_edit_stack()
            self.edit_stack.extend(edit_stack)  # send to media table
            self.check_undo_button()
        # rows deleted or rois redrawn in the popup need a reload
        roi_updated = dialog.roi_updated
        # free the popup (and its media player), it is parented to this view
        dialog.deleteLater()
        del dialog
        # reload data and update buttons
        self.refresh_table(reload=roi_updated)

    def _media_found(self, data):
        """
        Whether every media file in data exists, warning the user if not.

        Called by edit_row and edit_row_multiple before opening MediaEditPopup, which
        crashes on a missing file, e.g. when the source directories moved and have not
        been updated. Kept separate so both share the check and the message.
        """
        missing = [f for f in data['filepath'].dropna().unique() if not Path(f).is_file()]
        if not missing:
            return True
        logger.warning(f"Could not find {len(missing)} media file(s), e.g. {missing[0]}")
        dialog = AlertPopup(self, prompt=f"Could not find {len(missing)} media file(s), e.g.\n{missing[0]}\n\n"
                                         "If the media has moved, update its location in\n"
                                         "Edit > Configuration > Edit Source Directories.")
        dialog.exec()
        del dialog
        return False

    def duplicate(self):
        """Duplicate selected rows in the database."""
        self.selected_rows = self.media_table.selectedRows()
        if len(self.selected_rows) > 0:
            dialog = AlertPopup(self, f"Are you sure you want to duplicate {len(self.selected_rows)} files?", title="Warning")
            if dialog.exec():
                for row in self.selected_rows:
                    if self.data_type == 1:
                        mid = int(self.media_table._data_filtered.at[row, "media_id"])
                        self.mpDB.copy("media", mid)
                    else:
                        mid = int(self.media_table._data_filtered.at[row, "id"])
                        self.mpDB.copy("media", mid)
                del dialog

    def delete(self):
        """Delete selected rows from database"""
        self.selected_rows = self.media_table.selectedRows()
        if len(self.selected_rows) > 0:
            dialog = AlertPopup(self, f"""Are you sure you want to delete {len(self.selected_rows)} files? This cannot be undone.""", title="Warning")
            if dialog.exec():
                ids = self.media_table._data_filtered.loc[self.selected_rows, "id"].tolist()
                # media take their rois, thumbnails and embeddings with them
                if self.data_type == 0:
                    delete_media(self.mpDB, ids)
                else:
                    delete_rois(self.mpDB, ids)
                # Reload updated data
                self.load_table()
            del dialog

    # Get headers for the media table based on the current data type
    def _get_headers(self):
            """Return the headers for the media table based on the current data type"""
            if self.data_type == 1:
                # what is checked while validating comes first, beside the thumbnail
                headers = {0: ["select", "Select"],
                           1: ["thumbnail_path", "Thumbnail"],
                           2: ["individual_id", "Individual"],
                           3: ["viewpoint", "Viewpoint"],
                           4: ["favorite", "Favorite"],
                           5: ["sex", "Sex"],
                           6: ["filepath", "Filepath"],
                           7: ["timestamp", "Timestamp"],
                           8: ["station_id", "Station"],
                           9: ["camera_id", "Camera"],
                           10: ["sequence_id", "Sequence ID"],
                           11: ["external_id", "External ID"],
                           12: ["comment", "Comment"]}
            else:
                headers = {0: ["select", "Select"],
                           1: ["thumbnail_path", "Thumbnail"],
                           2: ["filepath", "Filepath"],
                           3: ["ext", "Extension"],
                           4: ["timestamp", "Timestamp"],
                           5: ["station_id", "Station"],
                           6: ["camera_id", "Camera"],
                           7: ["sequence_id", "Sequence ID"],
                           8: ["external_id", "External ID"],
                           9: ["comment", "Comment"],
                           10: ["roi_count", "# of Rois"]}
            return headers

    def _set_column_widths(self):
        """
        Size the table's columns by name, the rest at the header's default width

        Called from __init__ and by handle_data_loaded when the headers change, since
        the view keeps widths by position and the two data types put different columns
        at the same position (eg. Extension is only in the media view).
        """
        header = self.view.horizontalHeader()
        default = header.defaultSectionSize()
        for i, column in enumerate(self.media_table._columns):
            self.view.setColumnWidth(i, self.COLUMN_WIDTHS.get(column, default))
            # filepath and comment share the leftover width, the rest are resizable
            stretch = column in self.STRETCH_COLUMNS
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch if stretch
                                        else QHeaderView.ResizeMode.Interactive)

    def _set_delegates(self):
        """Set delegates for the table based on the data type"""
        columns = [h[0] for h in self._get_headers().values()]
        VIEWPOINT_COLUMN = columns.index("viewpoint") if "viewpoint" in columns else 8
        SEX_COLUMN = columns.index("sex") if "sex" in columns else 10

        if self.data_type == 1:  # ROI view
            combo_items = list(self.VIEWPOINTS.values())[1:]
            self.view.setItemDelegateForColumn(VIEWPOINT_COLUMN, ComboBoxDelegate(combo_items, self))
            # SEX COMBOBOX
            combo_items = ['Unknown', 'Male', 'Female']
            self.view.setItemDelegateForColumn(SEX_COLUMN, ComboBoxDelegate(combo_items, self))

        else:
            # the roi view's combo columns sit at other positions, clear them all
            for column in range(max(len(columns), 13)):
                self.view.setItemDelegateForColumn(column, None)
