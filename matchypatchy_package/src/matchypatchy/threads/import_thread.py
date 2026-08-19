"""
QThreads for Importing Data

"""
import pandas as pd
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.config import load_cfg
from matchypatchy.database.thumbnails import save_media_thumbnail, save_roi_thumbnail
from matchypatchy.database.media import get_sha256

# CSV MIGRATE ==================================================================
class CSVMigrateThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    error_update = pyqtSignal(list)  # Signal to update the error log

    EXPECTED_COLUMNS = {'id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
                        'reviewed', 'favorite', 'media_id',  'emb',
                        'filepath', 'ext', 'timestamp', 'sequence_id', 'external_id', 'comment', 
                        'individual_id', 'name', 'sex', 'age',
                        'station_id', 'station_name', 'lat', 'long', 
                        'station_survey_id', 'survey_name', 'region_name', 
                        'camera_id', 'camera_name'}

    def __init__(self, mpDB, data, logger):
        super().__init__()
        self.mpDB = mpDB
        self.logger = logger
        self.data = data
        self.thumbnail_dir = load_cfg('THUMBNAIL_DIR')
        self.station_ref = {}  # dictionary to store survey name to id mapping
        self.camera_ref = {}  # dictionary to store camera name to id mapping
        self.individual_ref = {}  # dictionary to store individual name to id mapping
        self.sequence_ref = {}  # dictionary to store sequence id mapping
        self.errors = []  # list to store errors encountered during import

    def run(self):
        roi_counter = 0  # progressbar counter
        for row in self.data.itertuples(index=False):
            if not self.isInterruptionRequested():

                print(row)

                # get survey id, create if not exists
                survey_id = self.survey(row.survey_name, row.region_name)

                # station
                new_station_id = self.station(row.station_id, row.station_name, survey_id, row.lat, row.long)

                # camera
                new_camera_id = self.camera(new_station_id, row.camera_id, row.camera_name)

                hash = get_sha256(row.filepath)
                if hash is None:
                    self.logger.warning(f"File {row.filepath} does not exist, skipping import...")
                    self.errors.append(row.filepath)
                    continue

                # new sequence id 
                sequence_id = self.sequence(row.sequence_id)

                # media
                media_id = self.mpDB.add_media(row.filepath,
                                               hash,
                                               row.ext,
                                               row.timestamp,
                                               station_id=new_station_id,
                                               camera_id=new_camera_id,
                                               sequence_id=sequence_id,
                                               external_id=row.external_id if not pd.isna(row.external_id) else None,
                                               comment=row.comment if not pd.isna(row.comment) else None)

                if media_id == "duplicate_error":
                    media_id = self.mpDB.select("media", columns="id", row_cond=f'filepath="{row.filepath}"')[0][0]
                
                # save thumbnail for new media
                media_thumbnail = save_media_thumbnail(self.thumbnail_dir, row.filepath, row.ext)
                self.mpDB.add_thumbnail("media", media_id, media_thumbnail)

                # individual
                individual_id = self.individual(row.individual_id, row.name, row.sex, row.age)

                # get bounding box coordinates, if any are missing, set to -1
                bbox_x = row.bbox_x if not pd.isna(row.bbox_x) else -1
                bbox_y = row.bbox_y if not pd.isna(row.bbox_y) else -1
                bbox_w = row.bbox_w if not pd.isna(row.bbox_w) else -1
                bbox_h = row.bbox_h if not pd.isna(row.bbox_h) else -1
                    
                # roi
                rid = self.mpDB.add_roi(media_id,
                                        row.frame,
                                        bbox_x, 
                                        bbox_y, 
                                        bbox_w, 
                                        bbox_h,
                                        viewpoint=row.viewpoint if not pd.isna(row.viewpoint) else None,
                                        reviewed=row.reviewed if not pd.isna(row.reviewed) else 0,
                                        favorite=row.favorite if not pd.isna(row.favorite) else 0,
                                        individual_id=individual_id,
                                        emb=0)  # do not add emb, must be reprocessed in new project
                # save thumbnail for new roi
                roi_thumbnail = save_roi_thumbnail(self.thumbnail_dir, row.filepath, row.ext, 
                                                   row.frame, bbox_x, bbox_y, bbox_w, bbox_h)
                self.mpDB.add_thumbnail("roi", rid, roi_thumbnail)

                roi_counter += 1
                self.progress_update.emit(roi_counter)

        if not self.isInterruptionRequested():
            # finished adding media
            self.finished.emit()
            self.error_update.emit(self.errors)  # Emit the list of errors encountered during import

    def survey(self, survey_name, region_name):
        """Get or create survey"""
        # get active survey
        try:
            survey_id = self.mpDB.select("survey", columns="id", row_cond=f'name="{survey_name}"')[0][0]
        except IndexError:
            region_id = self.region(region_name) if not pd.isna(region_name) else None
            survey_id = self.mpDB.add_survey(str(survey_name), region_id, None, None)
        return survey_id

    def region(self, region_name):
        """Get or create region"""
        try:
            region_id = self.mpDB.select("region", columns="id", row_cond=f'name="{region_name}"')[0][0]
        except IndexError:
            region_id = self.mpDB.add_region(str(region_name), None)
        return region_id

    def station(self, old_station_id, station_name, survey_id, lat, long):
        """Get or create station"""
        try:
            station_id = self.station_ref[old_station_id]
        except KeyError:
            try:
                station_id = self.mpDB.select("station", columns="id", row_cond=f'name="{station_name}"')[0][0]
            except IndexError:
                station_id = self.mpDB.add_station(str(station_name), 
                                                   lat if not pd.isna(lat) else None, 
                                                   long if not pd.isna(long) else None,
                                                   survey_id)
            self.station_ref[old_station_id] = station_id
        return station_id

    def camera(self, station_id, old_camera_id, camera_name):
        """Get or create camera, not required for import"""
        if not pd.isna(old_camera_id):
            try:
                # get camera id from reference dictionary first
                camera_id = self.camera_ref[old_camera_id]
            except KeyError:
                # get camera id from database if not in reference dictionary
                try:
                    camera_name = str(camera_name).strip()
                    camera_name = camera_name.replace("'", "''")
                    row_cond = f"name = '{camera_name}'"
                    rows = self.mpDB.select("camera", columns="id", row_cond=row_cond)
                    camera_id = rows[0][0]
                # if not in database, add camera
                except IndexError:
                    camera_id = self.mpDB.add_camera(str(camera_name), station_id)
                # add camera id to reference dictionary
                self.camera_ref[old_camera_id] = camera_id
            return camera_id
        # if no camera name, return None
        else:
            return None

    def individual(self, old_individual_id, name, sex, age):
        """Get or create individual ID, not required for import"""
        if not pd.isna(old_individual_id):
            try:
                # get individual id from reference dictionary first
                individual_id = self.individual_ref[old_individual_id]
            except KeyError:
                # get individual id from database if not in reference dictionary
                try:
                    individual_id = self.mpDB.select("individual", columns="id", row_cond=f'name="{name}"')[0][0]
                # if not in database, add individual
                except IndexError:
                    individual_id = self.mpDB.add_individual(str(name), 
                                                             sex if not pd.isna(sex) else None,
                                                             age if not pd.isna(age) else None)
            return individual_id
        # if no individual name, return None
        else:
            return None

    def sequence(self, old_sequence_id):
        """Get or create sequence ID, not required for import"""
        if not pd.isna(old_sequence_id):
            try:
                # get sequence id from reference dictionary first
                sequence_id = self.sequence_ref[old_sequence_id]
            except KeyError:
                sequence_id = self.mpDB.add_sequence()
                self.sequence_ref[old_sequence_id] = sequence_id
            return sequence_id
        else:
            return None



# CSV IMPORT ===================================================================
class CSVImportThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar

    def __init__(self, mpDB, unique_images, selected_columns, logger):
        super().__init__()
        self.mpDB = mpDB
        self.logger = logger
        self.unique_images = unique_images
        self.selected_columns = selected_columns
        self.thumbnail_dir = load_cfg('THUMBNAIL_DIR')

    def run(self):
        roi_counter = 0  # progressbar counter
        for filepath, group in self.unique_images:

            if not self.isInterruptionRequested():
                # check to see if file exists
                if not Path(filepath).exists():
                    self.logger.warning(f"File {filepath} does not exist, skipping import...")
                    continue

                # get file extension
                ext = Path(filepath).suffix.lower()

                # get remaining information
                exemplar = group.head(1)
                # timestamp
                timestamp = exemplar[self.selected_columns["timestamp"]].item()

                survey_id = self.survey(exemplar)
                station_id = self.station(exemplar, survey_id)
                camera_id = self.camera(exemplar, station_id)

                # Optional data
                sequence_id = int(exemplar[self.selected_columns["sequence_id"]].item()) if self.selected_columns["sequence_id"] != "None" else None
                external_id = int(exemplar[self.selected_columns["external_id"]].item()) if self.selected_columns["external_id"] != "None" else None
                comment = exemplar[self.selected_columns["comment"]].item() if self.selected_columns["comment"] != "None" else None

                hash = get_sha256(filepath)  # Calculate the SHA256 hash of the file

                # insert into table
                media_id = self.mpDB.add_media(filepath,
                                               hash,
                                               ext,
                                               timestamp,
                                               station_id=station_id,
                                               camera_id=camera_id,
                                               sequence_id=sequence_id,
                                               external_id=external_id,
                                               comment=comment)
                # image already added, get correct media_id
                if media_id == "duplicate_error":
                    media_id = self.mpDB.select("media", columns="id", row_cond=f'filepath="{filepath}"')[0][0]
                # save thumbnail for new media
                else:
                    media_thumbnail = save_media_thumbnail(self.thumbnail_dir, filepath, ext)
                    self.mpDB.add_thumbnail("media", media_id, media_thumbnail)

                for i, roi in group.iterrows():
                    # frame number for videos, else 1 if image
                    frame = roi["frame"] if "frame" in group.columns else 0

                    # convert old md bbox format if present, else look for new bbox format, else add filterable empties
                    if "bbox1" in roi:
                        bbox_x = roi["bbox1"]
                        bbox_y = roi["bbox2"]
                        bbox_w = roi["bbox3"]
                        bbox_h = roi["bbox4"]
                    elif "bbox_x" in roi:
                        bbox_x = roi["bbox_x"]
                        bbox_y = roi["bbox_y"]
                        bbox_w = roi["bbox_w"]
                        bbox_h = roi["bbox_h"]
                    else:  # add filterable empties
                        bbox_x = -1
                        bbox_y = -1
                        bbox_w = -1
                        bbox_h = -1

                    # individual
                    individual_id = self.individual(roi)

                    # viewpoint
                    viewpoint = int(roi[self.selected_columns["viewpoint"]]) if self.selected_columns["viewpoint"] != "None" else None

                    # set reviewed to 1 for named images
                    reviewed = 1 if individual_id is not None else 0

                    # do not add emb_id, to be determined later
                    roi_id = self.mpDB.add_roi(media_id,
                                               frame,
                                               bbox_x, bbox_y, bbox_w, bbox_h,
                                               viewpoint=viewpoint,
                                               reviewed=reviewed,
                                               individual_id=individual_id,
                                               emb=0)
                    # save thumbnails
                    roi_thumbnail = save_roi_thumbnail(self.thumbnail_dir, filepath, ext, frame, bbox_x, bbox_y, bbox_w, bbox_h)
                    self.mpDB.add_thumbnail("roi", roi_id, roi_thumbnail)

                    roi_counter += 1
                    self.progress_update.emit(roi_counter)

        if not self.isInterruptionRequested():
            # finished adding media
            self.finished.emit()

    def survey(self, exemplar):
        """Get or create survey"""
        # get active survey
        if len(self.selected_columns['survey']) > 1:
            survey_name = self.selected_columns['survey'][1]
            survey_id = self.mpDB.select("survey", columns="id", row_cond=f'name="{survey_name}"')[0][0]
        # get or create new survey
        else:
            survey_name = exemplar[self.selected_columns["survey"]].item()
            region_name = exemplar[self.selected_columns["region"]].item() if self.selected_columns["region"] != "None" else None
            try:
                survey_id = self.mpDB.select("survey", columns="id", row_cond=f'name="{survey_name}"')[0][0]
            except IndexError:
                survey_id = self.mpDB.add_survey(str(survey_name), region_name, None, None)
        return survey_id

    def station(self, exemplar, survey_id):
        """Get or create station"""
        station_name = exemplar[self.selected_columns["station"]].item()
        try:
            station_id = self.mpDB.select("station", columns="id", row_cond=f'name="{station_name}"')[0][0]
        except IndexError:
            station_id = self.mpDB.add_station(str(station_name), None, None, survey_id)
        return station_id

    def camera(self, exemplar, station_id):
        """Get or create camera"""
        if self.selected_columns["camera"] != "None":
            camera_name = exemplar[self.selected_columns["camera"]].item()
            try:
                camera_name = str(camera_name).strip()
                camera_name = camera_name.replace("'", "''")
                row_cond = f"name = '{camera_name}'"
                rows = self.mpDB.select("camera", columns="id", row_cond=row_cond)
                camera_id = rows[0][0]
            except IndexError:
                camera_id = self.mpDB.add_camera(str(camera_name), station_id)
            return camera_id

    def individual(self, roi):
        """Get or create individual ID"""
        if self.selected_columns["individual"] != "None":
            individual = roi[self.selected_columns["individual"]]
            try:
                individual_id = self.mpDB.select("individual", columns="id", row_cond=f'name="{individual}"')[0][0]
            except IndexError:
                individual_id = self.mpDB.add_individual(str(individual))
        else:  # no individual id, need review
            individual_id = None
        return individual_id


# FOLDER IMPORT ================================================================
class FolderImportThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar

    def __init__(self, mpDB, active_survey, data, station_level, camera_level, logger):
        super().__init__()
        self.mpDB = mpDB
        self.logger = logger
        self.active_survey = active_survey
        self.data = data
        self.station_level = station_level
        self.camera_level = camera_level
        self.default_station = None
        self.thumbnail_dir = load_cfg('THUMBNAIL_DIR')
        # get timezone for timestamp parsing

    def run(self):
        for i, file in self.data.iterrows():
            if not self.isInterruptionRequested():
                filepath = file['filepath']
                timestamp = file['datetime']

                # check to see if file exists
                if not Path(filepath).exists():
                    self.logger.warning(f"File {filepath} does not exist")
                    continue

                # get file extension
                ext = Path(filepath).suffix.lower()

                survey_id = self.active_survey[0]

                # get remaining information
                if self.station_level > 0:
                    station_id = self.station(filepath, survey_id)

                    # add camera if camera level provided, else None
                    if self.camera_level > 0:
                        camera_id = self.camera(filepath, station_id)

                else:
                    # create default station if no station level and use for all media
                    if not self.default_station:
                        self.default_station = self.mpDB.add_station("Default Station", None, None, int(survey_id))
                    station_id = self.default_station

                hash = get_sha256(filepath)  # Calculate the SHA256 hash of the file

                # insert into table, force type
                media_id = self.mpDB.add_media(filepath,
                                               hash,
                                               ext,
                                               str(timestamp),
                                               int(station_id),
                                               camera_id=int(camera_id) if self.camera_level > 0 else None,
                                               sequence_id=None,
                                               external_id=None,
                                               comment=None)
                # save thumbnail
                thumbnail_path = save_media_thumbnail(self.thumbnail_dir, filepath, ext)
                self.mpDB.add_thumbnail("media", media_id, thumbnail_path)

                self.progress_update.emit(i)

        # finished adding media
        self.finished.emit()

    def station(self, filepath, survey_id):
        """Get or create station"""
        station_name = Path(filepath).parts[self.station_level]
        station_name = str(station_name).strip()
        station_name = station_name.replace("'", "''")
        try:
            station_id = self.mpDB.select("station", columns="id", row_cond=f'name="{station_name}"')[0][0]
        except IndexError:
            station_id = self.mpDB.add_station(station_name, None, None, survey_id)
        return station_id
    
    def camera(self, filepath, station_id):
        camera_name = Path(filepath).parts[self.camera_level]
        camera_name = str(camera_name).strip()
        camera_name = camera_name.replace("'", "''")
        try:
            camera_id = self.mpDB.select("camera", columns="id", row_cond=f"name='{camera_name}'")[0][0]
        except IndexError:
            camera_id = self.mpDB.add_camera(str(camera_name), station_id)

        return camera_id

