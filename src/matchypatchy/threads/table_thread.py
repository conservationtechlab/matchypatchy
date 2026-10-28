"""
QThread for saving thumbnails to temp dir for media table
"""
import logging
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from matchypatchy.database.media import fetch_media, fetch_roi_media, fetch_individual
from matchypatchy.database import thumbnails
from matchypatchy.config import asset_path


logger = logging.getLogger(__name__)


class FetchTableThread(QThread):
    """Thread for generating and loading thumbnails with batch operations"""
    progress_update = pyqtSignal(int)
    # 0 means the current stage cannot be measured, show a busy bar
    progress_max = pyqtSignal(int)
    progress_prompt = pyqtSignal(str)
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
        self.thumbnails = pd.DataFrame()
        self.BATCH_SIZE = 50

        # make a copy of the thumbnail not found path
        thumbnail_notfound = QImage(str(asset_path(thumbnails.THUMBNAIL_NOTFOUND)))
        thumbnail_notfound.save(str(self.thumbnail_dir) + "/thumbnail_notfound.png", format="PNG")
        # and the placeholder for rois without a bounding box
        thumbnail_nobbox = QImage(str(asset_path(thumbnails.THUMBNAIL_NOBBOX)))
        thumbnail_nobbox.save(str(self.thumbnail_dir) + "/thumbnail_nobbox.png", format="PNG")


    def run(self):
        """
        Select all media, store in dataframe
        Merge with thumbnails table
        """
        try:
            # Check for missing thumbnails
            self.progress_max.emit(0)
            self.progress_prompt.emit("Checking thumbnails...")
            missing_ids = thumbnails.check_missing_thumbnails(self.mpDB, 
                                                              self.thumbnail_dir,
                                                              data_type=self.data_type)

            # roi
            if self.data_type == 1:
                self.progress_prompt.emit("Loading ROIs...")
                self.data = fetch_roi_media(self.mpDB, reset_index=False)
                if missing_ids:
                    self._generate_roi_thumbnails_batch(missing_ids)

                # Load all thumbnails
                self.progress_max.emit(0)
                self.progress_prompt.emit("Building table...")
                self.thumbnails = thumbnails.fetch_roi_thumbnails(self.mpDB)
                self.data = pd.merge(self.data, self.thumbnails, on="id", how="left")
                
                self.data.loc[self.data['bbox_w'] == -1, "thumbnail_path"] = "thumbnail_nobbox.png"

            # media
            elif self.data_type == 0:
                self.progress_prompt.emit("Loading media...")
                self.data = fetch_media(self.mpDB, counts=True)
                if missing_ids:
                    self._generate_media_thumbnails_batch(missing_ids)

                # Load all thumbnails
                self.progress_max.emit(0)
                self.progress_prompt.emit("Building table...")
                self.thumbnails = thumbnails.fetch_media_thumbnails(self.mpDB)
                self.data = pd.merge(self.data, self.thumbnails, on="id", how="left")
            else:
                self.data = pd.DataFrame()

            # sort
            if not self.data.empty:
                sort_cols = [c for c in ("timestamp", "filepath", "frame", "id")
                             if c in self.data.columns]
                self.data = (self.data
                             .sort_values(sort_cols, kind="stable", na_position="last")
                             .reset_index(drop=True))

            self.data['select'] = 0

            self.data['sequence_id'] = self.data['sequence_id'].astype("Int64")
            self.data['external_id'] = self.data['external_id'].astype("Int64")

            self.loaded_data.emit(self.data)
        except Exception as e:
            logger.error(f"Error loading thumbnails: {str(e)}")
        finally:
            self.done.emit()

    def _generate_roi_thumbnails_batch(self, missing_ids):
        """
        Batch generate ROI thumbnails and UPDATE existing entries.
        Single batch operation per thumbnail table.
        """
        # Fetch all missing ROI data at once, the progress total counts only these rows;
        # missing_ids can repeat ids and name rois that are not loaded
        missing_data = self.data[self.data['id'].isin(missing_ids)][
            ['id', 'filepath', 'ext', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h']
        ]
        # ROIs with invalid bounding boxes get the no-bbox placeholder instead
        missing_data = missing_data[missing_data['bbox_w'] != -1]
        if missing_data.empty:
            return
        self.progress_max.emit(len(missing_data))
        self.progress_prompt.emit(f"Generating {len(missing_data)} missing thumbnails...")

        # Prepare batch update data: {roi_id: {'thumbnail_path': path}}
        batch_updates = {}

        for idx, (_, row) in enumerate(missing_data.iterrows()):
            if self.isInterruptionRequested():
                break
            # count every row, including failures, so the bar reaches the total
            self.progress_update.emit(idx + 1)

            roi_id = row['id']
            try:
                # Generate thumbnail
                thumbnail_path = thumbnails.save_roi_thumbnail(self.thumbnail_dir,
                                                               row['filepath'],
                                                               row['ext'],
                                                               row['frame'],
                                                               row['bbox_x'],
                                                               row['bbox_y'],
                                                               row['bbox_w'],
                                                               row['bbox_h'])
                batch_updates[roi_id] = {'filepath': str(thumbnail_path)}

            except Exception as e:
                logger.error(f"Error generating thumbnail for ROI {roi_id}: {e}")
                continue

            # Single batch update operation
            if len(batch_updates) >= self.BATCH_SIZE:
                self.mpDB.batch_update_thumbnails("roi_thumbnails", "fid", batch_updates)
                batch_updates = {}
        
        # Final batch update for any remaining thumbnails
        if batch_updates:
            self.mpDB.batch_update_thumbnails("roi_thumbnails", "fid", batch_updates)
        

    def _generate_media_thumbnails_batch(self, missing_ids):
        """
        Batch generate media thumbnails and UPDATE existing entries.
        Single batch operation per thumbnail table.
        """
        # Fetch all missing media data at once, the progress total counts only these rows;
        # missing_ids can repeat ids
        missing_data = self.data[self.data['id'].isin(missing_ids)][['id', 'filepath', 'ext']]
        if missing_data.empty:
            return
        self.progress_max.emit(len(missing_data))
        self.progress_prompt.emit(f"Generating {len(missing_data)} missing thumbnails...")

        # Prepare batch update data
        batch_updates = {}

        for idx, (_, row) in enumerate(missing_data.iterrows()):
            if self.isInterruptionRequested():
                break
            # count every row, including failures, so the bar reaches the total
            self.progress_update.emit(idx + 1)

            media_id = row['id']
            try:
                # Generate thumbnail
                thumbnail_path = thumbnails.save_media_thumbnail(self.thumbnail_dir, 
                                                                 row['filepath'],
                                                                 row['ext'])
                batch_updates[media_id] = {'filepath': str(thumbnail_path)}

            except Exception as e:
                logger.error(f"Error generating thumbnail for media {media_id}: {e}")
                continue

            # Single batch update operation
            if len(batch_updates) >= self.BATCH_SIZE:
                self.mpDB.batch_update_thumbnails("media_thumbnails", "fid", batch_updates)
                batch_updates = {}

        # Final batch update for any remaining thumbnails
        if batch_updates:
            self.mpDB.batch_update_thumbnails("media_thumbnails", "fid", batch_updates)