"""
QThread for saving thumbnails to temp dir for media table
"""
import pandas as pd

from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import QThread, pyqtSignal, Qt

from matchypatchy.database.media import fetch_media, fetch_roi_media, fetch_individual
from matchypatchy.database import thumbnails
from matchypatchy.config import resource_path


class FetchTableThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    loaded_data = pyqtSignal(pd.DataFrame)
    done = pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.mpDB = parent.mpDB
        self.data_type = parent.data_type
        self.thumbnail_dir = parent.thumbnail_dir
        self.individual_list = fetch_individual(self.mpDB)
        self.data = pd.DataFrame()

    # STEP 2 - CALLED BY load_data()
    def run(self):
        """
        Select all media, store in dataframe
        Merge with thumbnails table
        """
        # check for missing thumbnails and add
        missing_thumbnails = thumbnails.check_missing_thumbnails(self.mpDB, data_type=self.data_type)

        # ROIS
        if self.data_type == 1:
            self.data = fetch_roi_media(self.mpDB, reset_index=False)
            print("Fetched Roi Media, total rows:", len(self.data))

            # add missing thumbnails
            if missing_thumbnails:
                for roi_id in missing_thumbnails:
                    row = self.data[self.data['id'] == roi_id]
                    filepath = row['filepath'].values[0]
                    ext = row['ext'].values[0]
                    frame = row['frame'].values[0]
                    bbox_x = row['bbox_x'].values[0]
                    bbox_y = row['bbox_y'].values[0]
                    bbox_w = row['bbox_w'].values[0]
                    bbox_h = row['bbox_h'].values[0]
                    thumbnail_path = thumbnails.save_roi_thumbnail(self.thumbnail_dir, filepath, ext,
                                                                   frame, bbox_x, bbox_y, bbox_w, bbox_h)
                    self.mpDB.delete("roi_thumbnails", f"fid={roi_id}")  # remove old entry if exists
                    self.mpDB.add_thumbnail("roi", roi_id, thumbnail_path)
            # load thumbnails
            self.thumbnails = thumbnails.fetch_roi_thumbnails(self.mpDB)
            self.data = pd.merge(self.data, self.thumbnails, on="id")

        # MEDIA
        elif self.data_type == 0:
            self.data = fetch_media(self.mpDB)
            print("Fetched Media, total rows:", len(self.data))
            # add missing thumbnails
            if missing_thumbnails:
                for media_id in missing_thumbnails:
                    filepath = self.data.loc[self.data['id'] == media_id, 'filepath'].values[0]
                    ext = self.data.loc[self.data['id'] == media_id, 'ext'].values[0]
                    thumbnail_path = thumbnails.save_media_thumbnail(self.thumbnail_dir, filepath, ext)
                    self.mpDB.delete("media_thumbnails", f"fid={media_id}")  # remove old entry if exists
                    self.mpDB.add_thumbnail("media", media_id, thumbnail_path)
            # load thumbnails
            self.thumbnails = thumbnails.fetch_media_thumbnails(self.mpDB)
            self.data = pd.merge(self.data, self.thumbnails, on="id")
        # return empty
        else:
            self.data = pd.DataFrame()

        self.loaded_data.emit(self.data)
        self.done.emit()


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
                thumbnail_path = str(resource_path(THUMBNAIL_NOTFOUND))
            qtw = QImage(thumbnail_path)

        # filepath and Timestamp not editable
        elif column == 'filepath' or column == 'timestamp':
            qtw = QTableWidgetItem(roi[column])
            qtw.setFlags(qtw.flags() & ~Qt.ItemFlag.ItemIsEditable)
        # Station
        elif column == 'station':
            qtw = QTableWidgetItem(self.valid_stations[roi["station_id"]])
        # Camera
        elif column == 'camera_id':
            if roi["camera_id"]:
                qtw = QTableWidgetItem(self.valid_cameras[int(roi["camera_id"])])
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
