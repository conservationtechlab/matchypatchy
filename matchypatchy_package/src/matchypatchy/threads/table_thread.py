"""
QThread for saving thumbnails to temp dir for media table
"""
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.database.media import fetch_media, fetch_roi_media, fetch_individual
from matchypatchy.database import thumbnails
from matchypatchy.config import asset_path


class FetchTableThread(QThread):
    """Thread for generating and loading thumbnails with batch operations"""
    progress_update = pyqtSignal(int)
    progress_max = pyqtSignal(int)
    loaded_data = pyqtSignal(pd.DataFrame)
    done = pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.cfg = parent.cfg
        self.mpDB = parent.mpDB
        self.logger = parent.logger
        self.data_type = parent.data_type
        self.thumbnail_dir = self.cfg.THUMBNAIL_DIR
        self.individual_list = fetch_individual(self.mpDB)
        self.data = pd.DataFrame()
        self.thumbnails = pd.DataFrame()
        self.BATCH_SIZE = 50

    def run(self):
        """
        Select all media, store in dataframe
        Merge with thumbnails table
        """
        try:
            # Check for missing thumbnails
            missing_ids = thumbnails.check_missing_thumbnails(self.mpDB, 
                                                              self.thumbnail_dir,
                                                              data_type=self.data_type)
            total_missing = len(missing_ids)
            self.progress_max.emit(total_missing)
            print("Total missing thumbnails:", total_missing)

            # roi
            if self.data_type == 1:
                self.data = fetch_roi_media(self.mpDB, reset_index=False)
                print("Fetched Roi Media, total rows:", len(self.data))
                if missing_ids:
                    self._generate_roi_thumbnails_batch(missing_ids, total_missing)

                # Load all thumbnails
                self.thumbnails = thumbnails.fetch_roi_thumbnails(self.mpDB)
                self.data = pd.merge(self.data, self.thumbnails, on="id", how="left")
                
                self.data.loc[self.data['bbox_w'] == -1, "thumbnail_path"] = asset_path(thumbnails.THUMBNAIL_NOTFOUND)

            # media
            elif self.data_type == 0:
                self.data = fetch_media(self.mpDB, counts=True)
                print("Fetched Media, total rows:", len(self.data))
                if missing_ids:
                    self._generate_media_thumbnails_batch(missing_ids, total_missing)

                # Load all thumbnails
                self.thumbnails = thumbnails.fetch_media_thumbnails(self.mpDB)
                self.data = pd.merge(self.data, self.thumbnails, on="id", how="left")
            else:
                self.data = pd.DataFrame()

            self.data['select'] = 0
            self.loaded_data.emit(self.data)
        except Exception as e:
            self.logger.error(f"Error loading thumbnails: {str(e)}")
        finally:
            self.done.emit()

    def _generate_roi_thumbnails_batch(self, missing_ids, total_missing):
        """
        Batch generate ROI thumbnails and UPDATE existing entries.
        Single batch operation per thumbnail table.
        """
        # Fetch all missing ROI data at once
        missing_data = self.data[self.data['id'].isin(missing_ids)][
            ['id', 'filepath', 'ext', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h']
        ]

        # Prepare batch update data: {roi_id: {'thumbnail_path': path}}
        batch_updates = {}

        for idx, (_, row) in enumerate(missing_data.iterrows()):
            if self.isInterruptionRequested():
                break

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
                print(f"Error generating thumbnail for ROI {roi_id}: {e}")
                continue

            # Update progress
            progress = int((idx + 1) / total_missing * 100)
            self.progress_update.emit(progress)

            # Single batch update operation
            if len(batch_updates) >= self.BATCH_SIZE:
                self.mpDB.batch_update_thumbnails("roi_thumbnails", "fid", batch_updates)
                batch_updates = {}
        
        # Final batch update for any remaining thumbnails
        if batch_updates:
            self.mpDB.batch_update_thumbnails("roi_thumbnails", "fid", batch_updates)
        

    def _generate_media_thumbnails_batch(self, missing_ids, total_missing):
        """
        Batch generate media thumbnails and UPDATE existing entries.
        Single batch operation per thumbnail table.
        """
        # Fetch all missing media data at once
        missing_data = self.data[self.data['id'].isin(missing_ids)][['id', 'filepath', 'ext']]

        # Prepare batch update data
        batch_updates = {}

        for idx, (_, row) in enumerate(missing_data.iterrows()):
            if self.isInterruptionRequested():
                break

            media_id = row['id']
            try:
                # Generate thumbnail
                thumbnail_path = thumbnails.save_media_thumbnail(self.thumbnail_dir, 
                                                                 row['filepath'],
                                                                 row['ext'])
                batch_updates[media_id] = {'filepath': str(thumbnail_path)}

            except Exception as e:
                print(f"Error generating thumbnail for media {media_id}: {e}")
                continue

            # Update progress
            progress = int((idx + 1) / total_missing * 100)
            self.progress_update.emit(progress)

            # Single batch update operation
            if len(batch_updates) >= self.BATCH_SIZE:
                self.mpDB.batch_update_thumbnails("media_thumbnails", "fid", batch_updates)
                batch_updates = {}

        # Final batch update for any remaining thumbnails
        if batch_updates:
            self.mpDB.batch_update_thumbnails("media_thumbnails", "fid", batch_updates)