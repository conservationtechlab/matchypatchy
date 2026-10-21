"""
GUI Window for viewing images
"""
import logging
import pandas as pd
from PyQt6.QtWidgets import (QHeaderView, QPushButton, QTableView, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QComboBox, QDialog)
from PyQt6.QtCore import Qt, pyqtSignal

from matchypatchy.database.media import IMAGE_EXT, fetch_individual, delete_media, delete_rois
from matchypatchy.database.location import camera_names
from matchypatchy.gui.media_table import MediaTable
from matchypatchy.gui.dialogs.popup_alert import AlertPopup
from matchypatchy.gui.dialogs.popup_media_edit import MediaEditPopup
from matchypatchy.gui.widgets.gui_assets import VerticalSeparator, StandardButton, ComboBoxDelegate
from matchypatchy.gui.widgets.widget_filterbar import FilterBar
from matchypatchy.threads.table_thread import FetchTableThread
from matchypatchy.threads.model_download_thread import load_model
from matchypatchy.threads.match_object import viewpoint_value
from matchypatchy.project import UsesProject


logger = logging.getLogger(__name__)


class DisplayMedia(UsesProject, QWidget):
    """GUI class for displaying and managing media content."""

    SAVE_STYLE = """ QPushButton { background-color: #2a3e5e; color: white; }"""
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
        # table loads, a newer load supersedes older ones still running
        self._load_id = 0
        self._loaders = []

        # data and edit stack
        self._data_raw = pd.DataFrame()
        self._data_filtered = pd.DataFrame()
        self.edit_stack = []
        
        layout = QVBoxLayout()
        # First Layer ----------------------------------------------------------
        first_layer = QHBoxLayout()
        # Change Views
        first_layer.addSpacing(10)
        button_return = StandardButton("Home")
        button_return.clicked.connect(self.home)
        first_layer.addWidget(button_return, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        button_compare = StandardButton("Compare")
        button_compare.clicked.connect(self.compare)
        first_layer.addWidget(button_compare, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        first_layer.addWidget(VerticalSeparator())

        # Show Type
        first_layer.addWidget(QLabel("Show:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.show_type = QComboBox()
        self.show_type.addItems(["Full Images", "ROIs"])
        self.show_type.setCurrentIndex(self.data_type)
        self.show_type.currentIndexChanged.connect(self.change_type)
        first_layer.addWidget(self.show_type, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        first_layer.addWidget(VerticalSeparator())

        # Save
        self.button_save = StandardButton("Save")
        self.button_save.clicked.connect(self.save)
        first_layer.addWidget(self.button_save, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Undo
        self.button_undo = StandardButton("Undo")
        self.button_undo.clicked.connect(self.undo)
        self.button_undo.setEnabled(False)
        first_layer.addWidget(self.button_undo, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        first_layer.addWidget(VerticalSeparator())

        # Select All
        self.button_select = StandardButton("Select All")
        self.button_select.setCheckable(True)
        self.button_select.pressed.connect(self.set_button_select)
        first_layer.addWidget(self.button_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Edit Rows
        self.button_edit = StandardButton("Edit Rows")
        self.button_edit.clicked.connect(self.edit_row_multiple)
        self.button_edit.setEnabled(False)
        first_layer.addWidget(self.button_edit, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Duplicate
        self.button_duplicate = StandardButton("Duplicate Rows")
        self.button_duplicate.clicked.connect(self.duplicate)
        self.button_duplicate.setEnabled(False)
        first_layer.addWidget(self.button_duplicate, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Delete
        self.button_delete = StandardButton("Delete Rows")
        self.button_delete.clicked.connect(self.delete)
        self.button_delete.setEnabled(False)
        first_layer.addWidget(self.button_delete, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        first_layer.addStretch()
        layout.addLayout(first_layer)

        # FILTERS --------------------------------------------------------------
        second_layer = QHBoxLayout()
        second_layer.addSpacing(5)
        self.filterbar = FilterBar(self, 180)
        second_layer.addWidget(self.filterbar, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.filters = self.filterbar.get_filters()  # get initial filters
        button_filter = QPushButton("Apply Filters")
        button_filter.clicked.connect(self.filter_table)
        button_clear_filter = QPushButton("Clear Filters")
        button_clear_filter.clicked.connect(self.clear_filters)
        second_layer.addWidget(button_filter, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        second_layer.addWidget(button_clear_filter, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        second_layer.addStretch()
        layout.addLayout(second_layer)

        # display rois or media
        self._data_raw = pd.DataFrame()
        self.view = QTableView()
        self.media_table = MediaTable(self, self._get_headers())
        self.view.setModel(self.media_table)
        self.view.setSortingEnabled(True)
        self.view.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.view.horizontalHeader().setSortIndicatorShown(True)
        self.view.horizontalHeader().setSectionsClickable(True)
        self.view.verticalHeader().setDefaultSectionSize(150)  # row size = thumbnail with
        self.view.horizontalHeader().setDefaultSectionSize(80)
        self.view.verticalHeader().sectionDoubleClicked.connect(self.edit_row)
        self.view.setColumnWidth(0, 30)  # Set the width of the select column
        self.view.setColumnWidth(1, 150)  # Set the width of the thumbnail column
        self.view.setColumnWidth(2, 50)  # Set the width of the filepath column, allow stretch
        self.view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)


        # Connect the selection changed signal from the media table to a handler
        self.media_table.user_edit.connect(self.add_edit_to_stack)
        layout.addWidget(self.view, stretch=1)

        # Count Label at Bottom
        self.count_label = QLabel("")
        layout.addWidget(self.count_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)

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

    def hide_progress(self):
        """Hide the progress bar in the progress popup"""
        if hasattr(self, 'alert_box') and self.alert_box is not None:
            self.alert_box.progress_bar.hide()

    def update_progress(self, progress):
        """Update the progress bar in the progress popup"""
        if hasattr(self, 'alert_box') and self.alert_box is not None:
            self.alert_box.set_counter(progress)

    def set_progress_max(self, max_value):
        """Set the maximum value for the progress bar"""
        # connects to FetchTableThread's progress_max signal
        if hasattr(self, 'alert_box') and self.alert_box is not None:
            self.update_prompt("Collecting missing thumbnails...")
            self.alert_box.set_max(max_value)
            self.alert_box.progress_bar.setFormat("%v/%m")   # shows percentage, e.g. 42%

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
        # individual and unidentified filters only apply to rois
        if prefilter and ('individual_id' in prefilter or prefilter.get('unidentified_only')):
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

    def clear_filters(self):
        """Clear all filters and refresh the table"""
        self.refresh_filters()
        self.refresh_table()

    # =========================================================================
    # MEDIA TABLE HANDLERS
    # =========================================================================

    # CHANGE VIEW TYPE (FULL IMAGE / ROI)
    def change_type(self):
        """Change between full image and ROI view"""
        if len(self.edit_stack) > 0:
            dialog = AlertPopup(self, prompt="Are you sure you want to change view? There are unsaved changes that will be lost.")
            cont = dialog.exec()
            del dialog
            if cont == QDialog.DialogCode.Rejected:
                self.show_type.blockSignals(True)
                self.show_type.setCurrentIndex(self.data_type)
                self.show_type.blockSignals(False)
                return
        # Clear unsaved edits since user confirmed they want to change view
        self.edit_stack.clear()
        self.check_undo_button()
            
        # change type to selected
        self.data_type = self.show_type.currentIndex()
        # reload table
        self.toggle_filterbar_datatype()
        self.load_table()

    # 1. RUN ON ENTRY
    def load_table(self):
        """Load media/roi data into table based on current data_type"""
        # check if there are rois first
        self.show_alert("Loading media...")
        roi_n = self.mpDB.count('roi')
        media_n = self.mpDB.count('media')

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
            if self.data_type == 1 and roi_n == 0:
                # no rois, default to full images
                self.data_type = 0
                self.update_prompt("No rois found, defaulting to full images.")
                self.hide_progress()

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
        for signal in (loader.loaded_data, loader.progress_max, loader.progress_update, loader.done):
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
        self.media_table.receiveData(self._data_filtered, headers=headers) # Send the filtered data to the media table for display
        # reloaded rows come back unticked
        self.button_select.setChecked(False)
        self._apply_sort()
        self._set_delegates()
        self.update_count_label()
        self.update_edd_buttons()

    def refresh_table(self, reload=False):
        """Refresh the table by reapplying edits and filters"""
        if reload:
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
        else:
            if self.filters['no_roi_mids'] is not False:
                self._data_filtered = self._data_filtered[self._data_filtered['id'].isin(self.filters['no_roi_mids'])]

        # no valid stations, empty dataframe
        self._data_filtered.reset_index(drop=True, inplace=True)
        # ensure the index is reset after filtering

    def update_count_label(self):
        """Set count label at bottom of media table"""
        self.selected_rows = self.media_table.selectedRows()
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

    def update_edd_buttons(self):
        """Enable/Disable Edit, Duplicate, Delete buttons based on selection and mode"""
        has_selection = len(self.media_table.selectedRows()) > 0
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

    # media table columns edited from the roi view
    MEDIA_COLUMNS = {'station_id', 'sequence_id', 'external_id', 'comment'}

    def save(self):
        """Save changes to the database in the order they were made"""
        failed = []
        # individual_id edits applied so far, so a later sex edit targets the new individual
        assigned_iids = {}
        for edit in self.edit_stack:
            if not self._save_edit(edit, assigned_iids):
                failed.append(edit)

        # keep unsaved edits so they are not silently lost
        self.edit_stack = failed
        self.check_undo_button()
        if failed:
            dialog = AlertPopup(self, prompt=f"{len(failed)} change(s) could not be saved, see the log for details.")
            dialog.exec()
            del dialog
        # reload so filters and undo work from the saved values
        self.refresh_table(reload=True)

    def _save_edit(self, edit, assigned_iids):
        """Write one EditObject to the database, return False if it failed"""
        replace_dict = {edit.reference: edit.new_value}
        # media view, or media columns from the roi view
        if self.data_type == 0 or edit.reference in self.MEDIA_COLUMNS:
            return self.mpDB.edit_row("media", int(edit.mid), replace_dict, allow_none=True)
        # rows without a roi id (eg. the full video row) have nothing to update
        if edit.rid is None or pd.isna(edit.rid):
            return True
        rid = int(edit.rid)
        if edit.reference == 'sex':
            # look up in the unfiltered data, the roi may be hidden by the current filter
            if rid in assigned_iids:
                iid = assigned_iids[rid]
            else:
                rows = self._data_raw.loc[self._data_raw['id'] == rid, 'individual_id']
                iid = rows.iloc[0] if len(rows) else None
            if iid is None or pd.isna(iid):
                return True  # no individual to update
            return self.mpDB.edit_row("individual", int(iid), replace_dict, allow_none=True)
        # roi columns; individual_id and viewpoint may be cleared (Unknown / None)
        ok = self.mpDB.edit_row("roi", rid, replace_dict, allow_none=True)
        if ok and edit.reference == 'individual_id':
            assigned_iids[rid] = edit.new_value
        return ok

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

    def edit_row_multiple(self):
        """Edit multiple selected rows"""
        self.selected_rows = self.media_table.selectedRows()
        data = self.media_table._data_filtered.iloc[self.selected_rows].reset_index(drop=True)
        current_image_index = 0
        # Launch Media Edit Popup
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
                headers = {0: ["select", "Select"],
                           1: ["thumbnail_path", "Thumbnail"],
                           2: ["filepath", "Filepath"],
                           3: ["timestamp", "Timestamp"],
                           4: ["station_id", "Station"],
                           5: ["camera_id", "Camera"],
                           6: ["sequence_id", "Sequence ID"],
                           7: ["external_id", "External ID"],
                           8: ["viewpoint", "Viewpoint"],
                           9: ["individual_id", "Individual"],
                           10: ["sex", "Sex"],
                           11: ["reviewed", "Reviewed"],
                           12: ["favorite", "Favorite"],
                           13: ["comment", "Comment"]}
            else:
                headers = {0: ["select", "Select"],
                           1: ["thumbnail_path", "Thumbnail"],
                           2: ["filepath", "Filepath"],
                           3: ["timestamp", "Timestamp"],
                           4: ["station_id", "Station"],
                           5: ["camera_id", "Camera"],
                           6: ["sequence_id", "Sequence ID"],
                           7: ["external_id", "External ID"],
                           8: ["comment", "Comment"],
                           9: ["roi_count", "# of Rois"]}
            return headers

    def _set_delegates(self):
        """Set delegates for the table based on the data type"""
        VIEWPOINT_COLUMN = 8
        SEX_COLUMN = 10

        if self.data_type == 1:  # ROI view
            combo_items = list(self.VIEWPOINTS.values())[1:]
            self.view.setItemDelegateForColumn(VIEWPOINT_COLUMN, ComboBoxDelegate(combo_items, self))
            # SEX COMBOBOX
            combo_items = ['Unknown', 'Male', 'Female']
            self.view.setItemDelegateForColumn(SEX_COLUMN, ComboBoxDelegate(combo_items, self))

        else:
            self.view.setItemDelegateForColumn(VIEWPOINT_COLUMN, None)
            self.view.setItemDelegateForColumn(SEX_COLUMN, None)
