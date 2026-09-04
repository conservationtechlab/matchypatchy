"""
QThreads for Importing Data

"""
import os
import pandas as pd
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.database.thumbnails import save_media_thumbnail, save_roi_thumbnail, THUMBNAIL_NOTFOUND
from matchypatchy.database.media import get_sha256
from matchypatchy.config import asset_path



# CSV MIGRATE ==================================================================
class CSVMigrateThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    error_update = pyqtSignal(list)  # Signal to update the error log

    EXPECTED_COLUMNS = {'id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
                        'reviewed', 'media_id', 'individual_id', 'emb', 'base_dir_id',
                        'relative_path', 'ext', 'timestamp', 'station_id', 'sequence_id',
                        'camera_id', 'external_id', 'comment', 'favorite', 'name', 'sex', 'age',
                        'filepath', 'station_name', 'lat', 'long', 'station_survey_id',
                        'survey_name', 'region_name', 'camera_name'}

    def __init__(self, parent, data):
        super().__init__()
        self.mpDB = parent.mpDB
        self.logger = parent.logger
        self.cfg = parent.cfg
        self.data = data
        self.thumbnail_dir = self.cfg.THUMBNAIL_DIR
        self.base_dir_ref = {}  # dictionary to store base directory path to id mapping
        self.station_ref = {}  # dictionary to store survey name to id mapping
        self.camera_ref = {}  # dictionary to store camera name to id mapping
        self.individual_ref = {}  # dictionary to store individual name to id mapping
        self.sequence_ref = {}  # dictionary to store sequence id mapping
        self.errors = []  # list to store errors encountered during import

        assert isinstance(self.data, pd.DataFrame), "Data must be a pandas DataFrame"
        missing_columns = self.EXPECTED_COLUMNS - set(self.data.columns)
        if missing_columns:
            raise ValueError(f"Data cannot be imported as it is missing the following required columns: {missing_columns}")

    def run(self):
        roi_counter = 0  # progressbar counter

        for row in self.data.itertuples(index=False):
            if not self.isInterruptionRequested():

                # get survey id, create if not exists
                survey_id = self.survey(row.survey_name, row.region_name)
                # station
                new_station_id = self.station(row.station_id, row.station_name, survey_id, row.lat, row.long)
                # camera
                new_camera_id = self.camera(new_station_id, row.camera_id, row.camera_name)

                # base directory
                new_base_dir_id = self._get_base_dir(row.base_dir_id, row.filepath, row.relative_path)
                # hash
                hash = get_sha256(row.filepath)
                if hash is None:
                    self.logger.warning(f"File {row.filepath} does not exist, skipping import...")
                    self.errors.append(row.filepath)
                    continue

                # new sequence id
                sequence_id = self.sequence(row.sequence_id)

                # media
                media_id = self.mpDB.add_media(new_base_dir_id,
                                               row.relative_path,
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

    def _get_base_dir(self, old_base_dir_id, filepath, relative_path):
        """Get the common base directory for a list of filepaths"""
        if old_base_dir_id in self.base_dir_ref:
            return self.base_dir_ref[old_base_dir_id]

        if not filepath or not relative_path:
            return None

        full_path = Path(filepath)
        rel_path = Path(relative_path)
        base_dir = Path(*full_path.parts[:-len(rel_path.parts)])

        # add to uploads table
        new_base_dir_id = self.mpDB.add_upload(str(base_dir))
        # add to ref
        self.base_dir_ref[old_base_dir_id] = new_base_dir_id

        return new_base_dir_id

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
    """Thread for importing CSV data into the database."""

    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    progress_message = pyqtSignal(str)  # Signal to reset the progress bar

    # How many ROIs to process between progress signal emissions.
    # Raising this reduces cross-thread signal overhead on large imports.
    PROGRESS_BATCH_SIZE = 10

    def __init__(self, parent, unique_images, selected_columns, active_survey):
        super().__init__()
        self.logger = parent.logger
        self.mpDB = parent.mpDB
        self.cfg = parent.cfg
        self.unique_images = unique_images
        self.selected_columns = selected_columns
        self.active_survey = active_survey
        self.thumbnail_dir = self.cfg.THUMBNAIL_DIR
        self.station_ref = {}
        self.camera_ref = {}
        self.individual_ref = {}
        self.sequence_ref = {}
        # NEW: cache survey lookups too -- previously every group re-queried the DB
        self.survey_ref = {}

    def run(self):
        roi_counter = 0  # progressbar counter
        emitted_counter = 0  # last value emitted, to batch signal emission
        self.progress_message.emit("Starting import...")

        # get common base directory for all images
        base_dir = self._get_base_dir(list(self.unique_images.groups.keys()))
        try:
            base_dir_id = self.mpDB.select("uploads", columns="id", row_cond=f'base_dir="{base_dir}"')[0][0]
        except IndexError:
            base_dir_id = self.mpDB.add_upload(base_dir)

        try:
            for filepath, group in self.unique_images:
                if self.isInterruptionRequested():
                    break

                # check to see if file exists
                if not Path(filepath).exists():
                    self.logger.warning(f"File {filepath} does not exist, skipping import...")
                    continue

                # get the relative path of the file with respect to the base directory
                relative_path = self._get_relative_path(filepath, base_dir)
                # get file extension
                ext = Path(filepath).suffix.lower()
                # Calculate the SHA256 hash of the file
                hash = get_sha256(filepath)

                # get remaining information
                exemplar = group.head(1).to_dict(orient='records')[0]
                # timestamp
                timestamp = exemplar.get(self.selected_columns["timestamp"])

                # get survey, station, and camera IDs
                survey_id = self.survey(exemplar)
                station_id = self.station(exemplar, survey_id)
                camera_id = self.camera(exemplar, station_id)

                # insert into table
                media_id = self.mpDB.add_media(base_dir_id,
                                               relative_path,
                                               hash,
                                               ext,
                                               timestamp,
                                               station_id=station_id,
                                               camera_id=camera_id,
                                               sequence_id=self.sequence(exemplar),
                                               external_id=self.external(exemplar),
                                               comment=self.comment(exemplar),
                                               commit=False)
                # image already added, get correct media_id
                if media_id == "duplicate_error":
                    media_id = self.mpDB.select("media", columns="id", row_cond=f'sha256="{hash}"')[0][0]
                # save thumbnail for new media
                else:
                    media_thumbnail = save_media_thumbnail(self.thumbnail_dir, filepath, ext)
                    self.mpDB.add_thumbnail("media", media_id, media_thumbnail)

                # add rois
                for roi in group.itertuples(index=False):
                    # frame number for videos, else 1 if image
                    frame = roi.frame if "frame" in group.columns else 0

                    # convert old md bbox format if present, else look for new bbox format, else add filterable empties
                    if "bbox1" in roi._fields:
                        bbox_x = roi.bbox1
                        bbox_y = roi.bbox2
                        bbox_w = roi.bbox3
                        bbox_h = roi.bbox4
                    elif "bbox_x" in roi._fields:
                        bbox_x = roi.bbox_x
                        bbox_y = roi.bbox_y
                        bbox_w = roi.bbox_w
                        bbox_h = roi.bbox_h
                    else:  # add filterable empties
                        bbox_x = -1
                        bbox_y = -1
                        bbox_w = -1
                        bbox_h = -1

                    # viewpoint
                    viewpoint_col = self.selected_columns["viewpoint"]
                    viewpoint_value = self._roi_value(roi, viewpoint_col)
                    viewpoint = self._convert_to_int(viewpoint_value) if viewpoint_col != "None" else None

                    # individual
                    individual_id = self.individual(roi)
                    # set reviewed to 1 for named images
                    reviewed = 1 if individual_id is not None else 0

                    favorite = self.favorite(roi)

                    # do not add emb_id, to be determined later
                    roi_id = self.mpDB.add_roi(media_id,
                                               frame,
                                               bbox_x, bbox_y, bbox_w, bbox_h,
                                               viewpoint=viewpoint,
                                               reviewed=reviewed,
                                               individual_id=individual_id,
                                               favorite=favorite,
                                               emb=0,
                                               commit=False)
                    # save thumbnails
                    if bbox_w == -1:
                        roi_thumbnail = asset_path(THUMBNAIL_NOTFOUND)
                        self.mpDB.add_thumbnail("roi", roi_id, str(roi_thumbnail), commit=False)
                    else:
                        roi_thumbnail = save_roi_thumbnail(self.thumbnail_dir, filepath, ext,
                                                           frame, bbox_x, bbox_y, bbox_w, bbox_h)
                        self.mpDB.add_thumbnail("roi", roi_id, str(roi_thumbnail), commit=False)

                    roi_counter += 1

                    # bank progress updates and commit in batches
                    if roi_counter - emitted_counter >= self.PROGRESS_BATCH_SIZE:
                        self.progress_update.emit(roi_counter)
                        emitted_counter = roi_counter
                        self.mpDB.db.commit()

        except Exception:
            self.mpDB.db.rollback()
            raise

        # make sure the progress bar reaches its true final value
        if emitted_counter != roi_counter:
            self.progress_update.emit(roi_counter)

        if not self.isInterruptionRequested():
            # finished adding media
            self.mpDB.db.commit()  # commit anything remaining
            self.finished.emit()

    def _get_base_dir(self, filepaths):
        """Get the common base directory for a list of filepaths"""
        if not filepaths:
            return None

        # Convert all to absolute paths T
        paths = [Path(fp).resolve() for fp in filepaths]
        # Then get parents and commonpath
        parents = [p.parent for p in paths]
        base_dir = Path(os.path.commonpath(parents))
        return str(base_dir)

    def _get_relative_path(self, filepath, base_dir):
        """Get the relative path of a file given its base directory"""
        return str(Path(filepath).relative_to(base_dir))

    def survey(self, exemplar):
        """Get or create survey"""
        # NEW: cache by resolved survey name/default so we don't hit the DB
        # for every image group -- surveys rarely vary within a single import.
        if self.selected_columns["survey"] is None:
            cache_key = self.active_survey
        else:
            cache_key = self._convert_to_str(exemplar.get(self.selected_columns["survey"]))

        if cache_key in self.survey_ref:
            return self.survey_ref[cache_key]

        survey_id = None
        if self.selected_columns["survey"] is None:
            survey_id = self.mpDB.select("survey", columns="id", row_cond=f'name="{self.active_survey}"')[0][0]
        else:
            survey_name = cache_key
            try:
                survey_id = self.mpDB.select("survey", columns="id", row_cond=f'name="{survey_name}"')[0][0]
            except IndexError:
                region_name = exemplar.get(self.selected_columns["region"])
                region_name = self._convert_to_str(region_name)
                survey_id = self.mpDB.add_survey(str(survey_name), region_name, None, None)

        self.survey_ref[cache_key] = survey_id
        return survey_id

    def station(self, exemplar, survey_id):
        """Get or create station"""
        station_name = exemplar.get(self.selected_columns["station"])
        station_name = self._convert_to_str(station_name)
        # check reference dictionary first
        if station_name in self.station_ref:
            return self.station_ref[station_name]
        try:
            station_id = self.mpDB.select("station", columns="id", row_cond=f'name="{station_name}"')[0][0]
        except IndexError:
            lat = exemplar.get(self.selected_columns["lat"])
            lat = self._convert_to_float(lat)
            long = exemplar.get(self.selected_columns["long"])
            long = self._convert_to_float(long)
            station_id = self.mpDB.add_station(str(station_name), lat, long, survey_id)
        self.station_ref[station_name] = station_id
        return station_id

    # OPTIONAL -----------------------------------------------------------------
    def camera(self, exemplar, station_id):
        """Get or create camera"""
        camera_id = None
        camera_name = exemplar.get(self.selected_columns["camera"])
        if camera_name is not None:
            # check reference dictionary first
            if camera_name in self.camera_ref:
                return self.camera_ref[camera_name]
            camera_name = self._convert_to_str(camera_name)
            try:
                camera_id = self.mpDB.select("camera", columns="id", row_cond=f"name='{camera_name}'")[0][0]
            except IndexError:
                camera_id = self.mpDB.add_camera(str(camera_name), station_id)
            self.camera_ref[camera_name] = camera_id
        return camera_id

    def sequence(self, exemplar):
        """Get or create sequence ID, not required for import"""
        sequence_id = None
        old_sequence_id = exemplar.get(self.selected_columns["sequence_id"])
        if old_sequence_id is not None:
            try:
                # get sequence id from reference dictionary first
                sequence_id = self.sequence_ref[old_sequence_id]
            except KeyError:
                sequence_id = self.mpDB.add_sequence()
                self.sequence_ref[old_sequence_id] = sequence_id
        return sequence_id

    def external(self, exemplar):
        """Get external ID"""
        external_id = exemplar.get(self.selected_columns["external_id"])
        external_id = self._convert_to_int(external_id)
        return external_id

    def comment(self, exemplar):
        """Get comment"""
        comment = exemplar.get(self.selected_columns["comment"])
        comment = self._convert_to_str(comment)
        return comment

    # ROI-RELATED METHODS
    def _roi_value(self, roi, column):
        """Get ROI value by selected column supporting string or integer references."""
        if column == "None" or column is None:
            return None
        if isinstance(column, int):
            return roi[column]
        return getattr(roi, column, None)

    def individual(self, roi):
        """Get or create individual ID"""
        individual_id = None
        if self.selected_columns["individual"] != "None":
            individual_name = self._roi_value(roi, self.selected_columns["individual"])
            individual_name = self._convert_to_str(individual_name)
            if individual_name is None:
                return None
            # check reference dictionary first
            if individual_name in self.individual_ref:
                return self.individual_ref[individual_name]
            try:
                individual_id = self.mpDB.select("individual", columns="id", row_cond=f'name="{individual_name}"')[0][0]
            except IndexError:
                sex = None
                age = None
                #TODO: limit sex and age to valid values
                if self.selected_columns["sex"] != "None":
                    sex = self._roi_value(roi, self.selected_columns["sex"])
                    sex = self._convert_to_str(sex)
                if self.selected_columns["age"] != "None":
                    age = self._roi_value(roi, self.selected_columns["age"])
                    age = self._convert_to_str(age)
                individual_id = self.mpDB.add_individual(individual_name, sex, age)
            self.individual_ref[individual_name] = individual_id
        return individual_id

    def favorite(self, roi):
        """Get favorite status"""
        if self.selected_columns["favorite"] != "None":
            favorite = self._roi_value(roi, self.selected_columns["favorite"])
            favorite = self._convert_to_int(favorite)
            return favorite if favorite is not None else 0
        # If favorite column is not specified, default to 0
        return 0

    def _convert_to_str(self, value):
        """Convert a value to a stripped string, handling None"""
        if value is None:
            return None
        if pd.isna(value):
            return None
        try:
            value = str(value).strip()
            value = value.replace("'", "''")
            return value
        except (ValueError, TypeError):
            return None

    def _convert_to_int(self, value):
        """Convert a value to an integer, handling None"""
        if value is None:
            return None
        if pd.isna(value):
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _convert_to_float(self, value):
        """Convert a value to a float, handling None"""
        if value is None:
            return None
        if pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


# FOLDER IMPORT ================================================================
class FolderImportThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar

    def __init__(self, parent, active_survey, data, station_level, camera_level):
        super().__init__()
        self.mpDB = parent.mpDB
        self.logger = parent.logger
        self.active_survey = active_survey
        self.data = data
        self.station_level = station_level
        self.camera_level = camera_level
        self.default_station = None
        self.thumbnail_dir = parent.cfg.THUMBNAIL_DIR
        # get timezone for timestamp parsing

    def run(self):
        # get base directory for the files being imported
        base_dir = self._get_base_dir(self.data['filepath'].tolist())
        try:
            base_dir_id = self.mpDB.select("uploads", columns="id", row_cond=f'base_dir="{base_dir}"')[0][0]
        except IndexError:
            base_dir_id = self.mpDB.add_upload(base_dir)

        for i, file in self.data.iterrows():
            if not self.isInterruptionRequested():

                filepath = file['filepath']
                # check to see if file exists
                if not Path(filepath).exists():
                    self.logger.warning(f"File {filepath} does not exist")
                    continue

                # get the relative path of the file with respect to the base directory
                relative_path = self._get_relative_path(filepath, base_dir)
                hash = get_sha256(filepath)  # Calculate the SHA256 hash of the file
                # get file extension
                ext = Path(filepath).suffix.lower()

                timestamp = file['datetime']

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

                # insert into table, force type
                media_id = self.mpDB.add_media(base_dir_id,
                                               relative_path,
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

    def _get_base_dir(self, filepaths):
        """Get the common base directory for a list of filepaths"""
        if not filepaths:
            return None

        paths = [Path(p) for p in filepaths]
        common = Path(os.path.commonpath([p.parent for p in paths]))
        return str(common)

    def _get_relative_path(self, filepath, base_dir):
        """Get the relative path of a file given its base directory"""
        return str(Path(filepath).relative_to(base_dir))

    def station(self, filepath, survey_id):
        """Get or create station"""
        station_name = Path(filepath).parts[self.station_level]
        station_name = str(station_name)
        try:
            station_id = self.mpDB.select("station", columns="id", row_cond=f'name="{station_name}"')[0][0]
        except IndexError:
            station_id = self.mpDB.add_station(station_name, None, None, survey_id)
        return station_id

    def camera(self, filepath, station_id):
        camera_name = Path(filepath).parts[self.camera_level]
        camera_name = str(camera_name)
        try:
            camera_id = self.mpDB.select("camera", columns="id", row_cond=f"name='{camera_name}'")[0][0]
        except IndexError:
            camera_id = self.mpDB.add_camera(camera_name, station_id)

        return camera_id


# BASE PATH UPDATE =============================================================
class BasePathUpdateThread(QThread):
    progress_update = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, mpDB, base_dir_id, new_base_dir):
        super().__init__()
        self.mpDB = mpDB
        self.base_dir_id = base_dir_id
        self.new_base_dir = new_base_dir

    def run(self):
        if not self.isInterruptionRequested():
            success = self.mpDB.update_base_dir(self.base_dir_id, self.new_base_dir)
            self.progress_update.emit(1 if success else 0)
        self.finished.emit()
