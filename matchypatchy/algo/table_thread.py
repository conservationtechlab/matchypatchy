"""
QThread for saving thumbnails to temp dir for media table
"""
import os
import pandas as pd
from pathlib import Path

from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (QTableWidgetItem, QWidget, 
                             QComboBox, QLabel, QHeaderView, QStyledItemDelegate)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QRect

from concurrent.futures import ThreadPoolExecutor, as_completed

THUMBNAIL_NOTFOUND = QImage(os.path.join(os.path.dirname(__file__), "assets/thumbnail_notfound.png"))
# TODO THUMBNAIL_NOTFOUND = QImage(os.path.normpath("assets/logo.png"))


class LoadTableThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    loaded_cell = pyqtSignal(int, int, object)
    done = pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.data = parent.data
        self.valid_stations = parent.valid_stations
        self.VIEWPOINTS = parent.VIEWPOINTS
        self.species_list = parent.species_list
        self.individual_list = parent.individual_list
        self.columns = parent.columns

    def run(self):
        for i, roi in self.data.iterrows():
            for j, column in self.columns.items():
                if not self.isInterruptionRequested():
                    qtw = self.add_cell(roi, column)
                    self.loaded_cell.emit(i, j, qtw)
            self.progress_update.emit(i+1)

        if not self.isInterruptionRequested():
            self.done.emit()


    def add_cell(self, roi, column):
        """
        Adds Row to Table with Items from self.data_filtered
        """
        if column == 'select':
            qtw = QTableWidgetItem()
            qtw.setFlags(qtw.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            qtw.setCheckState(Qt.CheckState.Unchecked)
        # Thumbnail
        #TODO: FIX ASSET PATH
        elif column == 'thumbnail':
            thumbnail_path = roi['thumbnail_path']
            if not thumbnail_path:
                thumbnail_path = "/matchypatchy/gui/assets/thumbnail_notfound.png"
            qtw = QImage(thumbnail_path)

        # FilePath and Timestamp not editable
        elif column == 'filepath' or column == 'timestamp':
            qtw = QTableWidgetItem(roi[column])
            qtw.setFlags(qtw.flags() & ~Qt.ItemFlag.ItemIsEditable)
        # Station
        elif column == 'station':
            qtw = QTableWidgetItem(self.valid_stations[roi["station_id"]])
        # Viewpoint
        elif column == 'viewpoint':
            vp_raw = roi["viewpoint"]

            if pd.isna(vp_raw) or vp_raw is None or str(vp_raw) == "None":
                vp_key = "None"
            else:
                vp_key = str(int(vp_raw))  # convert float 1.0 → int 1 → str "1"

            vp_value = self.VIEWPOINTS.get(vp_key, "None")
            qtw = QTableWidgetItem(vp_value)


        # Species ID
        elif column == 'binomen' or column == 'common':
            if self.species_list.empty:
                # can't edit if no species in table
                qtw = QTableWidgetItem()
                qtw.setFlags(qtw.flags() & ~Qt.ItemFlag.ItemIsEditable)
            else:
                if roi['species_id'] is not None:
                    print(f"species_id is {roi['species_id']}")
                    print("species_list is\n", self.species_list)

                    species = self.species_list[self.species_list['id'] == roi['species_id']]
                    print("filtered species is\n", species)

                    if not species.empty:
                        qtw = QTableWidgetItem(str(species[column].values[0]))
                    else:
                        print("Species not found — setting to 'Unknown'")
                        qtw = QTableWidgetItem("Unknown")

                else:
                    qtw = QTableWidgetItem("Unknown")

                '''
                if roi['species_id'] is not None:
                    print(f"species list is {self.species_list}")
                    species = self.species_list[self.species_list['id'] == roi['species_id']]
                    print(f"species is {species}")
                    self.table.setItem(i, column, QTableWidgetItem(species[data][0]))
                else:
                    self.table.setItem(i, column, QTableWidgetItem(None))
                '''
        
        elif column == "name" or column == "sex" or column == 'age':
            if roi['individual_id'] is not None:
                individual = self.individual_list[self.individual_list['id'] == roi['individual_id']]
                if not individual.empty:
                    qtw = QTableWidgetItem(str(individual[column].values[0]))
                else:
                    print(f"Warning: individual_id {roi['individual_id']} not found in individual_list")
                    qtw = QTableWidgetItem("Unknown")
            else:
                qtw = QTableWidgetItem("Unknown")


        # Reviewed and Favorite Checkbox
        elif column == 'reviewed' or column == 'favorite':
            qtw = QTableWidgetItem()
            qtw.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            qtw.setCheckState(self.set_checkstate(roi[column]))
        else:
            qtw = QTableWidgetItem(str(roi[column]))

        # return widget
        return qtw
    
    def set_checkstate(self, item):
        """
        Set the checkbox of reviewed and favorite columns
        when adding rows
        """
        if item:
            return Qt.CheckState.Checked
        else:
            return Qt.CheckState.Unchecked
