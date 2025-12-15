"""
Widget for displaying list of Media
"""
import pandas as pd

from PyQt6.QtWidgets import (QTableWidget, QVBoxLayout, QWidget, QLabel, QHeaderView)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal

from matchypatchy.algo.models import load_model
from matchypatchy.algo.table_thread import LoadTableThread
from matchypatchy.database.media import fetch_media, fetch_roi_media, fetch_individual
from matchypatchy.database.thumbnails import fetch_media_thumbnails, fetch_roi_thumbnails
from matchypatchy.gui.popup_alert import AlertPopup
from matchypatchy.gui.gui_assets import ComboBoxDelegate


class MediaTable(QWidget):
    update_signal = pyqtSignal(list)

    def __init__(self, parent):
        super().__init__(parent)
        self.mpDB = parent.mpDB
        self.parent = parent
        self.data = pd.DataFrame()
        self.data_filtered = pd.DataFrame()
        self.individual_list = pd.DataFrame()
        self.thumbnails = dict()
        self.data_type = 1
        self.VIEWPOINTS = load_model('VIEWPOINTS')
        self.thumbnail_size = 150

        self.edit_stack = []

        # Set up layout
        layout = QVBoxLayout()
        # Create QTableWidget
        self.table = QTableWidget()
        self.table.setColumnCount(17)  # Columns: Thumbnail, Name, and Description
        self.table.setHorizontalHeaderLabels(["Select", "Thumbnail", "Filepath", "Timestamp",
                                              "Station", "Camera", "Sequence ID", "External ID",
                                              "Viewpoint", "Individual", "Sex", "Age",
                                              "Reviewed", "Favorite", "Comment"])
        # self.table.setSortingEnabled(True)  # TODO: NEED TO FIGURE OUT HOW TO SORT data_filtered FIRST
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.verticalHeader().sectionDoubleClicked.connect(self.edit_row)
        self.table.cellChanged.connect(self.update_entry)  # allow user editing
        self.table.cellChanged.connect(self.handle_checkbox_change)  # select change
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        # Add table to the layout
        layout.addWidget(self.table)
        self.setLayout(layout)

        # Connect table.cellchanged to Media View
        self.update_signal.connect(parent.handle_table_change)

    # RUN ON ENTRY -------------------------------------------------------------
    def load_data(self, data_type):
        """
        Fetch table, format, and filter data
        data_type: 0 = media, 1 = rois
        Returns True if data loaded, False if no media
        """
        # clear old view
        self.data_type = data_type
        self.table.clearContents()
        # fetch data
        self.fetch()
        self.format_table()
        if not self.data.empty:
            self.filter()
            return True
        else:
            # no media, give warning, go home
            return False

    # STEP 2 - CALLED BY load_data()
    def fetch(self):
        """
        Select all media, store in dataframe
        Merge with thumbnails table
        """
        self.individual_list = fetch_individual(self.mpDB)
        # TODO check missing thumbnails
        # ROIS
        if self.data_type == 1:
            self.data = fetch_roi_media(self.mpDB, reset_index=False)
            self.thumbnails = fetch_roi_thumbnails(self.mpDB)
            self.data = pd.merge(self.data, self.thumbnails, on="id")
        # MEDIA
        elif self.data_type == 0:
            self.data = fetch_media(self.mpDB)
            self.thumbnails = fetch_media_thumbnails(self.mpDB)
            self.data = pd.merge(self.data, self.thumbnails, on="id")
        # return empty
        else:
            self.data = pd.DataFrame()

    # STEP 3 - CALLED BY load_data()
    def format_table(self):
        if self.data_type == 1:
            # corresponding mpDB column names
            self.columns = {0: "select",
                            1: "thumbnail",
                            2: "filepath",
                            3: "timestamp",
                            4: "station",
                            5: "camera",
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
            VIEWPOINT_COLUMN = 8
            SEX_COLUMN = 10
            AGE_COLUMN = 11
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
                            5: "camera",
                            6: "sequence_id",
                            7: "external_id",
                            8: "comment"}
            self.table.setColumnCount(len(self.columns))  # Columns: Thumbnail, Name, and Description
            self.table.setHorizontalHeaderLabels(["Select", "Thumbnail", "Filepath", "Timestamp",
                                                  "Station", "Camera", "Sequence ID",
                                                  "External ID", "Comment"])
        # adjust widths
        self.table.resizeColumnsToContents()
        for col in range(self.table.columnCount()):
            if col == 0:  # select
                self.table.setColumnWidth(0, 40)
            elif col == 1:  # thumbnail
                self.table.setColumnWidth(col, max(self.table.columnWidth(col), self.thumbnail_size))
            else:
                self.table.setColumnWidth(col, max(self.table.columnWidth(col), 80))

    def filter(self):
        """
        Filter media based on active survey selected in dropdown of DisplayMedia
        Always run before updating table

        if filter > 0 : use id
        if filter == 0: do not filter
        if filter is None: select None
        """
        # create new copy of full dataset
        self.data_filtered = self.data.copy()
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

        self.data_filtered.reset_index(inplace=True)
        # refresh table contents
        self.refresh_table()

    # triggered by filter() finishing
    def refresh_table(self, popup=True):
        """
        Add rows to table by creating LoadTableThread to generate QTableWidgetItems
        """
        # clear old contents and prep for filtered data
        self.table.clearContents()
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

            self.table_loader_thread = LoadTableThread(self)
            self.table_loader_thread.loaded_cell.connect(self.add_cell)
            self.table_loader_thread.done.connect(lambda: self.table.blockSignals(False))

            if popup:
                loading_bar = AlertPopup(self, "Loading data...", progressbar=True, cancel_only=True)
                loading_bar.set_max(n_rows)
                self.table_loader_thread.progress_update.connect(loading_bar.set_counter)
                loading_bar.rejected.connect(self.table_loader_thread.requestInterruption)
                loading_bar.show()

            self.table_loader_thread.start()

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
        if (item == Qt.CheckState.Checked):
            return 1
        else:
            return 0

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
        for edit in self.edit_stack:
            self.data_filtered.loc[edit['row'], edit['reference']] = edit['new_value']

    def handle_checkbox_change(self, row, column):
        """ Detect when a checkbox is checked or unchecked """
        if column == 0:
            item = self.table.item(row, column)
            if item is not None:
                checked = item.checkState() == Qt.CheckState.Checked
                self.select_row(row, overwrite=checked)
                self.parent.check_selected_rows()

    def update_entry(self, row, column):
        """
        Allows user to edit entry in table

        Save edits in queue, allow undo
        prompt user to save edits
        """
        reference = self.columns[column]
        rid = int(self.data_filtered.at[row, "id"])

        if reference == 'select':
            return
        # checked items
        elif reference == 'reviewed' or reference == 'favorite':
            previous_value = int(self.data_filtered.at[row, reference])
            new_value = self.get_checkstate_int(self.table.item(row, column).checkState())
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
        elif reference == 'individual_id' or reference == 'sex' or reference == 'age':
            rid = self.data_filtered.at[row, 'individual_id']
            if rid is None:
                dialog = AlertPopup(self, "Please tag the ROI with an individual first.")
                if dialog.exec():
                    del dialog
                    self.apply_edits()
                    self.refresh_table(popup=False)
                    return
            else:
                previous_value = self.data_filtered.at[row, reference]
                new_value = self.table.item(row, column).text()

        else:
            previous_value = self.data_filtered.at[row, reference]
            new_value = self.table.item(row, column).text()

        # add edit to stack
        edit = {'row': row,
                'column': column,
                'id': rid,
                'reference': reference,
                'previous_value': previous_value,
                'new_value': new_value}
        self.edit_stack.append(edit)
        self.update_signal.emit([row, column])
        self.apply_edits()
        self.refresh_table(popup=False)

    def transpose_edit_stack(self, edit_stack):
        """
        Transpose edit stack from popup_roi to media_table format
        """
        for edit in edit_stack:
            print(edit)
            id = edit['id']
            row = self.data_filtered.index[self.data_filtered['id'] == id].tolist()
            column = list(self.columns.keys())[list(self.columns.values()).index(edit['reference'])]
            if row:
                row = row[0]
                new_edit = {'row': row,
                            'column': column,
                            'id': id,
                            'reference': edit['reference'],
                            'previous_value': edit['previous_value'],
                            'new_value': edit['new_value']}
                print(new_edit)
                self.edit_stack.append(new_edit)

    def undo(self):
        """
        Undo last edit and refresh table
        """
        # TODO: handle multiple selection edits as one undo
        if len(self.edit_stack) > 0:
            last = self.edit_stack.pop()
            self.data_filtered.loc[last['row'], last['reference']] = last['previous_value']
            self.refresh_table(popup=False)

    def save_changes(self):
        # commit all changes in self.edit_stack to database
        while len(self.edit_stack) > 0:
            edit = self.edit_stack.pop()
            id = edit['id']
            replace_dict = {edit['reference']: edit['new_value']}
            if self.data_type == 1:
                if edit['reference'] in {'station_id', 'sequence_id', 'external_id'}:
                    self.mpDB.edit_row("media", id, replace_dict, allow_none=False, quiet=False)
                elif edit['reference'] in {'age', 'sex'}:
                    iid = self.data_filtered.loc[self.data_filtered['id'] == id, 'individual_id'].values[0]
                    iid = int(iid) if pd.notna(iid) else None
                    if iid is not None:
                        self.mpDB.edit_row("individual", iid, replace_dict, allow_none=False, quiet=False)
                elif edit['reference'] in {'comment'}:
                    self.mpDB.edit_row("media", id, replace_dict, allow_none=True, quiet=False)
                else:
                    self.mpDB.edit_row("roi", id, replace_dict, allow_none=False, quiet=False)
            else:
                self.mpDB.edit_row("media", id, replace_dict, allow_none=False, quiet=False)

    def select_row(self, row, overwrite=None):
        select = self.table.item(row, 0)
        if overwrite is not None:
            if overwrite is True:
                select.setCheckState(Qt.CheckState.Checked)
            else:
                select.setCheckState(Qt.CheckState.Unchecked)
        else:
            self.invert_checkstate(select)

    def selectedRows(self):
        selected_rows = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                selected_rows.append(row)
        return selected_rows

    def edit_row(self, row):
        self.parent.edit_row(row)
