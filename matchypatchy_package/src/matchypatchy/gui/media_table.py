"""
Widget for displaying list of Media
"""
import pandas as pd

from PyQt6.QtWidgets import (QTableWidget, QVBoxLayout, QWidget, QLabel, QHeaderView)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QTimer, Qt, pyqtSignal

from matchypatchy.database.media import fetch_individual, EditObject
from matchypatchy.threads.model_download_thread import load_model
from matchypatchy.threads.table_thread import FetchTableThread, LoadTableThread

from matchypatchy.gui.dialogs.popup_alert import AlertPopup
from matchypatchy.gui.widgets.gui_assets import ComboBoxDelegate


class MediaTable(QWidget):
    """Widget for displaying list of Media"""

    update_signal = pyqtSignal(list)
    checkbox_signal = pyqtSignal()
    loaded_data = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.cfg = parent.cfg
        self.mpDB = parent.mpDB
        # threads
        self.dataloader = None
        self.table_loader_thread = None

        self.data = pd.DataFrame()
        self.data_filtered = pd.DataFrame()
        self.individual_list = pd.DataFrame()
        self.thumbnails = {}
        self.data_type = 1
        self.VIEWPOINTS = load_model('VIEWPOINTS')
        self.thumbnail_size = 150
        self.thumbnail_dir = self.cfg.THUMBNAIL_DIR
        self.columns = ["Select", "Thumbnail", "Filepath", "Timestamp",
                        "Station", "Camera", "Sequence ID", "External ID",
                        "Viewpoint", "Individual", "Sex", "Age",
                        "Reviewed", "Favorite", "Comment"]

        self.valid_stations = []
        self.valid_cameras = []

        # NOTE: do we want to refresh edit stack on re-entry?
        self.edit_stack = []

        # Set up layout
        layout = QVBoxLayout()
        # Create QTableWidget
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.columns))  # Columns: Thumbnail, Name, and Description
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        # Connect sorting
        self.sort_order = dict(zip(range(self.table.columnCount()),
                                   [Qt.SortOrder.AscendingOrder] * self.table.columnCount()))
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().setSectionsClickable(True)
        # Connect header click to sorting function
        self.table.horizontalHeader().sectionClicked.connect(self.sort)
        # Connect double click to edit row
        self.table.verticalHeader().sectionDoubleClicked.connect(self.edit_row)
        self.table.cellChanged.connect(self.update_entry)  # allow user editing

        # Add table to the layout
        layout.addWidget(self.table)
        self.setLayout(layout)

    def update_project(self, cfg, mpDB):
        """Update database object"""
        self.cfg = cfg
        self.mpDB = mpDB

    # RUN ON ENTRY -------------------------------------------------------------
    def clear_and_load_contents(self, data_type):
        """Clear all contents of the media table"""
        # clear old view and reformat
        self.data_type = data_type
        self.table.clearContents()
        self.table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        # run step 2
        self.format_table()

        # fetch data
        self.individual_list = fetch_individual(self.mpDB)
        self.dataloader = FetchTableThread(self)
        self.dataloader.done.connect(self.filter)
        self.dataloader.loaded_data.connect(lambda data: setattr(self, 'data', data))
        self.dataloader.start()

    # STEP 2 - CALLED BY load_data()
    def format_table(self):
        """
        Format table for media or roi display, add delegates for combos, and load thumbnails
        """
        VIEWPOINT_COLUMN = 8
        SEX_COLUMN = 10
        AGE_COLUMN = 11

        if self.data_type == 1:
            # corresponding mpDB column names
            self.columns = {0: "select",
                            1: "thumbnail",
                            2: "filepath",
                            3: "timestamp",
                            4: "station",
                            5: "camera_id",
                            6: "sequence_id",
                            7: "external_id",
                            8: "viewpoint",
                            9: "individual_id",
                            10: "sex",
                            11: "age",
                            12: "reviewed",
                            13: "favorite",
                            14: "comment"}

            self.table.setColumnCount(len(self.columns))  # Columns: Thumbnail, Name, and Description
            self.table.setHorizontalHeaderLabels(["Select", "Thumbnail", "Filepath", "Timestamp",
                                                  "Station", "Camera", "Sequence ID", "External ID",
                                                  "Viewpoint", "Individual", "Sex", "Age",
                                                  "Reviewed", "Favorite", "Comment"])
            # VIEWPOINT COMBOS
            combo_items = list(self.VIEWPOINTS.values())[1:]
            self.table.setItemDelegateForColumn(VIEWPOINT_COLUMN, ComboBoxDelegate(combo_items, self))
            # SEX COMBOBOX
            combo_items = ['Unknown', 'Male', 'Female']
            self.table.setItemDelegateForColumn(SEX_COLUMN, ComboBoxDelegate(combo_items, self))
            # AGE COMBOBOX
            combo_items = ['Unknown', 'Juvenile', 'Subadult', 'Adult']
            self.table.setItemDelegateForColumn(AGE_COLUMN, ComboBoxDelegate(combo_items, self))

        # MEDIA (data_type == 0)
        else:
            # corresponding mpDB column names
            self.columns = {0: "select",
                            1: "thumbnail",
                            2: "filepath",
                            3: "timestamp",
                            4: "station",
                            5: "camera_id",
                            6: "sequence_id",
                            7: "external_id",
                            8: "comment",
                            9: "roi_count"}
            self.table.setColumnCount(len(self.columns))  # Columns: Thumbnail, Name, and Description
            self.table.setHorizontalHeaderLabels(["Select", "Thumbnail", "Filepath", "Timestamp",
                                                  "Station", "Camera", "Sequence ID",
                                                  "External ID", "Comment", "# of Rois"])

            # clear item delegates (really only necessary for viewpoint)
            self.table.setItemDelegateForColumn(VIEWPOINT_COLUMN, None)
            self.table.setItemDelegateForColumn(SEX_COLUMN, None)
            self.table.setItemDelegateForColumn(AGE_COLUMN, None)

        # adjust widths
        self.table.resizeColumnsToContents()
        for col in range(self.table.columnCount()):
            if col == 0:  # select
                self.table.setColumnWidth(0, 40)
            elif col == 1:  # thumbnail
                self.table.setColumnWidth(col, max(self.table.columnWidth(col), self.thumbnail_size))
            else:
                self.table.setColumnWidth(col, max(self.table.columnWidth(col), 80))

        # increase checkbox size
        self.table.setStyleSheet("""QTableWidget::indicator { width: 25px; height: 25px;}""")

    # Step 3 - Filter and Display ------------------------------------------------------
    def filter(self):
        """
        Filter media based on active survey selected in dropdown of DisplayMedia
        Always run before updating table

        if filter > 0 : use id
        if filter == 0: do not filter
        if filter is None: select None
        """
        print("Filtering media with current filters:", self.parent.filters)
        print("Original data size:", self.data.shape)
        # create new copy of full dataset
        self.data_filtered = self.data.copy()

        # if no media, skip
        if self.data_filtered.empty:
            return

        # include user edits to current data_filtered:
        self.apply_edits()

        # map parent filters and valid stations/cameras to local variables
        filters = self.parent.filters
        self.valid_stations = self.parent.valid_stations
        # self.valid_cameras =  # select all cameras for now
        self.valid_cameras = dict(self.mpDB.select("camera", columns="id, name"))

        # Location Filter (depends on prefilterd stations from MediaDisplay)
        if self.valid_stations:
            self.data_filtered = self.data_filtered[self.data_filtered['station_id'].isin(list(self.valid_stations.keys()))]
            # Single station Filter
            if filters['active_station'][0] > 0:
                self.data_filtered = self.data_filtered[self.data_filtered['station_id'] == filters['active_station'][0]]
            self.data_filtered['station'] = self.data_filtered['station_id'].map(self.valid_stations)
        else:
            # no valid stations, empty dataframe
            self.data_filtered.drop(self.data_filtered.index, inplace=True)

        # ROI-only filters
        if self.data_type == 1:
            # Viewpoint Filter
            if filters['active_viewpoint'][0] > 0:
                self.data_filtered = self.data_filtered[self.data_filtered['viewpoint'] == filters['active_viewpoint'][0] - 1]
            elif filters['active_viewpoint'][0] is None:
                self.data_filtered = self.data_filtered[self.data_filtered['viewpoint'].isna()]

            # Individual Filter
            if filters['active_individual'][0] > 0:
                self.data_filtered = self.data_filtered[self.data_filtered['individual_id'] == filters['active_individual'][0]]
            elif filters['active_individual'][0] is None:
                self.data_filtered = self.data_filtered[self.data_filtered['individual_id'].isna()]

            # Unidentified Filter
            if filters['unidentified_only']:
                self.data_filtered = self.data_filtered[self.data_filtered['individual_id'].isna()]

            # Favorites Filter
            if filters['favorites_only']:
                self.data_filtered = self.data_filtered[self.data_filtered['favorite'] == 1]

        else:
            if filters['no_roi_mids'] is not False:
                self.data_filtered = self.data_filtered[self.data_filtered['id'].isin(filters['no_roi_mids'])]

        self.data_filtered.reset_index(inplace=True)

        # let display_media know about the new filtered data
        self.loaded_data.emit()

        # refresh table contents
        self.refresh_table()

    # triggered by filter() finishing
    def refresh_table(self, popup=True):
        """
        Add rows to table by creating LoadTableThread to generate QTableWidgetItems
        """
        # clear old contents and prep for filtered data
        self.table.clearContents()
        # reload individual data if necessary
        self.individual_list = fetch_individual(self.mpDB)
        # if there are any left
        n_rows = self.data_filtered.shape[0]

        if n_rows:
            # disconnect edit function while refreshing to prevent needless calls
            self.table.setRowCount(n_rows)
            for row in range(n_rows):
                self.table.setRowHeight(row, self.thumbnail_size)

            # set station delegate post filter
            station_delegate = ComboBoxDelegate(list(self.valid_stations.values()), self)
            self.table.setItemDelegateForColumn(4, station_delegate)

            # Disconnect cellChanged signals to prevent triggering during table refresh
            self.table.cellChanged.disconnect(self.update_entry)
            self.table_loader_thread = LoadTableThread(self)
            self.table_loader_thread.loaded_cell.connect(self.add_cell)
            self.table_loader_thread.done.connect(lambda: self.table.blockSignals(False))
            self.table_loader_thread.done.connect(self.reconnect_signals)
            self.table_loader_thread.done.connect(self.loaded_data.emit)
            self.table_loader_thread.done.connect(self.checkbox_signal.emit)

            if popup:
                loading_bar = AlertPopup(self, "Loading data...", progressbar=True, cancel_only=True)
                loading_bar.set_max(n_rows)
                self.table_loader_thread.progress_update.connect(loading_bar.set_counter)
                loading_bar.rejected.connect(self.table_loader_thread.requestInterruption)
                loading_bar.show()

            self.table_loader_thread.start()

    def reconnect_signals(self):
        """Reconnect cellChanged signals after table refresh"""
        self.table.cellChanged.connect(self.update_entry)

    def sort(self, column):
        """
        Sort table by column and order
        """
        reference = self.columns[column]
        if reference == 'thumbnail':
            return  # Do not sort by thumbnail column

        self.table.blockSignals(True)
        ascending = self.sort_order[column] == Qt.SortOrder.AscendingOrder
        self.data_filtered.sort_values(by=reference, ascending=ascending, inplace=True)
        self.data_filtered.reset_index(inplace=True, drop=True)
        self.refresh_table(popup=False)

        self.table.blockSignals(False)

        # invert sort order for next click
        self.sort_order[column] = (Qt.SortOrder.DescendingOrder
                                   if self.sort_order[column] == Qt.SortOrder.AscendingOrder
                                   else Qt.SortOrder.AscendingOrder)
        # update the arrow indicator shown in the header
        self.table.horizontalHeader().setSortIndicator(column, self.sort_order[column])

    # Set Table Entries --------------------------------------------------------
    def add_cell(self, row, column, qtw):
        """
        Connect LoadTableThread signal to add cell to table
        """
        self.table.blockSignals(True)
        if column == 1:
            pixmap = QPixmap.fromImage(qtw)
            qtw = QLabel()
            qtw.setPixmap(pixmap)
            self.table.setCellWidget(row, column, qtw)
        else:
            self.table.setItem(row, column, qtw)
           
    def get_checkstate_int(self, item):
        """Get integer value from checkstate of checkbox item"""
        return 1 if (item.checkState() == Qt.CheckState.Checked) else 0

    def invert_checkstate(self, item):
        """Invert checkstate of checkbox item"""
        if item.checkState() == Qt.CheckState.Checked:
            item.setCheckState(Qt.CheckState.Unchecked)
        else:
            item.setCheckState(Qt.CheckState.Checked)

    # UPDATE ENTRIES -----------------------------------------------------------
    def apply_edits(self):
        """
        Applies all previous edits to the current data_filter if the row is present
        """
        # if no edits, skip
        if len(self.edit_stack) == 0:
            return
        # apply edits to current data_filtered
        for edit in self.edit_stack:
            row, column = self.get_edit_table_item(edit)
            # item not found in current filter
            if row is None or column is None:
                continue
            # not relevant to this data type view
            if column not in self.data_filtered.columns:
                continue

            # print(f"DEBUG Applying edit: {edit} to row: {row}, column: {column}")
            # print(f"DEBUG Current data_filtered before edit: {self.data_filtered.loc[row, column]}")
            self.data_filtered.loc[row, column] = edit.new_value
            # print(f"DEBUG Current data_filtered after edit: {self.data_filtered.loc[row, column]}")

    def undo(self):
        """
        Undo last edit and refresh table
        """
        if len(self.edit_stack) > 0:
            last = self.edit_stack.pop()
            # revert the change in data_filtered
            row, column = self.get_edit_table_item(last)

            self.data_filtered.loc[row, column] = last.previous_value
            self.refresh_table(popup=False)

    def get_edit_table_item(self, edit):
        """
        Return Row and Column for a given edit object
        """
        # find row and column in current data_filtered
        if self.data_type == 1:
            if edit.rid is None:
                return None, None
            row = self.data_filtered.index[self.data_filtered['id'] == edit.rid].to_list()
        else:
            if edit.mid is None:
                return None, None
            row = self.data_filtered.index[self.data_filtered['id'] == edit.mid].to_list()
        if not row:
            return None, None

        # TODO - check if multiple rows found for the same edit, and handle accordingly
        if len(row) > 1:
            print(f"Warning: multiple rows found for edit {edit}. Using first match.")

        row = row[0]
        column = edit.reference

        return row, column

    def update_entry(self, row, column):
        """
        Allows user to edit entry directly in table

        Save edits in queue, allow undo
        prompt user to save edits
        """
        reference = self.columns[column]

        if self.data_type == 1:
            rid = int(self.data_filtered.at[row, "id"])
            media_id = int(self.data_filtered.at[row, "media_id"])
        else:
            rid = None
            media_id = int(self.data_filtered.at[row, "id"])

        if reference == 'select':
            item = self.table.item(row, column)
            if item is not None:
                checked = self.get_checkstate_int(item)
                self.data_filtered.loc[row, 'select'] = checked
                self.checkbox_signal.emit()
            return

        # checked items
        if reference in ['reviewed', 'favorite']:
            previous_value = int(self.data_filtered.at[row, reference])
            new_value = self.get_checkstate_int(self.table.item(row, column))
        # station
        elif reference == 'station':
            reference = 'station_id'
            previous_value = int(self.data_filtered.at[row, reference])
            new_value = [k for k, v in self.valid_stations.items() if v == self.table.item(row, column).text()][0]
        # viewpoint
        elif reference == 'viewpoint':
            previous_value = self.data_filtered.at[row, reference]
            # i hate this
            key = [k for k, v in self.VIEWPOINTS.items() if v == self.table.item(row, column).text()][0]
            if key == 'None':
                new_value = None
            else:
                new_value = int(key)
        # individual
        elif reference in ['individual_id', 'sex', 'age']:
            iid = self.data_filtered.at[row, "individual_id"]
            if iid is None:
                dialog = AlertPopup(self, "Please tag the ROI with an individual first.")
                dialog.exec()
                del dialog
                self.apply_edits()
                self.refresh_table(popup=False)
                return
            else:
                previous_value = self.data_filtered.at[row, reference]
                new_value = self.table.item(row, column).text()
        # everything else
        else:
            previous_value = self.data_filtered.at[row, reference]
            new_value = self.table.item(row, column).text()

        # add edit to stack
        edit = EditObject(rid=rid,
                          mid=media_id,
                          reference=reference,
                          previous_value=previous_value,
                          new_value=new_value)

        self.edit_stack.append(edit)
        self.update_signal.emit([row, column])  # update undo button in DisplayMedia
        self.apply_edits()
        self.refresh_table(popup=False)

    def add_edit_stack(self, edit_stack):
        """
        Add edits from popup to the edit stack and apply to current data_filtered
        Connected to DisplayMedia.edit_stack_signal
        """
        for edit in edit_stack:
            self.edit_stack.append(edit)
        self.apply_edits()
        self.refresh_table(popup=False)

    def save_changes(self):
        """Save all changes in the edit stack to the database"""
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
        self.clear_and_load_contents(self.data_type)

    def select_row(self, row, overwrite=None):
        """Select a specific row in the media table, optionally overwriting its current state"""
        select = self.table.item(row, 0)
        if overwrite is not None:
            if overwrite is True:
                select.setCheckState(Qt.CheckState.Checked)
                self.data_filtered.loc[row, 'select'] = 1
            else:
                select.setCheckState(Qt.CheckState.Unchecked)
                self.data_filtered.loc[row, 'select'] = 0
        else:
            self.invert_checkstate(select)
            self.data_filtered.loc[row, 'select'] = self.get_checkstate_int(select)

    def select_all(self, overwrite=False):
        """Select all rows in the media table, optionally overwriting their current state"""
        for row in range(self.table.rowCount()):
            self.select_row(row, overwrite=overwrite)

    def selectedRows(self):
        """Return a list of currently selected rows in the media table"""
        return self.data_filtered[self.data_filtered['select'].astype(bool)].index.tolist()

    def edit_row(self, row):
        """Edit a specific row in the media table by delegating to the parent"""
        self.parent.edit_row(row)
