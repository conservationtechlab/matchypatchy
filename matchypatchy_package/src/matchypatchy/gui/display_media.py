"""
GUI Window for viewing images
"""
import pandas as pd
from PyQt6.QtWidgets import (QHeaderView, QPushButton, QTableView, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QComboBox, QDialog)
from PyQt6.QtCore import Qt, pyqtSignal

from matchypatchy.database.media import IMAGE_EXT, fetch_roi, fetch_individual
from matchypatchy.gui.media_table import MediaTable
from matchypatchy.gui.dialogs.popup_alert import AlertPopup
from matchypatchy.gui.dialogs.popup_media_edit import MediaEditPopup
from matchypatchy.gui.widgets.gui_assets import VerticalSeparator, StandardButton, ComboBoxDelegate
from matchypatchy.gui.widgets.widget_filterbar import FilterBar
from matchypatchy.threads.table_thread import FetchTableThread
from matchypatchy.threads.model_download_thread import load_model


class DisplayMedia(QWidget):
    """GUI class for displaying and managing media content."""

    SAVE_STYLE = """ QPushButton { background-color: #2a3e5e; color: white; }"""
    edit_stack_signal = pyqtSignal(list)  # Signal to send edit stack to main GUI

    def __init__(self, parent, data_type=1):
        super().__init__()
        self.parent = parent
        self.logger = parent.logger
        self.cfg = parent.cfg
        self.mpDB = parent.mpDB
        self.VIEWPOINTS = load_model('VIEWPOINTS')
        # 0 for Media, 1 for ROI
        self.data_type = data_type
        self.valid_stations = []
        self.selected_rows = []

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
        self.view.verticalHeader().sectionDoubleClicked.connect(self.edit_row)
        for col in range(self.media_table.columnCount()):
            self.view.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.view.setColumnWidth(0, 40)  # Set the width of the select column
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

    def update_project(self, cfg, mpDB):
        """Update database object"""
        self.cfg = cfg
        self.mpDB = mpDB
        self.filterbar.update_project(mpDB)

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
                selected_rows = self.view.selectionModel().selectedRows()
                rois = self.media_table._data_filtered.loc[[index.row() for index in selected_rows], "id"]
                rois = rois.tolist()
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
    def show_progress(self, prompt):
        """Progress Popup for Match Thread"""
        if not hasattr(self, 'progress') or self.progress is None:
            self.progress = AlertPopup(self, prompt, progressbar=True, cancel_only=False)
        self.progress.update_prompt(prompt)
        self.progress.show()

    def update_prompt(self, prompt):
        """Update the prompt in the progress popup"""
        if hasattr(self, 'progress') and self.progress is not None:
            self.progress.update_prompt(prompt)

    def update_progress(self, progress):
        """Update the progress bar in the progress popup"""
        if hasattr(self, 'progress') and self.progress is not None:
            self.progress.set_counter(progress)

    def set_progress_max(self, max_value):
        """Set the maximum value for the progress bar"""
        if hasattr(self, 'progress') and self.progress is not None:
            self.progress.set_max(max_value)

    def close_progress(self):
        """Close the progress popup"""
        if hasattr(self, 'progress') and self.progress is not None:
            self.progress.close()
            self.progress = None

    def show_alert(self, message):
        """Display an alert message to the user"""
        dialog = AlertPopup(self, prompt=message)
        dialog.exec()
        del dialog

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
            dialog = AlertPopup(self, prompt="There are unsaved changes. Are you sure you want to change view?")
            cont = dialog.exec()
            del dialog
            if cont == QDialog.DialogCode.Rejected:
                self.show_type.blockSignals(True)
                self.show_type.setCurrentIndex(self.data_type)
                self.show_type.blockSignals(False)
                return
        # change type to selected
        self.data_type = self.show_type.currentIndex()
        # reload table
        self.toggle_filterbar_datatype()
        self.load_table()

    # 1. RUN ON ENTRY
    def load_table(self):
        """Load media/roi data into table based on current data_type"""
        # check if there are rois first
        roi_n = self.mpDB.count('roi')
        media_n = self.mpDB.count('media')

        if media_n == 0:
            # no media at all
           # self.media_table.clear_and_load_contents(self.data_type)
            self.update_prompt("No images found! Please import media.")
            if self.progress.exec():
                self.home()
            return False
        else:
            if self.data_type == 1 and roi_n == 0:
                # no rois, default to full images
                self.data_type = 0
                self.update_prompt("No rois found, defaulting to full images.")

                self.show_type.blockSignals(True)
                self.show_type.setCurrentIndex(self.data_type)
                self.show_type.blockSignals(False)

            # load table with current data type
            self.individual_list = fetch_individual(self.mpDB)
            self.dataloader = FetchTableThread(self)
            self.dataloader.loaded_data.connect(lambda data: self.handle_data_loaded(data))
            self.dataloader.progress_max.connect(lambda n_missing: self.set_progress_max(n_missing))
            self.dataloader.progress_update.connect(lambda progress: self.update_progress(progress))
            self.dataloader.done.connect(self.close_progress)  # Close the progress dialog when done
            self.dataloader.start()
            return True

    def handle_data_loaded(self, data=None):
        """Handle data loaded from the FetchTableThread"""
        self._data_raw = data
        self.apply_edits()  # Apply any pending edits to the raw data before filtering
        self.filter_data()  # Apply filters to the raw data to get the filtered data
        headers = self._get_headers()
        self.media_table.receiveData(self._data_filtered, headers=headers) # Send the filtered data to the media table for display
        self._set_delegates()
        self.update_count_label()
        self.update_edd_buttons()

    def refresh_table(self):
        """Refresh the table by reapplying edits and filters"""
        self.apply_edits()
        self.filter_data()
        self.media_table.receiveData(self._data_filtered)
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
                print("Applying edit for RID:", edit.rid)
                self._data_filtered.loc[self._data_filtered["id"] == edit.rid, edit.reference] = edit.new_value
                print(self._data_filtered[self._data_filtered["id"] == edit.rid])
            else:
                self._data_filtered.loc[self._data_filtered["id"] == edit.mid, edit.reference] = edit.new_value
            
    def filter_data(self):
        """Filter the data based on the provided filters"""
        # if no media, skip
        if self._data_filtered.empty:
            return
        # self.valid_cameras =  # select all cameras for now
        self.valid_cameras = dict(self.mpDB.select("camera", columns="id, name"))
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
                self._data_filtered = self._data_filtered[self._data_filtered['viewpoint'] == self.filters['active_viewpoint'][0] - 1]
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
        self.count_label.setText(f"Total Media: {self.media_table.rowCount()}")

    def update_count_label_selected(self):
        """Set count label at bottom of media table to show selected/total"""
        self.count_label.setText(f"Selected: {len(self.media_table.selectedRows())} / {self.media_table.rowCount()}")

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
            self.update_count_label_selected()
        else:
            self.button_edit.setEnabled(False)
            self.button_duplicate.setEnabled(False)
            self.button_delete.setEnabled(False)
            self.update_count_label()

    def save(self):
        """Save changes to the media table"""
        #self.media_table.save_changes()
        while len(self.edit_stack) > 0:
            edit = self.edit_stack.pop()
            replace_dict = {edit.reference: edit.new_value}
            # roi view
            if self.data_type == 1:
                # edit media table value
                if edit.reference in {'station_id', 'sequence_id', 'external_id', 'comment'}:
                    self.mpDB.edit_row("media", edit.mid, replace_dict, allow_none=False, quiet=False)
                # edit individual table value
                elif edit.reference in {'age', 'sex'}:
                    iid = self.data_filtered.loc[self.data_filtered['id'] == edit.rid, 'individual_id'].values[0]
                    iid = int(iid) if pd.notna(iid) else None
                    if iid is not None:
                        self.mpDB.edit_row("individual", iid, replace_dict, allow_none=False, quiet=False)
                # edit roi table value
                else:
                    self.mpDB.edit_row("roi", edit.rid, replace_dict, allow_none=False, quiet=False)
            # media view
            else:
                self.mpDB.edit_row("media", edit.mid, replace_dict, allow_none=False, quiet=False)

        # reload data and refresh table
        self.edit_stack = []
        #self.clear_and_load_contents(self.data_type)
        self.check_undo_button()

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
            self.update_count_label()
        else:
            self.media_table.selectAll(select=True)
            self.update_count_label_selected()

    def undo(self):
        """Undo last edit"""
        if len(self.edit_stack) > 0:
            print("Undoing last edit:", self.edit_stack[-1])
            self.edit_stack.pop()
            self.refresh_table() 

    # EDIT POPUP ---------------------------------------------------------------

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
                           'viewpoint', 'individual_id', 'age', 'sex']] = pd.NA
                data = pd.concat([data, video_row], ignore_index=True)  # add video row

        # Launch Media Edit Popup
        dialog = MediaEditPopup(self, data, self.data_type, current_image_index=current_image_index)
        if dialog.exec():
            edit_stack = dialog.get_edit_stack()
            self.edit_stack_signal.emit(edit_stack)  # send to media table
            self.check_undo_button()
            del dialog
        # reload data and update buttons
        self.load_table()

    def edit_row_multiple(self):
        """Edit multiple selected rows"""
        selected_rows = self.media_table.selectedRows()
        data = self.media_table._data_filtered.iloc[selected_rows].reset_index(drop=True)
        current_image_index = 0
        # Launch Media Edit Popup
        dialog = MediaEditPopup(self, data, self.data_type, current_image_index=current_image_index)
        if dialog.exec():
            edit_stack = dialog.get_edit_stack()
            self.edit_stack_signal.emit(edit_stack)  # send to media table
            self.check_undo_button()
            del dialog
        # reload data and update buttons
        self.load_table()

    def duplicate(self):
        """Duplicate selected rows in the database."""
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
        if len(self.selected_rows) > 0:
            dialog = AlertPopup(self, f"""Are you sure you want to delete {len(self.selected_rows)} files? This cannot be undone.""", title="Warning")
            if dialog.exec():
                for row in self.selected_rows:
                    if self.data_type == 0:
                        id = int(self.media_table._data_filtered.at[row, "id"])
                        # delete all rois associated with this media
                        rois = fetch_roi(self.mpDB, media_id=id)
                        if len(rois) > 0:
                            for roi in rois['roi_id']:
                                self.mpDB.delete_emb(id=roi)
                        # cascade delete will handle associated roi_thumbnails and roi entries
                        self.mpDB.delete('media', f'id={id}')
                    else:
                        id = int(self.media_table._data_filtered.at[row, "id"])
                        self.mpDB.delete_emb(id=id)
                        self.mpDB.delete('roi', f'id={id}')
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
                           11: ["age", "Age"],
                           12: ["reviewed", "Reviewed"],
                           13: ["favorite", "Favorite"],
                           14: ["comment", "Comment"]}
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
        AGE_COLUMN = 11    

        if self.data_type == 1:  # ROI view
            combo_items = list(self.VIEWPOINTS.values())[1:]
            self.view.setItemDelegateForColumn(VIEWPOINT_COLUMN, ComboBoxDelegate(combo_items, self))
            # SEX COMBOBOX
            combo_items = ['Unknown', 'Male', 'Female']
            self.view.setItemDelegateForColumn(SEX_COLUMN, ComboBoxDelegate(combo_items, self))
            # AGE COMBOBOX
            combo_items = ['Unknown', 'Juvenile', 'Subadult', 'Adult']
            self.view.setItemDelegateForColumn(AGE_COLUMN, ComboBoxDelegate(combo_items, self))

        else:
            self.view.setItemDelegateForColumn(VIEWPOINT_COLUMN, None)
            self.view.setItemDelegateForColumn(SEX_COLUMN, None)
            self.view.setItemDelegateForColumn(AGE_COLUMN, None)