"""
QThread for saving thumbnails to temp dir for media table
"""
import pandas as pd

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.database.media import fetch_media, fetch_roi_media, fetch_individual
from matchypatchy.database import thumbnails
from matchypatchy.config import asset_path


class FetchTableThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    prompt_update = pyqtSignal(str)  # Signal to update the alert prompt
    loaded_data = pyqtSignal(pd.DataFrame)
    done = pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.cfg = parent.cfg
        self.mpDB = parent.mpDB
        self.data_type = parent.data_type
        self.thumbnail_dir = self.cfg.THUMBNAIL_DIR
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
        if missing_thumbnails:
            self.prompt_update.emit(f"Found {len(missing_thumbnails)} missing thumbnails. Refreshing...")

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
                    # skip if bounding box is invalid
                    if bbox_w == -1:
                        thumbnail_path = asset_path(thumbnails.THUMBNAIL_NOTFOUND)
                    else:
                        thumbnail_path = thumbnails.save_roi_thumbnail(self.thumbnail_dir, filepath, ext,
                                                                       frame, bbox_x, bbox_y, bbox_w, bbox_h)
                        self.mpDB.delete("roi_thumbnails", f"fid={roi_id}")  # remove old entry if exists
                        self.mpDB.add_thumbnail("roi", roi_id, thumbnail_path)
            # load thumbnails
            self.thumbnails = thumbnails.fetch_roi_thumbnails(self.mpDB)
            self.data = pd.merge(self.data, self.thumbnails, on="id")

        # MEDIA
        elif self.data_type == 0:
            self.data = fetch_media(self.mpDB, counts=True)
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

        self.data['select'] = 0
        self.loaded_data.emit(self.data)
        self.done.emit()
