"""
Widget for displaying list of Media
['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint', 'reviewed', 
'media_id', 'species_id', 'individual_id', 'emb_id', 'filepath', 'ext', 'datetime', 
'site_id', 'sequence_id', 'pair_id', 'comment', 'favorite', 'binomen', 'common', 'name', 'sex']
"""

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

import pandas as pd
from .widget_thumbnail import ThumbnailWidget


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
        survey_id = self.parent.active_survey[0]
        valid_sites = dict(self.mpDB.select("site", columns="id, name", row_cond=f'survey_id={survey_id}'))
        self.data = self.data[self.data['site_id'].isin(list(valid_sites.keys()))]
        self.data['site'] = self.data['site_id'].map(valid_sites)
        
    def update(self):
        """
        Fetch and Filter data, Update table
        """
        self.fetch()
        self.filter()
        self.table.setRowCount(len(self.data))  

        for i, roi in self.data.iterrows():
            # Load and set the thumbnail
            #thumbnail = ThumbnailWidget(roi["filepath"]).scaled(50, 50)  # Scale the image to thumbnail size
            #icon = QIcon(pixmap)
            thumbnail_item = QTableWidgetItem()
            #thumbnail_item.setIcon(icon)

            # Reviewed Checkbox
            reviewed = QTableWidgetItem()
            reviewed.setCheckState(self.check_state(roi["reviewed"]))
            self.table.setItem(i, 0, reviewed)  # Thumbnail column

            # Thumbnail
            self.table.setItem(i, 1, thumbnail_item)

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
 
        # enable checkboxes
        self.table.itemChanged.connect(self.on_checkbox_change)


    def check_state(self, item):
        """
        Set the checkbox of reviewed and favorite columns
        """
        if item:
            return Qt.CheckState.Checked
        else:
            return Qt.CheckState.Unchecked
        
    def on_checkbox_change(self, item): 
        print(item.row(),item.column())

        # update database 