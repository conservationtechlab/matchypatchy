"""
Widget for displaying list of Media
['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint', 'reviewed', 
'media_id', 'species_id', 'individual_id', 'emb_id', 'filepath', 'ext', 'timestamp', 
'station_id', 'sequence_id', 'external_id', 'comment', 'favorite', 'binomen', 'common', 'name', 'sex']
"""

import pandas as pd

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QLabel, QHeaderView, QAbstractItemView
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, pyqtSignal

from matchypatchy.algo import models
from matchypatchy.algo.thumbnail_thread import LoadThumbnailThread
from matchypatchy.database.media import fetch_media, fetch_roi_media
from matchypatchy.gui.popup_alert import ProgressPopup


class MediaTable(QWidget):
    update_signal = pyqtSignal(int, int)

    def __init__(self, parent):
        super().__init__(parent)
        self.mpDB = parent.mpDB
        self.parent = parent
        self.data = pd.DataFrame()
        self.thumbnails = dict()
        self.data_type = 1
        self.VIEWPOINT = models.load('VIEWPOINTS')

        self.edit_stack = []

        # Set up layout
        layout = QVBoxLayout()

        # Create QTableWidget
        self.table = QTableWidget()
        self.table.setColumnCount(15)  # Columns: Thumbnail, Name, and Description
        self.table.setHorizontalHeaderLabels(["Select","Thumbnail", "File Path", "Timestamp", 
                                              "Viewpoint", "Species", "Common", "Individual", "Sex", 
                                              "Station", "Sequence ID", "External ID", "Reviewed", "Favorite", "Comment"])
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, 100)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.verticalHeader().sectionClicked.connect(self.select_row)
        self.table.verticalHeader().sectionDoubleClicked.connect(self.edit_row)
        self.table.cellChanged.connect(self.update_entry)  # allow user editing

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
        # ROIS
        if self.data_type == 1:
            self.data = fetch_roi_media(self.mpDB, reset_index=False)
            # corresponding mpDB column names
            self.columns = ["select", "thumbnail", "filepath", "timestamp",
                            "station", "sequence_id", "external_id",
                            "viewpoint", "binomen", "common", "individual_id", "sex", 
                            "reviewed", "favorite", "comment"]
            self.table.setColumnCount(15)  
            self.table.setHorizontalHeaderLabels(["Select","Thumbnail", "File Path", "Timestamp",
                                                "Station", "Sequence ID", "External ID", 
                                                "Viewpoint", "Species", "Common", "Individual", "Sex",  
                                                "Reviewed", "Favorite", "Comment"])
            self.table.resizeColumnsToContents()
            self.table.setColumnWidth(1, 100)
        # MEDIA
        elif self.data_type == 0:
            self.data = fetch_media(self.mpDB)
            # corresponding mpDB column names
            self.columns = ["select", "thumbnail", "filepath", "timestamp",
                            "station", "sequence_id", "external_id", "favorite", "comment"]
            self.table.setColumnCount(9)  # Columns: Thumbnail, Name, and Description
            self.table.setHorizontalHeaderLabels( ["Select","Thumbnail", "File Path", "Timestamp", "Station",
                                                   "Sequence ID", "External ID", "Favorite", "Comment"])
            self.table.resizeColumnsToContents()
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
        # map 
        filters = self.parent.filters
        valid_stations = self.parent.valid_stations

        # Region Filter (depends on prefilterd stations from MediaDisplay)
        if 'region_filter' in filters.keys() and valid_stations:
            self.data_filtered = self.data_filtered[self.data_filtered['station_id'].isin(list(valid_stations.keys()))]
        # Survey Filter (depends on prefilterd stations from MediaDisplay)
        if 'survey_filter' in filters.keys() and valid_stations:
            self.data_filtered = self.data_filtered[self.data_filtered['station_id'].isin(list(valid_stations.keys()))]
        # Single station Filter
        if 'active_station' in filters.keys() and valid_stations:
            if filters['active_station'][0] > 0:
                self.data_filtered = self.data_filtered[self.data_filtered['station_id'] == filters['active_station'][0]]
            self.data_filtered['station'] = self.data_filtered['station_id'].map(valid_stations)
        else:
            # no valid stations, empty dataframe
            self.data_filtered.drop(self.data_filtered.index, inplace=True)

        # Species Filter
        if 'active_species' in filters.keys():
            if filters['active_species'][0] > 0:
                self.data_filtered = self.data_filtered[self.data_filtered['species_id'] == filters['active_species'][0]]
            elif filters['active_species'][0] is None: 
                self.data_filtered = self.data_filtered[self.data_filtered['species_id'].isna()]

        # Individual Filter
        if 'active_individual' in filters.keys():
            if filters['active_individual'][0] > 0:
                self.data_filtered = self.data_filtered[self.data_filtered['individual_id'] == filters['active_individual'][0]]
            elif filters['active_individual'][0] is None: 
                self.data_filtered = self.data_filtered[self.data_filtered['individual_id'].isna()]

        # Unidentified Filter
        if 'unidentified_only' in filters.keys():
            if filters['unidentified_only']:
                self.data_filtered = self.data_filtered[self.data_filtered['individual_id'].isna()]

        # Favorites Filter
        if 'favorites_only' in filters.keys():
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
        # include user edits to current data_filtered:
        self.apply_edits()
        # display data
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
        
        column_counter=0

        # Edit Checkbox
        edit = QTableWidgetItem()
        edit.setFlags(edit.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        edit.setCheckState(Qt.CheckState.Unchecked)
        self.table.setItem(i, column_counter, edit) 
        column_counter+=1

        # Thumbnail
        thumbnail = QImage(roi['thumbnail_path'])
        pixmap = QPixmap.fromImage(thumbnail)
        label = QLabel()
        label.setPixmap(pixmap)
        self.table.setCellWidget(i, column_counter, label)
        column_counter+=1
        
        # Data
        filepath = QTableWidgetItem(roi["filepath"])
        filepath.setFlags(filepath.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(i, column_counter, filepath)  # File Path column
        column_counter+=1

        self.table.setItem(i, column_counter, QTableWidgetItem(roi["timestamp"]))  # Date Time column
        column_counter+=1
        self.table.setItem(i, column_counter, QTableWidgetItem(roi["station"]))   # station column
        column_counter+=1
        self.table.setItem(i, column_counter, QTableWidgetItem(str(roi["sequence_id"])))  # Sequence ID column
        column_counter+=1
        self.table.setItem(i, column_counter, QTableWidgetItem(str(roi["external_id"])))  # External ID column
        column_counter+=1

        if self.data_type: # ADD ROI COLUMNS
            self.table.setItem(i, column_counter, QTableWidgetItem(self.VIEWPOINT[str(roi["viewpoint"])]))  # Viewpoint column
            column_counter+=1
            self.table.setItem(i, column_counter, QTableWidgetItem(roi["binomen"]))   # Taxon column
            column_counter+=1
            self.table.setItem(i, column_counter, QTableWidgetItem(roi["common"]))  # Species column
            column_counter+=1
            self.table.setItem(i, column_counter, QTableWidgetItem(roi["name"]))  # Individual ID column
            column_counter+=1
            self.table.setItem(i, column_counter, QTableWidgetItem(roi["sex"]))  # Sex column
            column_counter+=1

            reviewed = QTableWidgetItem()
            reviewed.setFlags(reviewed.flags() & Qt.ItemFlag.ItemIsUserCheckable)
            reviewed.setCheckState(self.set_check_state(roi["reviewed"]))
            self.table.setItem(i, column_counter, reviewed) 
            column_counter+=1
          
        # Favorite Checkbox
        favorite = QTableWidgetItem()
        favorite.setFlags(favorite.flags() & Qt.ItemFlag.ItemIsUserCheckable)
        favorite.setCheckState(self.set_check_state(roi["favorite"]))
        self.table.setItem(i, column_counter, favorite)  
        column_counter+=1

        # Comment
        self.table.setItem(i, column_counter, QTableWidgetItem(roi["comment"]))  # Favorite column

    def set_check_state(self, item):
        """
        Set the checkbox of reviewed and favorite columns
        when adding rows
        """
        if item:
            return Qt.CheckState.Checked
        else:
            return Qt.CheckState.Unchecked
        
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
        for edit in self.edit_stack:
            if not self.data_filtered.empty and self.data_filtered[self.id_col].isin([edit[0]]).any():
                self.data_filtered.loc[self.data_filtered[self.id_col] == edit[0], edit[1]] = edit[3]

    def update_entry(self, row, column): 
        """
        Allows user to edit entry in table 

        Save edits in queue, allow undo 
        prompt user to save edits 
        """
        reference = self.columns[column]
        rid = int(self.data_filtered.at[row, "id"])
        # tell parent
        self.update_signal.emit(row, column)

        if reference == 'select':
            return
        
        # checked items
        elif reference == 'reviewed' or reference == 'favorite':
            print(self.table.item(row, column).checkState())
            previous_value = self.set_check_state(self.data_filtered.at[row, reference])
            new_value = self.table.item(row, column).checkState()

        # everything else
        else:
            previous_value = self.data_filtered.at[row, reference]
            new_value = self.table.item(row, column).text()
            
        # add edit to stack
        edit = [rid, reference, previous_value, new_value]
        self.edit_stack.append(edit)

    def undo(self):
        """
        Undo last edit and refresh table
        """
        if len(self.edit_stack) > 0:
            last = self.edit_stack.pop()
            self.data_filtered.at[last[0], last[1]] = last[2]
            self.refresh_table()

    # TODO
    def save_changes(self):
        # commit all changes in self.edit_stack to database
        for edit in self.edit_stack:
            id = edit[0]
            replace_dict = {edit[1]: edit[3]}
            if self.data_type == 1:
                #self.mpDB.edit_row("roi", edit[0], replace_dict, allow_none=False, quiet=True)
                pass
            else:
                #self.mpDB.edit_row("media", edit[0], replace_dict, allow_none=False, quiet=True)
                pass

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
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked:
                selected_rows.append(row)
        return selected_rows

     # TODO
    def edit_row(self, row):
        print('edit')
        rid = int(self.data_filtered.at[row, "id"])
        self.parent.edit_row(rid, self.data_type)