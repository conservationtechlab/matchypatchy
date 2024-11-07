"""
Widget for displaying list of Media
['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint', 'reviewed', 
'media_id', 'species_id', 'individual_id', 'emb_id', 'filepath', 'ext', 'timestamp', 
'site_id', 'sequence_id', 'capture_id', 'comment', 'favorite', 'binomen', 'common', 'name', 'sex']
"""

# TODO: MAKE TABLE EDITABLE
# TODO: KEEP QUEUE OF EDITS, UNDOABLE, COMMIT SAVE OR RETURN
# TODO: MAKE THUMBNAIL LOAD FASTER

import tempfile
import pandas as pd

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QLabel, QHeaderView
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QRect

from matchypatchy.config import TEMP_DIR, VIEWPOINT
from matchypatchy.gui.popup_alert import AlertPopup
from matchypatchy.database.media import fetch_media

THUMBNAIL_NOTFOUND = '/home/kyra/matchypatchy/matchypatchy/gui/assets/thumbnail_notfound.png'

class MediaTable(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.mpDB = parent.mpDB
        self.parent = parent
        self.data = pd.DataFrame()
        self.thumbnails = dict()
        self.crop = True
        self.edits = list()
        self.columns = ["reviewed","thumbnail", "filepath", "timestamp", 
                        "viewpoint", "binomen", "common", "individual_id", "sex", 
                        "site", "sequence_id", "capture_id", "favorite", "comment"]
        # Set up layout
        layout = QVBoxLayout()

        # Create QTableWidget
        self.table = QTableWidget()
        self.table.setColumnCount(14)  # Columns: Thumbnail, Name, and Description
        self.table.setHorizontalHeaderLabels(["Reviewed","Thumbnail", "File Path", "Timestamp", 
                                              "Viewpoint", "Species", "Common", "Individual", "Sex", 
                                              "Site", "Sequence ID", "Capture ID", "Favorite", "Comment"])
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, 100)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSortingEnabled(True)
        self.table.itemChanged.connect(self.update_entry)  # allow user editing

        # Add table to the layout
        layout.addWidget(self.table)
        self.setLayout(layout)


    def fetch(self):
        """
        Select all media, store in dataframe
        """
        roi_n = self.mpDB.count('roi')        
        if roi_n > 0:
            media, column_names = self.mpDB.all_media()
            self.data = pd.DataFrame(media, columns=column_names)  
        # no rois processed, default to full image
        else:
            self.data = fetch_media(self.mpDB)
            self.crop = False  # display full image
            if not self.data.empty:
                # fill in missing columns
                self.data =self.data.assign(reviewed=0, binomen=None, common=None, 
                                            name=None, sex=None, individual_id=0)
            else: 
                # no media, give warning, go home
                self.parent.loading_bar.close()
                dialog = AlertPopup(self, "No images found! Please import media.", title="Alert")
                if dialog.exec():
                    self.parent.home()
                    del dialog

        # set df index to table index
        #self.data = self.data.set_index("id")

    # RUN ON ENTRY
    def load(self):
        """
        Fetch table, load images and save as thumbnails to TEMP_DIR
        """
        self.fetch()  
        
        self.parent.loading_bar.show()
        self.table.clearContents() 
        self.table.setRowCount(len(self.data))  
        # load images
        self.image_loader_thread = LoadThumbnailThread(self.data, self.crop)
        self.image_loader_thread.progress_update.connect(self.parent.loading_bar.set_counter)
        self.image_loader_thread.loaded_image.connect(self.add_thumbnail_path)
        self.image_loader_thread.finished.connect(self.filter)
        self.image_loader_thread.start()


    def filter(self):
        """
        Filter media based on active survey selected in dropdown of DisplayMedia
        Always run before updating table
        """
        # create new copy of full dataset
        self.data_filtered = self.data
        # Survey Filter
        if self.parent.valid_sites:
            self.data_filtered = self.data_filtered[self.data_filtered['site_id'].isin(list(self.parent.valid_sites.keys()))]
            self.data_filtered['site'] = self.data_filtered['site_id'].map(self.parent.valid_sites)
        else:
            self.data_filtered['site'] = self.data_filtered['site_id']

        # Single Site Filter
        if self.parent.active_site[0] > 0:
            self.data_filtered = self.data_filtered[self.data_filtered['site_id'] == self.parent.active_site[0]]

        # Species Filter
        if self.parent.active_species[0] > 0:
            self.data_filtered = self.data_filtered[self.data_filtered['species_id'] == self.parent.active_species[0]]

        # Unidentified Filter
        if self.parent.unidentified_only:
            self.data_filtered = self.data_filtered[self.data_filtered['individual_id'] == 0]

        if self.parent.favorites_only:
            self.data_filtered = self.data_filtered[self.data_filtered['favorite'] == 1]

        # refresh table
        self.refresh_table()

    def refresh_table(self):
        """
        Add rows to table
        """
        # clear old contents and prep for filtered data
        self.table.clearContents() 
        # disconnect edit function while refreshing to prevent needless calls
        self.table.blockSignals(True)  
        self.table.setRowCount(self.data_filtered.shape[0])
        for i in range(self.data_filtered.shape[0]):
            self.add_row(i)
        self.table.blockSignals(False)  # reconnect editing
       
    # TODO: UPDATE ENTRIES
    def update_entry(self, item): 
        """
        Allows user to edit entry in table 

        Save edits in queue, allow undo 
        prompt user to save edits 
        """
        entry = item.row()
        reference = self.columns[item.column()]
        print(entry,reference)
        # if checkbox
        if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
            print(item.checkState() == Qt.CheckState.Checked)
        # else is text
        else:
            print(self.data_filtered.at[entry, reference])
            # convert row and column to 
            print(item.text())  

        # add to queue
    
    def set_check_state(self, item):
        """
        Set the checkbox of reviewed and favorite columns
        when adding rows
        """
        if item:
            return Qt.CheckState.Checked
        else:
            return Qt.CheckState.Unchecked

    def add_row(self, i):
        roi = self.data_filtered.iloc[i]
        self.table.setRowHeight(i, 100)
        # Reviewed Checkbox
        reviewed = QTableWidgetItem()
        reviewed.setFlags(reviewed.flags() | Qt.ItemFlag.ItemIsUserCheckable)
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
        self.table.setItem(i, 4, QTableWidgetItem(VIEWPOINT[roi["viewpoint"]]))  # Viewpoint column
        self.table.setItem(i, 5, QTableWidgetItem(roi["binomen"]))   # File Path column
        self.table.setItem(i, 6, QTableWidgetItem(roi["common"]))  # Date Time column
        self.table.setItem(i, 7, QTableWidgetItem(roi["name"]))  # Individual column
        self.table.setItem(i, 8, QTableWidgetItem(roi["sex"]))  # Sex column
        self.table.setItem(i, 9, QTableWidgetItem(roi["site"]))   # Site column
        self.table.setItem(i, 10, QTableWidgetItem(str(roi["sequence_id"])))  # Sequence ID column
        self.table.setItem(i, 11, QTableWidgetItem(str(roi["capture_id"])))  # Sequence ID column
        
        # Favorite Checkbox
        favorite = QTableWidgetItem()
        favorite.setFlags(favorite.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        favorite.setCheckState(self.set_check_state(roi["favorite"]))
        self.table.setItem(i, 12, favorite)   # Comment column

        # Comment
        self.table.setItem(i, 13, QTableWidgetItem(roi["comment"]))  # Favorite column

    # adds emitted temp thumbnail path to data 
    def add_thumbnail_path(self, i, thumbnail_path):
        self.data.loc[i,'thumbnail_path'] = thumbnail_path


class LoadThumbnailThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    loaded_image = pyqtSignal(int, str)

    def __init__(self, data, crop=True):
        super().__init__()
        self.data = data
        self.crop = crop
        self.size = 99
    
    def run(self):
        for i, roi in self.data.iterrows():
            # load image
            self.original = QImage(roi['filepath'])
            # image not found, use placeholder
            if self.original.isNull():
                self.image = QImage(THUMBNAIL_NOTFOUND)
            else:
                # crop for rois
                if self.crop:
                    left = self.original.width() * roi['bbox_x']
                    top = self.original.height() * roi['bbox_y']
                    right = self.original.width() * roi['bbox_w']
                    bottom = self.original.height() * roi['bbox_h']
                    crop_rect = QRect(int(left), int(top), int(right), int(bottom))
                    self.image = self.original.copy(crop_rect)
                # no crop for media
                else:
                    self.image = self.original.copy()
            # scale it to 99x99
            scaled_image = self.image.scaled(self.size, self.size,
                                            Qt.AspectRatioMode.KeepAspectRatio, 
                                            Qt.TransformationMode.SmoothTransformation)
            
            # create a temporary file to hold thumbnail
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_file_path = temp_file.name 
            # save the image
            scaled_image.save(temp_file_path, format="JPG")
            # emit thumbnail_path and progress update
            self.loaded_image.emit(i, temp_file_path)
            self.progress_update.emit(int((i + 1) / len(self.data) * 100))
