"""
QThread for saving thumbnails to temp dir for media table
"""
import pandas as pd

from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import QThread, pyqtSignal, Qt

from matchypatchy.algo.thumbnails import THUMBNAIL_NOTFOUND
from matchypatchy.config import resource_path


class LoadTableThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    loaded_cell = pyqtSignal(int, int, object)
    done = pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.data = parent.data_filtered
        self.valid_stations = parent.valid_stations
        self.valid_cameras = parent.valid_cameras
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
            self.progress_update.emit(i + 1)

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
        elif column == 'thumbnail':
            thumbnail_path = roi['thumbnail_path']
            if not thumbnail_path:
                thumbnail_path = resource_path(THUMBNAIL_NOTFOUND)
            qtw = QImage(thumbnail_path)

        # filepath and Timestamp not editable
        elif column == 'filepath' or column == 'timestamp':
            qtw = QTableWidgetItem(roi[column])
            qtw.setFlags(qtw.flags() & ~Qt.ItemFlag.ItemIsEditable)
        # Station
        elif column == 'station':
            qtw = QTableWidgetItem(self.valid_stations[roi["station_id"]])
        # Camera
        elif column == 'camera':
            if roi["camera_id"]:
                qtw = QTableWidgetItem(self.valid_cameras[roi["camera_id"]])
            else:  # can be null
                qtw = QTableWidgetItem()
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
                    species = self.species_list[self.species_list['id'] == roi['species_id']]

                    if not species.empty:
                        qtw = QTableWidgetItem(str(species[column].values[0]))
                    else:
                        print("Species not found — setting to 'Unknown'")
                        qtw = QTableWidgetItem("Unknown")

                else:
                    qtw = QTableWidgetItem("Unknown")

        # name not editable here
        elif column == "individual_id":
            if roi['individual_id'] is not None:
                name = self.individual_list.loc[roi['individual_id'], 'name']
                qtw = QTableWidgetItem(str(name))
            else:
                qtw = QTableWidgetItem("Unknown")
            qtw.setFlags(qtw.flags() & ~Qt.ItemFlag.ItemIsEditable)

        elif column == "sex" or column == 'age':
            if roi['individual_id'] is not None:
                qtw = QTableWidgetItem(str(roi[column]))
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
