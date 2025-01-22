"""
Widget for displaying list of Media
['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint', 'reviewed', 
'media_id', 'species_id', 'individual_id', 'emb_id', 'filepath', 'ext', 'timestamp', 
'station_id', 'sequence_id', 'external_id', 'comment', 'favorite', 'binomen', 'common', 'name', 'sex']
"""

# TODO: MAKE TABLE EDITABLE
# TODO: KEEP QUEUE OF EDITS, UNDOABLE, COMMIT SAVE OR RETURN
# TODO: keep track of thumbnails


import pandas as pd

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QLabel, QHeaderView
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt

from matchypatchy.algo import models
from matchypatchy.algo.thumbnail_thread import LoadThumbnailThread
from matchypatchy.database.media import fetch_media
from matchypatchy.gui.popup_alert import ProgressPopup


class MediaTable(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.mpDB = parent.mpDB
        self.parent = parent
        self.data = pd.DataFrame()
        self.thumbnails = dict()
        self.crop = True
        self.VIEWPOINT = models.load('VIEWPOINT')

        self.edit_stack = []

        self.edits = list()
        self.columns = ["reviewed","thumbnail", "filepath", "timestamp", 
                        "viewpoint", "binomen", "common", "individual_id", "sex", 
                        "station", "sequence_id", "external_id", "favorite", "comment"]
        # Set up layout
        layout = QVBoxLayout()

        # Create QTableWidget
        self.table = QTableWidget()
        self.table.setColumnCount(14)  # Columns: Thumbnail, Name, and Description
        self.table.setHorizontalHeaderLabels(["Reviewed","Thumbnail", "File Path", "Timestamp", 
                                              "Viewpoint", "Species", "Common", "Individual", "Sex", 
                                              "Station", "Sequence ID", "External ID", "Favorite", "Comment"])
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, 100)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSortingEnabled(True)
        self.table.itemChanged.connect(self.update_entry)  # allow user editing

        # Add table to the layout
        layout.addWidget(self.table)
        self.setLayout(layout)


    # RUN ON ENTRY -------------------------------------------------------------
    def load_data(self):
        """
        Fetch table, load images and save as thumbnails to TEMP_DIR
        """
        # clear old view
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
        roi_n = self.mpDB.count('roi')        
        if roi_n > 0:
            media, column_names = self.mpDB.all_media()
            self.data = pd.DataFrame(media, columns=column_names)  
            self.crop = True
            self.id_col = 'roi.id'
            
        # no rois processed, default to full image
        else:
            self.data = fetch_media(self.mpDB)
            self.data = self.data.assign(reviewed=0, binomen=None, common=None, viewpoint=None,
                                        name=None, sex=None, individual_id=0)
            self.crop = False  # display full image
            self.id_col = 'id'
    
    # STEP 3 - CALLED BY MAIN GUI IF DATA FOUND
    def load_images(self):
        """
        Load images if data is available
        Does not run if load_data returns false to MediaDisplay
        """
        self.loading_bar = ProgressPopup(self, "Loading images...")
        self.loading_bar.show()
        self.image_loader_thread = LoadThumbnailThread(self.data, self.crop)
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
       
    # UPDATE ENTRIES -----------------------------------------------------------
    def apply_edits(self):
        """
        Applies all previous edits to the current data_filter if the row is present
        """
        for edit in self.edit_stack:
            if not self.data_filtered.empty and self.data_filtered[self.id_col].isin([edit[0]]).any():
                self.data_filtered.loc[self.data_filtered[self.id_col] == edit[0], edit[1]] = edit[3]

    def update_entry(self, item): 
        """
        Allows user to edit entry in table 

        Save edits in queue, allow undo 
        prompt user to save edits 
        """
        entry = item.row()  # refers to filtered dataframe, can change if refiltered
        reference = self.columns[item.column()]
        id = int(self.data_filtered.at[entry, self.id_col])
        # get unfiltered id
        
        # checked items
        if reference == 'reviewed' or reference == 'favorite':
            print(item.checkState())
            previous_value = self.set_check_state(self.data_filtered.at[entry, reference])
            new_value = item.checkState()

        # everything else
        else:
            previous_value = self.data_filtered.at[entry, reference]
            new_value = item.text()
            
        # add edit to stack
        edit = [id, reference, previous_value, new_value]
        self.edit_stack.append(edit)

    # TODO
    def update_row(self):
        pass

    # TODO
    def update_column(self):
        pass   

    def undo(self):
        # id, entry, reference, previous, new
        last = self.edit_stack.pop()
        print(last)
        self.data_filtered.at[last[1], last[2]] = last[3]

    def save_changes(self):
        # commit all changes in self.edit_stack to database
        for edit in self.edit_stack:
            pass
        
    # Set Table Entries --------------------------------------------------------
    def add_row(self, i):
        roi = self.data_filtered.iloc[i]
        self.table.setRowHeight(i, 100)
        # Reviewed Checkbox
        reviewed = QTableWidgetItem()
        reviewed.setFlags(reviewed.flags() & Qt.ItemFlag.ItemIsUserCheckable)
        reviewed.setCheckState(self.set_check_state(roi["reviewed"]))

        self.table.setItem(i, 0, reviewed)  # Thumbnail column

        # Thumbnail
        thumbnail = QImage(roi['thumbnail_path'])
        pixmap = QPixmap.fromImage(thumbnail)
        label = QLabel()
        label.setPixmap(pixmap)
        self.table.setCellWidget(i, 1, label)
        
        # Data
        self.table.setItem(i, 2, QTableWidgetItem(roi["filepath"]))  # File Path column
        self.table.setItem(i, 3, QTableWidgetItem(roi["timestamp"]))  # Date Time column

        viewpoint = QTableWidgetItem(self.VIEWPOINT[str(roi["viewpoint"])])
        self.table.setItem(i, 4, viewpoint)  # Viewpoint column
        binomen = QTableWidgetItem(roi["binomen"])
        self.table.setItem(i, 5, binomen)   # Taxon column
        common = QTableWidgetItem(roi["common"])
        self.table.setItem(i, 6, common)  # Species column
        name = QTableWidgetItem(roi["name"])
        self.table.setItem(i, 7, name)  # Individual ID column
        sex = QTableWidgetItem(roi["sex"])
        self.table.setItem(i, 8, sex)  # Sex column

        self.table.setItem(i, 9, QTableWidgetItem(roi["station"]))   # station column
        self.table.setItem(i, 10, QTableWidgetItem(str(roi["sequence_id"])))  # Sequence ID column
        self.table.setItem(i, 11, QTableWidgetItem(str(roi["external_id"])))  # Sequence ID column
        
        if not self.crop:
            reviewed.setFlags(reviewed.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            viewpoint.setFlags(viewpoint.flags() & ~Qt.ItemFlag.ItemIsEditable)
            binomen.setFlags(binomen.flags() & ~Qt.ItemFlag.ItemIsEditable)
            common.setFlags(common.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name.setFlags(name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            sex.setFlags(sex.flags() & ~Qt.ItemFlag.ItemIsEditable)

        # Favorite Checkbox
        favorite = QTableWidgetItem()
        favorite.setFlags(favorite.flags() & Qt.ItemFlag.ItemIsUserCheckable)
        favorite.setCheckState(self.set_check_state(roi["favorite"]))
        self.table.setItem(i, 12, favorite)   # Comment column

        # Comment
        self.table.setItem(i, 13, QTableWidgetItem(roi["comment"]))  # Favorite column

    def set_check_state(self, item):
        """
        Set the checkbox of reviewed and favorite columns
        when adding rows
        """
        if item:
            return Qt.CheckState.Checked
        else:
            return Qt.CheckState.Unchecked

    # captures emitted temp thumbnail path to data, saves to table
    def add_thumbnail_path(self, i, thumbnail_path):
        self.data.loc[i,'thumbnail_path'] = thumbnail_path
 