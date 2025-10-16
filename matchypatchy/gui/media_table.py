"""
Widget for displaying list of Media
"""
import pandas as pd

from PyQt6.QtWidgets import (QTableWidget, QVBoxLayout, QWidget, QComboBox,
                             QLabel, QHeaderView, QStyledItemDelegate)

from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal

from matchypatchy.algo import models
from matchypatchy.algo.thumbnail_thread import LoadThumbnailThread
from matchypatchy.algo.table_thread import LoadTableThread
from matchypatchy.database.media import fetch_media, fetch_roi_media
from matchypatchy.database.species import fetch_species, fetch_individual
from matchypatchy.gui.popup_alert import AlertPopup


class MediaTable(QWidget):
    update_signal = pyqtSignal(list)

    def __init__(self, parent):
        super().__init__(parent)
        self.mpDB = parent.mpDB
        self.parent = parent
        self.data = pd.DataFrame()
        self.species_list = pd.DataFrame()
        self.individual_list = pd.DataFrame()
        self.thumbnails = dict()
        self.image_loader_thread = None
        self.data_type = 1
        self.VIEWPOINTS = models.load('VIEWPOINTS')

        self.edit_stack = []

        # Set up layout
        layout = QVBoxLayout()

        # Create QTableWidget
        self.table = QTableWidget()
        self.table.setColumnCount(17)  # Columns: Thumbnail, Name, and Description
        self.table.setHorizontalHeaderLabels(["Select", "Thumbnail", "File Path", "Timestamp",
                                              "Station", "Camera", "Sequence ID", "External ID",
                                              "Viewpoint", "Species", "Common", "Individual", "Sex", "Age",
                                              "Reviewed", "Favorite", "Comment"])
        # self.table.setSortingEnabled(True)  # NEED TO FIGURE OUT HOW TO SORT data_filtered FIRST
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.verticalHeader().sectionDoubleClicked.connect(self.edit_row)
        self.table.cellChanged.connect(self.update_entry)  # allow user editing
        self.table.cellChanged.connect(self.handle_checkbox_change)  # select change
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        # Add table to the layout
        layout.addWidget(self.table)
        self.setLayout(layout)

        # Connect table.cellchanged to parent
        self.update_signal.connect(parent.handle_table_change)

    # RUN ON ENTRY -------------------------------------------------------------
    def load_data(self, data_type):
        """
        Fetch table, load images and save as thumbnails to TEMP_DIR
        """
        # clear old view
        self.data_type = data_type
        self.table.clearContents()
        # fetch data
        self.fetch()
        self.format_table()
        if not self.data.empty:
            return True
        else:
            # no media, give warning, go home
            return False

    # STEP 2 - CALLED BY load_data()
    def fetch(self):
        """
        Select all media, store in dataframe
        """
        self.species_list = fetch_species(self.mpDB)
        self.individual_list = fetch_individual(self.mpDB)
        # ROIS
        if self.data_type == 1:
            self.data = fetch_roi_media(self.mpDB, reset_index=False)
        # MEDIA
        elif self.data_type == 0:
            self.data = fetch_media(self.mpDB)
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
                            9: "binomen",
                            10: "common",
                            11: "name",
                            12: "sex",
                            13: "age",
                            14: "reviewed",
                            15: "favorite",
                            16: "comment"}

            self.table.setColumnCount(17)
            self.table.setHorizontalHeaderLabels(["Select", "Thumbnail", "File Path", "Timestamp",
                                                  "Station", "Camera", "Sequence ID", "External ID",
                                                  "Viewpoint", "Species", "Common", "Individual", "Sex", "Age",
                                                  "Reviewed", "Favorite", "Comment"])
            # adjust widths
            self.table.resizeColumnsToContents()
            for col in range(self.table.columnCount()):
                self.table.setColumnWidth(col, max(self.table.columnWidth(col), 50))
            self.table.setColumnWidth(1, 100)

            # VIEWPOINT COMBOS
            combo_items = list(self.VIEWPOINTS.values())[1:]
            self.table.setItemDelegateForColumn(8, ComboBoxDelegate(combo_items, self))

            # SPECIES COMBOBOX
            if not self.species_list.empty:
                combo_items = [None] + self.species_list['binomen'].str.capitalize().to_list()
                self.table.setItemDelegateForColumn(9, ComboBoxDelegate(combo_items, self))
                combo_items = [None] + self.species_list['common'].str.capitalize().to_list()
                self.table.setItemDelegateForColumn(10, ComboBoxDelegate(combo_items, self))

            # SEX COMBOBOX
            combo_items = ['Unknown', 'Male', 'Female']
            self.table.setItemDelegateForColumn(12, ComboBoxDelegate(combo_items, self))

            # AGE COMBOBOX
            combo_items = ['Unknown', 'Juvenile', 'Subadult', 'Adult']
            self.table.setItemDelegateForColumn(13, ComboBoxDelegate(combo_items, self))

        # MEDIA
        elif self.data_type == 0:
            # corresponding mpDB column names
            self.columns = {0: "select",
                            1: "thumbnail",
                            2: "filepath",
                            3: "timestamp",
                            4: "station",
                            5: "camera",
                            6: "sequence_id",
                            7: "external_id",
                            8: "favorite",
                            9: "comment"}
            self.table.setColumnCount(10)  # Columns: Thumbnail, Name, and Description
            self.table.setHorizontalHeaderLabels(["Select", "Thumbnail", "File Path", "Timestamp",
                                                  "Station", "Camera", "Sequence ID",
                                                  "External ID", "Favorite", "Comment"])
            # adjust widths
            self.table.resizeColumnsToContents()
            for col in range(self.table.columnCount()):
                self.table.setColumnWidth(col, max(self.table.columnWidth(col), 50))
            self.table.setColumnWidth(1, 100)

    # STEP 4 - CALLED BY MAIN GUI IF DATA FOUND
    def load_images(self):
        """
        Load images if data is available
        Does not run if load_data returns false to MediaDisplay
        """
        loading_bar = AlertPopup(self, "Loading images...", progressbar=True, cancel_only=True)
        loading_bar.show()
        self.image_loader_thread = LoadThumbnailThread(self.mpDB, self.data, self.data_type)
        self.image_loader_thread.progress_update.connect(loading_bar.set_counter)
        self.image_loader_thread.loaded_images.connect(self.add_thumbnail_paths)
        self.image_loader_thread.done.connect(self.filter)

        loading_bar.rejected.connect(self.image_loader_thread.requestInterruption)
        self.image_loader_thread.start()

        # captures emitted temp thumbnail path to data, saves to table
    def add_thumbnail_paths(self, thumbnail_paths):
        self.data = pd.merge(self.data, pd.DataFrame(thumbnail_paths, columns=["id", "thumbnail_path"]), on="id")

    # STEP 5 - Triggered by load_images() finishing
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
        # map
        filters = self.parent.filters
        self.valid_stations = self.parent.valid_stations
        self.valid_cameras = self.parent.valid_cameras

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

        # refresh table contents
        self.refresh_table()

    def refresh_table(self, popup=True):
        """
        Add rows to table
        """
        self.data_filtered.reset_index(drop=True, inplace=True)
        n_rows = self.data_filtered.shape[0]

        # clear old contents and prep for filtered data
        self.table.clearContents()
        # disconnect edit function while refreshing to prevent needless calls
        self.table.setRowCount(n_rows)
        for row in range(n_rows):
            self.table.setRowHeight(row, 100)

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
        Adds Row to Table with Items from self.data_filtered
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
        if (item == Qt.CheckState.Checked):
            return 1
        else:
            return 0

    def invert_checkstate(self, item):
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

    # UPDATE CELL ENTRY
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

        # species
        elif reference == 'common':
            reference = 'species_id'
            previous_value = self.data_filtered.at[row, reference]
            new = self.table.item(row, column).text()
            if new is None:
                new_value = None
            else:
                new_value = self.species_list.loc[self.species_list['common'] == new, 'id'][0]
        elif reference == 'binomen':
            reference = 'species_id'
            previous_value = self.data_filtered.at[row, reference]
            new = self.table.item(row, column).text()
            if new is None:
                new_value = None
            else:
                new_value = self.species_list.loc[self.species_list['binomen'] == new, 'id'][0]

        # individual
        elif reference == 'name' or reference == 'sex' or reference == 'age':
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
                elif edit['reference'] in {'name', 'age', 'sex'}:
                    self.mpDB.edit_row("individual", id, replace_dict, allow_none=False, quiet=False)
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


# COMBOBOX FOR VIEWPOINT, SPECIES, SEX
class ComboBoxDelegate(QStyledItemDelegate):
    """Custom delegate to use QComboBox for editing"""
    itemSelected = pyqtSignal(int, int, int)

    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items  # ComboBox items

    def createEditor(self, parent, option, index):
        """Create and return the ComboBox editor"""
        combo = QComboBox(parent)
        combo.addItems(self.items)
        return combo

    def setEditorData(self, editor, index):
        """Set the current value in the editor"""
        current_text = index.data()
        combo_index = editor.findText(current_text)  # Find matching index
        if combo_index >= 0:
            editor.setCurrentIndex(combo_index)

    def setModelData(self, editor, model, index):
        """Save the selected value to the model"""
        selected_text = editor.currentText()
        selected_index = editor.currentIndex()  # 🔥 Get the current index
        self.itemSelected.emit(index.row(), index.column(), selected_index)

        # Save selected text in table model
        model.setData(index, selected_text)
