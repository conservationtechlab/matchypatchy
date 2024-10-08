"""
Widget for displaying list of Media
['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint', 'reviewed', 
'media_id', 'species_id', 'individual_id', 'emb_id', 'filepath', 'ext', 'datetime', 
'site_id', 'sequence_id', 'pair_id', 'comment', 'favorite', 'binomen', 'common', 'name', 'sex']
"""
import pandas as pd
from PIL import Image
from PIL.ImageQt import ImageQt

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QLabel
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import QThread, pyqtSignal, Qt


class MediaTable(QWidget):

    def __init__(self, parent):
        super().__init__(parent)
        self.mpDB = parent.mpDB
        self.parent = parent
        # Set up layout
        layout = QVBoxLayout()

        # Create QTableWidget
        self.table = QTableWidget()
        self.table.setColumnCount(12)  # Columns: Thumbnail, Name, and Description
        self.table.setHorizontalHeaderLabels(["Reviewed","Thumbnail", "File Path", "Date Time", "Species", "Common", "Individual", "Sex", "Site", "Sequence ID", "Favorite", "Comment"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 60) 
        self.table.setColumnWidth(10, 60) 
        # Add table to the layout
        layout.addWidget(self.table)
        self.setLayout(layout)

    def fetch(self):
        """
        Select all media, store in dataframe
        """
        media, column_names = self.mpDB.all_media()
        self.data = pd.DataFrame(media, columns=column_names)

    def filter(self):
        """
        Filter media based on active survey selected in dropdown of DisplayMedia
        """
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
        
    def update(self):
        """
        Fetch and Filter data, Update table
        """
        self.fetch()
        self.filter()

        self.table.setRowCount(len(self.data_filtered))  
        self.image_loader_thread = LoadThumbnailThread(self.data_filtered)

        # Connect signals from the thread to the main thread
        self.image_loader_thread.progress_update.connect(self.parent.loading_bar.set_counter)
        self.image_loader_thread.image_loaded.connect(self.add_row)
        self.image_loader_thread.start()

        # enable checkboxes
        #self.table.itemChanged.connect(self.on_checkbox_change)
    
    def check_state(self, item):
        """
        Set the checkbox of reviewed and favorite columns
        """
        if item:
            return Qt.CheckState.Checked
        else:
            return Qt.CheckState.Unchecked


    def on_checkbox_change(self, item): 
        #print(item.row(),item.column())
        pass
        # update database  

    def add_row(self, i, thumbnail):
        roi = self.data_filtered.iloc[i]
        self.table.setRowHeight(i, 100)
        # Reviewed Checkbox
        reviewed = QTableWidgetItem()
        reviewed.setCheckState(self.check_state(roi["reviewed"]))
        self.table.setItem(i, 0, reviewed)  # Thumbnail column

        # Thumbnail
        label = QLabel()
        label.setPixmap(thumbnail)
        self.table.setCellWidget(i, 1, label)
        
        # Data
        self.table.setItem(i, 2, QTableWidgetItem(roi["filepath"]))  # File Path column
        self.table.setItem(i, 3, QTableWidgetItem(roi["datetime"]))  # Date Time column
        self.table.setItem(i, 4, QTableWidgetItem(roi["binomen"]))   # File Path column
        self.table.setItem(i, 5, QTableWidgetItem(roi["common"]))  # Date Time column
        self.table.setItem(i, 6, QTableWidgetItem(roi["name"]))  # Individual column
        self.table.setItem(i, 7, QTableWidgetItem(roi["sex"]))  # Sex column
        self.table.setItem(i, 8, QTableWidgetItem(roi["site"]))   # Site column
        self.table.setItem(i, 9, QTableWidgetItem(roi["sequence_id"]))  # Sequence ID column
        
        # Favorite Checkbox
        favorite = QTableWidgetItem()
        favorite.setCheckState(self.check_state(roi["favorite"]))
        self.table.setItem(i, 10, favorite)   # Comment column

        # Comment
        self.table.setItem(i, 11, QTableWidgetItem(roi["comment"]))  # Favorite column
        


class LoadThumbnailThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    image_loaded = pyqtSignal(int, QPixmap)

    def __init__(self, data_filtered, crop=True):
        super().__init__()
        self.data_filtered = data_filtered
        self.crop = crop
        self.size = 99
    
    def run(self):
        for i, roi in self.data_filtered.iterrows():

            pil_image = Image.open(roi['filepath'])
            img_width, img_height = pil_image.size 

            if self.crop:
                left = img_width * roi['bbox_x']
                top = img_height * roi['bbox_y']
                right = img_width * (roi['bbox_x'] + roi['bbox_w'])
                bottom = img_height * (roi['bbox_y'] + roi['bbox_h'])
                pil_image = pil_image.crop((left, top, right, bottom))

            qimage = ImageQt(pil_image)
            pixmap = QPixmap.fromImage(qimage)
            scaled_pixmap = pixmap.scaled(self.size, self.size, Qt.AspectRatioMode.KeepAspectRatio, 
                                          Qt.TransformationMode.SmoothTransformation)
            
            # padded_image = QPixmap(self.size, self.size)
            # padded_image.fill(Qt.GlobalColor.black) 
            
            # painter = QPainter(padded_image)
            # # Calculate position to center the scaled image
            # x = (self.size - scaled_pixmap.width()) // 2
            # y = (self.size - scaled_pixmap.height()) // 2
            # painter.drawPixmap(x, y, scaled_pixmap)
            # painter.end()
        
            self.image_loaded.emit(i, scaled_pixmap)
            self.progress_update.emit(int((i + 1) / len(self.data_filtered) * 100))