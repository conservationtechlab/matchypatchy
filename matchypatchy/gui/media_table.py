"""
Widget for displaying list of Media
['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint', 'reviewed', 
'media_id', 'species_id', 'individual_id', 'emb_id', 'filepath', 'ext', 'timestamp', 
'station_id', 'sequence_id', 'external_id', 'comment', 'favorite', 'binomen', 'common', 'name', 'sex', 'age']
"""
import pandas as pd

from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, 
                             QComboBox, QLabel, QHeaderView, QStyledItemDelegate)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, pyqtSignal

from matchypatchy.algo import models
from matchypatchy.algo.thumbnail_thread import LoadThumbnailThread
from matchypatchy.database.media import fetch_media, fetch_roi_media
from matchypatchy.database.species import fetch_species, fetch_individual
from matchypatchy.gui.popup_alert import ProgressPopup


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
        self.data_type = 1
        self.VIEWPOINTS = models.load('VIEWPOINTS')

        self.edit_stack = []

        # Set up layout
        layout = QVBoxLayout()

        # Create QTableWidget
        self.table = QTableWidget()
        self.table.setColumnCount(15)  # Columns: Thumbnail, Name, and Description
        self.table.setHorizontalHeaderLabels(["Select","Thumbnail", "File Path", "Timestamp", 
                                              "Station", "Sequence ID", "External ID",
                                              "Viewpoint", "Species", "Common", "Individual", "Sex", "Age"
                                              "Reviewed", "Favorite", "Comment"])
        #self.table.setSortingEnabled(True)  # NEED TO FIGURE OUT HOW TO SORT data_filtered FIRST
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.verticalHeader().sectionClicked.connect(self.select_row)
        self.table.verticalHeader().sectionDoubleClicked.connect(self.edit_row)
        self.table.cellChanged.connect(self.update_entry)  # allow user editing
        
        self.table.cellChanged.connect(self.handle_checkbox_change) #select change 

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
            # corresponding mpDB column names
            self.columns = {0: "select", 1:"thumbnail", 
                            2:"filepath", 3:"timestamp",
                            4:"station", 5:"sequence_id", 
                            6:"external_id", 7:"viewpoint", 
                            8:"binomen", 9:"common", 
                            10:"name", 11:"sex", 12:"age",
                            13:"reviewed", 14:"favorite", 15:"comment"}
            self.table.setColumnCount(15)  
            self.table.setHorizontalHeaderLabels(["Select","Thumbnail", "File Path", "Timestamp",
                                                "Station", "Sequence ID", "External ID", 
                                                "Viewpoint", "Species", "Common", "Individual", "Sex", "Age",
                                                "Reviewed", "Favorite", "Comment"])
            # adjust widths
            self.table.resizeColumnsToContents()
            for col in range(self.table.columnCount()):
                self.table.setColumnWidth(col, max(self.table.columnWidth(col), 50))
            self.table.setColumnWidth(1, 100)

            # VIEWPOINT COMBOS
            combo_items = list(self.VIEWPOINTS.values())[1:]
            self.table.setItemDelegateForColumn(7, ComboBoxDelegate(combo_items, self))

            # SPECIES COMBOBOX
            if not self.species_list.empty:
                combo_items = [None] + self.species_list['binomen'].str.capitalize().to_list()
                self.table.setItemDelegateForColumn(8, ComboBoxDelegate(combo_items, self))
                combo_items = [None] + self.species_list['common'].str.capitalize().to_list()
                self.table.setItemDelegateForColumn(9, ComboBoxDelegate(combo_items, self))

            # SEX COMBOBOX
            combo_items = ['Unknown', 'Male', 'Female']
            self.table.setItemDelegateForColumn(11, ComboBoxDelegate(combo_items, self))

            # AGE COMBOBOX
            combo_items = ['Unknown', 'Juvenile', 'Subadult', 'Adult']
            self.table.setItemDelegateForColumn(12, ComboBoxDelegate(combo_items, self))

        # MEDIA
        elif self.data_type == 0:
            self.data = fetch_media(self.mpDB)
            # corresponding mpDB column names
            self.columns = {0:"select", 1:"thumbnail", 
                            2:"filepath", 3:"timestamp",
                            4:"station", 5:"sequence_id", 
                            6:"external_id", 7:"favorite", 8:"comment"}
            self.table.setColumnCount(9)  # Columns: Thumbnail, Name, and Description
            self.table.setHorizontalHeaderLabels( ["Select","Thumbnail", "File Path", "Timestamp", "Station",
                                                   "Sequence ID", "External ID", "Favorite", "Comment"])
            
            # adjust widths
            self.table.resizeColumnsToContents()
            for col in range(self.table.columnCount()):
                self.table.setColumnWidth(col, max(self.table.columnWidth(col), 50))
            self.table.setColumnWidth(1, 100)
            
        else:
            # return empty
            self.data = pd.DataFrame()
    
    # STEP 3 - CALLED BY MAIN GUI IF DATA FOUND
    def load_images(self):
        """
        Load images if data is available
        Does not run if load_data returns false to MediaDisplay
        """
        self.loading_bar = ProgressPopup(self, "Loading images...")
        self.loading_bar.show()
        self.image_loader_thread = LoadThumbnailThread(self.mpDB, self.data, self.data_type)
        self.image_loader_thread.progress_update.connect(self.loading_bar.set_counter)
        self.image_loader_thread.loaded_image.connect(self.add_thumbnail_path)
        self.image_loader_thread.finished.connect(self.filter)
        self.image_loader_thread.start()

    # STEP 4 - Triggered by load_images() finishing
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

        # Species Filter
        if filters['active_species'][0] > 0:
            self.data_filtered = self.data_filtered[self.data_filtered['species_id'] == filters['active_species'][0]]
        elif filters['active_species'][0] is None: 
            self.data_filtered = self.data_filtered[self.data_filtered['species_id'].isna()]

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

    def refresh_table(self):
        """
        Add rows to table
        """
        # clear old contents and prep for filtered data
        self.table.clearContents()
        # disconnect edit function while refreshing to prevent needless calls
        self.table.blockSignals(True) 
        # display data
        #print(f"data filtered is {self.data_filtered['viewpoint']}")
        self.table.setRowCount(self.data_filtered.shape[0])
        for i in range(self.data_filtered.shape[0]):
            self.add_row(i)
        self.table.blockSignals(False)  # reconnect editing
        
    # Set Table Entries --------------------------------------------------------
    def add_row(self, i):
        """
        Adds Row to Table with Items from self.data_filtered
        """
        roi = self.data_filtered.iloc[i]
        self.table.setRowHeight(i, 100)
        
        for column, data in self.columns.items():
             # Edit Checkbox
            if data == 'select':
                edit = QTableWidgetItem()
                edit.setFlags(edit.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                edit.setCheckState(Qt.CheckState.Unchecked)
                self.table.setItem(i, column, edit) 
        
            # Thumbnail
            elif data == 'thumbnail':
                thumbnail = QImage(roi['thumbnail_path'])
                pixmap = QPixmap.fromImage(thumbnail)
                label = QLabel()
                label.setPixmap(pixmap)
                self.table.setCellWidget(i, column, label)
            # FilePath and Timestamp not editable
            elif data == 'filepath' or data == 'timestamp':
                noedit = QTableWidgetItem(roi[data])
                noedit.setFlags(noedit.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i, column, noedit)
            # Station
            elif data == 'station':
                self.table.setItem(i, column, QTableWidgetItem(self.valid_stations[roi["station_id"]]))
            # Viewpoint
            elif data == 'viewpoint':
                vp_raw = roi["viewpoint"]
                print(f"vp_raw is {vp_raw}")

                if pd.isna(vp_raw) or vp_raw is None or str(vp_raw) == "None":
                    vp_key = "None"
                else:
                    vp_key = str(int(vp_raw))  # convert float 1.0 → int 1 → str "1"

                vp_value = self.VIEWPOINTS.get(vp_key, "None")
                self.table.setItem(i, column, QTableWidgetItem(vp_value))


            # Species ID
            elif data == 'binomen' or data == 'common':
                if self.species_list.empty:
                    # can't edit if no species in table
                    noedit = QTableWidgetItem()
                    noedit.setFlags(noedit.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(i, column, noedit)
                else:
                    if roi['species_id'] is not None:
                        species = self.species_list[self.species_list['id'] == roi['species_id']]
                        self.table.setItem(i, column, QTableWidgetItem(species[data][0]))
                    else:
                        self.table.setItem(i, column, QTableWidgetItem(None))

            elif data == "name" or data == "sex" or data == 'age':
                if roi['individual_id'] is not None:
                    individual = self.individual_list[self.individual_list['id'] == roi['individual_id']]
                    self.table.setItem(i, column, QTableWidgetItem(individual[data][0]))
                else:
                    self.table.setItem(i, column, QTableWidgetItem(None))

            # Reviewed and Favorite Checkbox
            elif data == 'reviewed' or data == 'favorite':
                qtw = QTableWidgetItem()
                qtw.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                qtw.setCheckState(self.set_checkstate(roi[data]))
                self.table.setItem(i, column, qtw) 
            else:
                self.table.setItem(i, column, QTableWidgetItem(str(roi[data]))) 

        # combo delegates
        delegate = ComboBoxDelegate(list(self.valid_stations.values()), self)
        self.table.setItemDelegateForColumn(4, delegate)


    def set_checkstate(self, item):
        """
        Set the checkbox of reviewed and favorite columns
        when adding rows
        """
        if item:
            return Qt.CheckState.Checked
        else:
            return Qt.CheckState.Unchecked
        
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

    # captures emitted temp thumbnail path to data, saves to table
    def add_thumbnail_path(self, i, thumbnail_path):
        self.data.loc[i,'thumbnail_path'] = thumbnail_path


    # UPDATE ENTRIES -----------------------------------------------------------
    def apply_edits(self):
        """
        Applies all previous edits to the current data_filter if the row is present
        """
        #print(self.edit_stack)
        for edit in self.edit_stack:
            if not self.data_filtered.empty and self.data_filtered['id'].isin([edit['id']]).any():
                self.data_filtered.loc[edit['row'], edit['reference']] = edit['new_value']

    def handle_checkbox_change(self, row, column):
        """ Detect when a checkbox is checked or unchecked """
        if column == 0: 
            item = self.table.item(row, column)
            if item is not None:
                checked = item.checkState() == Qt.CheckState.Checked
                print(f"Checkbox at row {row} is {'checked' if checked else 'unchecked'}")
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
            print("DataFrame columns:", self.data_filtered.columns)
            previous_value = int(self.data_filtered.at[row, reference])
            print(f'previous_value is {previous_value}')
            new_value = self.get_checkstate_int(self.table.item(row, column).checkState())
            print(new_value)
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

        elif reference ==  'binomen':
            reference = 'species_id'
            previous_value = self.data_filtered.at[row, reference]
            new = self.table.item(row, column).text()
            if new is None:
                new_value = None
            else:
                new_value = self.species_list.loc[self.species_list['binomen'] == new, 'id'][0]
    
        # everything else
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
        self.refresh_table()


    def undo(self):
        """
        Undo last edit and refresh table
        """
        if len(self.edit_stack) > 0:
            last = self.edit_stack.pop()
            self.data_filtered.loc[last['row'], last['reference']] = last['previous_value']
            self.refresh_table()

    def save_changes(self):
        # commit all changes in self.edit_stack to database
        for edit in self.edit_stack:
            print(edit)
            id = edit['id']
            replace_dict = {edit['reference']: edit['new_value']}
            if self.data_type == 1:
                self.mpDB.edit_row("roi", id, replace_dict, allow_none=False, quiet=False)
            else:    
                self.mpDB.edit_row("media", id, replace_dict, allow_none=False, quiet=False)
                pass

    def select_row(self, row, overwrite=None):
        select = self.table.item(row, 0)
        print("select row")
        if overwrite is not None:
            if overwrite is True:
                select.setCheckState(Qt.CheckState.Checked)
            else:
                select.setCheckState(Qt.CheckState.Unchecked)
        else:
            self.invert_checkstate(select)

    def selectedRows(self):
        print("selectedRows called")
        selected_rows = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked:
                selected_rows.append(row)
        return selected_rows

    def edit_row(self, row):
        rid = int(self.data_filtered.at[row, "id"])
        self.parent.edit_row(rid)


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