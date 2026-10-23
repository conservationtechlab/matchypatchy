"""
QThreads for Importing Data

"""
import os
import logging
import time
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.database.thumbnails import save_media_thumbnail, save_roi_thumbnail, THUMBNAIL_NOTFOUND
from matchypatchy.database.media import get_sha256
from matchypatchy.database.mpdb import sql_text


logger = logging.getLogger(__name__)


def roi_key(frame, bbox_x, bbox_y, bbox_w, bbox_h):
    """Identify a roi by frame and bbox, rounded the same way add_roi stores them."""
    return (int(frame),) + tuple(round(float(b), 4) for b in (bbox_x, bbox_y, bbox_w, bbox_h))


def count_existing_rois(mpDB, media_id):
    """Return a count of each roi key already in the database for media_id."""
    rows = mpDB.select("roi", columns="frame, bbox_x, bbox_y, bbox_w, bbox_h",
                       row_cond=f'media_id={media_id}')
    return Counter(roi_key(*row) for row in rows or [])


class ThumbnailQueue:
    """
    Make thumbnails on a pool of worker threads, recording each in the database once it is saved.

    Used by CSVMigrateThread, CSVImportThread and FolderImportThread in place of calling
    save_media_thumbnail/save_roi_thumbnail directly. Decoding images is nearly all the
    time an import spends per file and OpenCV releases the GIL while decoding, so files
    are decoded side by side. The database connection belongs to the import thread, so
    workers only save files: add() queues the work and the add_thumbnail rows are written
    from the import thread, as add() waits for the oldest work or when finish() is called.
    Kept as a class rather than inlined so the three imports share the bounded queue and
    the rule that finish() must run before the final commit.
    """
    # queued work per worker, enough to keep workers busy without decoding far ahead of the database
    PENDING_PER_WORKER = 2

    def __init__(self, mpDB, workers=None):
        self.mpDB = mpDB
        self.workers = workers or min(8, os.cpu_count() or 1)
        self.pool = ThreadPoolExecutor(self.workers, thread_name_prefix="thumbnail")
        self.pending = deque()

    def add(self, table, fid, save, *args):
        """Save a thumbnail with save(*args) in the background and record it for fid in table"""
        self.pending.append((table, fid, self.pool.submit(save, *args)))
        while len(self.pending) > self.workers * self.PENDING_PER_WORKER:
            self._record_oldest()

    def finish(self):
        """Wait for all queued thumbnails and record them, call before the final commit"""
        while self.pending:
            self._record_oldest()

    def close(self):
        """Stop the workers, dropping thumbnails not yet started, eg. after an import fails"""
        self.pool.shutdown(wait=True, cancel_futures=True)

    def _record_oldest(self):
        """Wait for the oldest queued thumbnail and add its row; a worker's exception is raised here"""
        table, fid, future = self.pending.popleft()
        self.mpDB.add_thumbnail(table, fid, future.result(), commit=False)


# CSV MIGRATE ==================================================================
class CSVMigrateThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    error_update = pyqtSignal(list)  # Signal to update the error log
    import_failed = pyqtSignal(str)  # Signal to report a fatal import error

    # How many ROIs to process between progress signal emissions.
    PROGRESS_BATCH_SIZE = 10
    # Seconds between commits. Each commit waits for the disk (~15 ms), so committing with
    # every progress update cost more than adding the rows; a short interval keeps the write
    # lock from being held long. An interrupted import is resumed by importing again.
    COMMIT_INTERVAL = 1.0

    EXPECTED_COLUMNS = {'id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
                        'reviewed', 'media_id', 'individual_id', 'emb', 'base_dir_id',
                        'relative_path', 'ext', 'timestamp', 'station_id', 'sequence_id',
                        'camera_id', 'external_id', 'comment', 'favorite', 'name', 'sex',
                        'filepath', 'station_name', 'lat', 'long', 'station_survey_id',
                        'survey_name', 'region_name', 'camera_name'}

    def __init__(self, parent, data):
        super().__init__()
        self.mpDB = parent.mpDB
        self.cfg = parent.cfg
        self.data = data
        self.thumbnail_dir = self.cfg.THUMBNAIL_DIR
        self.base_dir_ref = {}  # dictionary to store base directory path to id mapping
        self.survey_ref = {}  # dictionary to store survey name to id mapping
        self.station_ref = {}  # dictionary to store survey name to id mapping
        self.camera_ref = {}  # dictionary to store camera name to id mapping
        self.individual_ref = {}  # dictionary to store individual name to id mapping
        self.sequence_ref = {}  # dictionary to store sequence id mapping
        self.media_ref = {}  # dictionary to store file hash to media id mapping
        self.skipped_ref = set()  # hashes of files skipped because a different file has their path
        self.existing_roi_ref = {}  # dictionary to store media id to count of rois already in the project
        self.errors = []  # list to store errors encountered during import

        assert isinstance(self.data, pd.DataFrame), "Data must be a pandas DataFrame"
        missing_columns = self.EXPECTED_COLUMNS - set(self.data.columns)
        if missing_columns:
            raise ValueError(f"Data cannot be imported as it is missing the following required columns: {missing_columns}")

    def run(self):
        roi_counter = 0  # progressbar counter
        emitted_counter = 0  # last value emitted, to batch signal emission
        last_commit = time.monotonic()
        thumbnails = ThumbnailQueue(self.mpDB)

        try:
            for row in self.data.itertuples(index=False):
                if self.isInterruptionRequested():
                    break

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
                    logger.warning(f"File {row.filepath} does not exist, skipping import...")
                    self.errors.append(row.filepath)
                    continue

                # new sequence id
                sequence_id = self.sequence(row.sequence_id)

                # a different file was already at this path, its other rois are skipped too
                if hash in self.skipped_ref:
                    continue

                # media, each roi of a file is its own row so only the first adds it
                media_id = self.media_ref.get(hash)
                if media_id is None:
                    media_id = self.mpDB.add_media(new_base_dir_id,
                                                   row.relative_path,
                                                   hash,
                                                   row.ext,
                                                   row.timestamp,
                                                   station_id=new_station_id,
                                                   camera_id=new_camera_id,
                                                   sequence_id=sequence_id,
                                                   external_id=row.external_id if not pd.isna(row.external_id) else None,
                                                   comment=row.comment if not pd.isna(row.comment) else None,
                                                   commit=False)

                    if media_id == "duplicate_path":
                        # don't attach its rois to the file already at that path
                        logger.warning(f"A different file is already in the project at {row.filepath}, skipping import...")
                        self.errors.append(row.filepath)
                        self.skipped_ref.add(hash)
                        continue
                    elif media_id == "duplicate_hash":
                        # already in the project; media has no filepath column, but the file's hash is unique
                        media_id = self.mpDB.select("media", columns="id", row_cond=f"sha256='{hash}'")[0][0]
                        self.existing_roi_ref[media_id] = count_existing_rois(self.mpDB, media_id)
                    else:
                        # save thumbnail for new media
                        thumbnails.add("media", media_id, save_media_thumbnail,
                                       self.thumbnail_dir, row.filepath, row.ext)
                        self.existing_roi_ref[media_id] = Counter()
                    self.media_ref[hash] = media_id

                # get bounding box coordinates, if any are missing, set to -1
                bbox_x = row.bbox_x if not pd.isna(row.bbox_x) else -1
                bbox_y = row.bbox_y if not pd.isna(row.bbox_y) else -1
                bbox_w = row.bbox_w if not pd.isna(row.bbox_w) else -1
                bbox_h = row.bbox_h if not pd.isna(row.bbox_h) else -1

                # skip rois already in the project (eg. resuming an interrupted migration)
                # each existing roi accounts for one row, so repeated keys (eg. -1 bboxes) are counted
                existing_rois = self.existing_roi_ref[media_id]
                key = roi_key(row.frame, bbox_x, bbox_y, bbox_w, bbox_h)
                if existing_rois[key] > 0:
                    existing_rois[key] -= 1
                    roi_counter += 1
                    continue

                # individual
                individual_id = self.individual(row.individual_id, row.name, row.sex)

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
                                        emb=0,  # do not add emb, must be reprocessed in new project
                                        commit=False)
                # save thumbnail for new roi, a box-less one has nothing to crop
                if bbox_w != -1:
                    thumbnails.add("roi", rid, save_roi_thumbnail, self.thumbnail_dir, row.filepath, row.ext,
                                   row.frame, bbox_x, bbox_y, bbox_w, bbox_h)
                    # a roi with a box was already detected, a box-less one still needs the detector
                    self.mpDB.mark_detection_done([media_id], commit=False)

                roi_counter += 1

                # bank progress updates in batches, commit on an interval
                if roi_counter - emitted_counter >= self.PROGRESS_BATCH_SIZE:
                    self.progress_update.emit(roi_counter)
                    emitted_counter = roi_counter
                if time.monotonic() - last_commit >= self.COMMIT_INTERVAL:
                    self.mpDB.db.commit()
                    last_commit = time.monotonic()

            thumbnails.finish()
            self.mpDB.db.commit()  # commit anything remaining

        except Exception as error:
            # an unhandled exception in a QThread aborts the whole app, report it instead
            self.mpDB.db.rollback()
            logger.exception("Import failed")
            self.import_failed.emit(str(error))
            return
        finally:
            thumbnails.close()

        # make sure the progress bar reaches its true final value
        if emitted_counter != roi_counter:
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

        # reuse the upload if this directory is already in the project, else add it
        try:
            new_base_dir_id = self.mpDB.select("uploads", columns="id", row_cond=f'base_dir={sql_text(str(base_dir))}')[0][0]
        except IndexError:
            new_base_dir_id = self.mpDB.add_upload(str(base_dir))
            if new_base_dir_id is None:
                raise RuntimeError(f"Failed to add upload '{base_dir}', see log for database error")
        # add to ref
        self.base_dir_ref[old_base_dir_id] = new_base_dir_id

        return new_base_dir_id

    def survey(self, survey_name, region_name):
        """Get or create survey"""
        # check reference dictionary first
        if survey_name in self.survey_ref:
            return self.survey_ref[survey_name]
        try:
            survey_id = self.mpDB.select("survey", columns="id", row_cond=f'name={sql_text(survey_name)}')[0][0]
        except IndexError:
            region_id = self.region(region_name) if not pd.isna(region_name) else None
            survey_id = self.mpDB.add_survey(str(survey_name), region_id, None, None)
            if survey_id is None:
                raise RuntimeError(f"Failed to add survey '{survey_name}' (region: {region_name}), see log for database error")
        self.survey_ref[survey_name] = survey_id
        return survey_id

    def region(self, region_name):
        """Get or create region"""
        try:
            region_id = self.mpDB.select("region", columns="id", row_cond=f'name={sql_text(region_name)}')[0][0]
        except IndexError:
            region_id = self.mpDB.add_region(str(region_name), None)
            if region_id is None:
                raise RuntimeError(f"Failed to add region '{region_name}', see log for database error")
        return region_id

    def station(self, old_station_id, station_name, survey_id, lat, long):
        """Get or create station"""
        try:
            station_id = self.station_ref[old_station_id]
        except KeyError:
            try:
                row_cond = f'name={sql_text(station_name)} AND survey_id={int(survey_id)}'
                station_id = self.mpDB.select("station", columns="id", row_cond=row_cond)[0][0]
            except IndexError:
                station_id = self.mpDB.add_station(str(station_name),
                                                   lat if not pd.isna(lat) else None,
                                                   long if not pd.isna(long) else None,
                                                   survey_id)
                if station_id is None:
                    raise RuntimeError(f"Failed to add station '{station_name}' (survey_id: {survey_id}), see log for database error")
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
                    row_cond = f"name={sql_text(camera_name)} AND station_id={int(station_id)}"
                    rows = self.mpDB.select("camera", columns="id", row_cond=row_cond)
                    camera_id = rows[0][0]
                # if not in database, add camera
                except IndexError:
                    camera_id = self.mpDB.add_camera(str(camera_name), station_id)
                    if camera_id is None:
                        raise RuntimeError(f"Failed to add camera '{camera_name}' (station_id: {station_id}), see log for database error")
                # add camera id to reference dictionary
                self.camera_ref[old_camera_id] = camera_id
            return camera_id
        # if no camera name, return None
        else:
            return None

    def individual(self, old_individual_id, name, sex):
        """Get or create individual ID, not required for import"""
        if not pd.isna(old_individual_id):
            try:
                # get individual id from reference dictionary first
                individual_id = self.individual_ref[old_individual_id]
            except KeyError:
                # get individual id from database if not in reference dictionary
                try:
                    individual_id = self.mpDB.select("individual", columns="id", row_cond=f'name={sql_text(name)}')[0][0]
                # if not in database, add individual
                except IndexError:
                    individual_id = self.mpDB.add_individual(str(name), sex if not pd.isna(sex) else None)
                # add individual id to reference dictionary
                self.individual_ref[old_individual_id] = individual_id
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
    import_failed = pyqtSignal(str)  # Signal to report a fatal import error

    # How many ROIs to process between progress signal emissions.
    # Raising this reduces cross-thread signal overhead on large imports.
    PROGRESS_BATCH_SIZE = 10
    # Seconds between commits. Each commit waits for the disk (~15 ms), so committing with
    # every progress update cost more than adding the rows; a short interval keeps the write
    # lock from being held long. An interrupted import is resumed by importing again.
    COMMIT_INTERVAL = 1.0

    def __init__(self, parent, unique_images, selected_columns, active_survey):
        super().__init__()
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
        last_commit = time.monotonic()
        thumbnails = ThumbnailQueue(self.mpDB)
        self.progress_message.emit("Starting import...")

        # get common base directory for all images
        files = self._files()
        base_dir = self._get_base_dir([filepath for filepath, _, _ in files])
        try:
            base_dir_id = self.mpDB.select("uploads", columns="id", row_cond=f'base_dir={sql_text(base_dir)}')[0][0]
        except IndexError:
            base_dir_id = self.mpDB.add_upload(base_dir)

        try:
            for filepath, exemplar, rois in files:
                if self.isInterruptionRequested():
                    break

                # check to see if file exists
                if not Path(filepath).exists():
                    logger.warning(f"File {filepath} does not exist, skipping import...")
                    continue

                # get the relative path of the file with respect to the base directory
                relative_path = self._get_relative_path(filepath, base_dir)
                # get file extension
                ext = Path(filepath).suffix.lower()
                # Calculate the SHA256 hash of the file
                hash = get_sha256(filepath)

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
                # a different file is already at this path, skip rather than attach rois to it
                if media_id == "duplicate_path":
                    logger.warning(f"A different file is already in the project at {filepath}, skipping import...")
                    continue
                # image already added, get correct media_id and its existing rois
                elif media_id == "duplicate_hash":
                    media_id = self.mpDB.select("media", columns="id", row_cond=f'sha256="{hash}"')[0][0]
                    existing_rois = count_existing_rois(self.mpDB, media_id)
                # save thumbnail for new media
                else:
                    existing_rois = Counter()
                    thumbnails.add("media", media_id, save_media_thumbnail, self.thumbnail_dir, filepath, ext)

                # add rois
                for roi in rois:
                    # frame number for videos, else 1 if image
                    frame = roi.frame if "frame" in roi._fields else 0

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
                    # blank cells (eg. images without a detection) are box-less rois, not a failed import
                    if any(pd.isna(b) for b in (bbox_x, bbox_y, bbox_w, bbox_h)):
                        bbox_x = bbox_y = bbox_w = bbox_h = -1
                    if pd.isna(frame):
                        frame = 0

                    # skip rois already imported (eg. resuming an interrupted import)
                    # each existing roi accounts for one row, so repeated keys (eg. -1 bboxes) are counted
                    key = roi_key(frame, bbox_x, bbox_y, bbox_w, bbox_h)
                    if existing_rois[key] > 0:
                        existing_rois[key] -= 1
                        roi_counter += 1
                        continue

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
                    if bbox_w != -1:
                        thumbnails.add("roi", roi_id, save_roi_thumbnail, self.thumbnail_dir, filepath, ext,
                                       frame, bbox_x, bbox_y, bbox_w, bbox_h)
                        # a roi with a box was already detected, a box-less one still needs the detector
                        self.mpDB.mark_detection_done([media_id], commit=False)

                    roi_counter += 1

                    # bank progress updates in batches, commit on an interval
                    if roi_counter - emitted_counter >= self.PROGRESS_BATCH_SIZE:
                        self.progress_update.emit(roi_counter)
                        emitted_counter = roi_counter
                    if time.monotonic() - last_commit >= self.COMMIT_INTERVAL:
                        self.mpDB.db.commit()
                        last_commit = time.monotonic()

            thumbnails.finish()
            self.mpDB.db.commit()  # commit anything remaining

        except Exception as error:
            # an unhandled exception in a QThread aborts the whole app, report it instead
            self.mpDB.db.rollback()
            logger.exception("Import failed")
            self.import_failed.emit(str(error))
            return
        finally:
            thumbnails.close()

        # make sure the progress bar reaches its true final value
        if emitted_counter != roi_counter:
            self.progress_update.emit(roi_counter)

        if not self.isInterruptionRequested():
            # finished adding media
            self.finished.emit()

    def _files(self):
        """
        List (filepath, exemplar, rois) for each file, in the order iterating the groupby gives.

        Called once by run() in place of iterating self.unique_images. Iterating a groupby
        builds a DataFrame per file, and calling to_dict/itertuples on each small frame cost
        several ms per file, most of a CSV import's time. One itertuples over the whole table,
        grouped in Python, gives the same rows. exemplar is the file's first row keyed by column
        name, as group.head(1).to_dict(orient='records')[0] gave; rois are its rows as
        namedtuples, as group.itertuples(index=False) gave.
        """
        data = self.unique_images.obj
        key = self.unique_images.keys
        key = key[0] if isinstance(key, list) else key
        rows = {}
        for filepath, row in zip(data[key], data.itertuples(index=False)):
            # groupby leaves out rows without a filepath
            if self.unique_images.dropna and pd.isna(filepath):
                continue
            rows.setdefault(filepath, []).append(row)
        filepaths = sorted(rows) if self.unique_images.sort else rows
        return [(filepath, self._exemplar(data.columns, rows[filepath][0]), rows[filepath]) for filepath in filepaths]

    def _exemplar(self, columns, row):
        """
        A file's first row as a dict keyed by column name, with pd.NA read as None like to_dict gives.

        Called by _files; kept separate so the NA rule sits apart from the grouping.
        """
        return {column: None if value is pd.NA else value for column, value in zip(columns, row)}

    def _get_base_dir(self, filepaths):
        """Get the common base directory for a list of filepaths"""
        if not filepaths:
            return None

        # Convert all to absolute paths. Use abspath rather than resolve():
        # on Windows resolve() expands mapped drives (H:\) to UNC paths (\\server\share)
        paths = [Path(os.path.abspath(fp)) for fp in filepaths]
        # Then get parents and commonpath
        parents = [p.parent for p in paths]
        try:
            base_dir = Path(os.path.commonpath(parents))
            return str(base_dir)
        except ValueError:
            # If the paths are on different drives, commonpath will raise a ValueError.
            logger.error("Filepaths are on different drives, cannot determine a common base directory.")
            return None

    def _get_relative_path(self, filepath, base_dir):
        """Get the relative path of a file given its base directory"""
        # If base_dir is None, return the parent directory of the filepat
        if base_dir is None:
            return Path(filepath).parent
        return str(Path(os.path.abspath(filepath)).relative_to(base_dir))

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
            survey_id = self.mpDB.select("survey", columns="id", row_cond=f'name={sql_text(self.active_survey)}')[0][0]
        else:
            survey_name = cache_key
            try:
                survey_id = self.mpDB.select("survey", columns="id", row_cond=f'name={sql_text(survey_name)}')[0][0]
            except IndexError:
                region_name = exemplar.get(self.selected_columns["region"])
                region_name = self._convert_to_str(region_name)
                region_id = self.region(region_name) if region_name is not None else None
                survey_id = self.mpDB.add_survey(str(survey_name), region_id, None, None)
                if survey_id is None:
                    raise RuntimeError(f"Failed to add survey '{survey_name}' (region: {region_name}), see log for database error")

        self.survey_ref[cache_key] = survey_id
        return survey_id

    def region(self, region_name):
        """Get or create region"""
        try:
            region_id = self.mpDB.select("region", columns="id", row_cond=f'name={sql_text(region_name)}')[0][0]
        except IndexError:
            region_id = self.mpDB.add_region(str(region_name), None)
            if region_id is None:
                raise RuntimeError(f"Failed to add region '{region_name}', see log for database error")
        return region_id

    def station(self, exemplar, survey_id):
        """Get or create station"""
        station_name = exemplar.get(self.selected_columns["station"])
        station_name = self._convert_to_str(station_name)
        # check reference dictionary first, station names are only unique within a survey
        station_key = (station_name, survey_id)
        if station_key in self.station_ref:
            return self.station_ref[station_key]
        try:
            row_cond = f'name={sql_text(station_name)} AND survey_id={int(survey_id)}'
            station_id = self.mpDB.select("station", columns="id", row_cond=row_cond)[0][0]
        except IndexError:
            lat = exemplar.get(self.selected_columns["lat"])
            lat = self._convert_to_float(lat)
            long = exemplar.get(self.selected_columns["long"])
            long = self._convert_to_float(long)
            station_id = self.mpDB.add_station(str(station_name), lat, long, survey_id)
            if station_id is None:
                raise RuntimeError(f"Failed to add station '{station_name}' (survey_id: {survey_id}), see log for database error")
        self.station_ref[station_key] = station_id
        return station_id

    # OPTIONAL -----------------------------------------------------------------
    def camera(self, exemplar, station_id):
        """Get or create camera"""
        camera_id = None
        # a blank cell reads as NaN, convert before checking for a camera
        camera_name = self._convert_to_str(exemplar.get(self.selected_columns["camera"]))
        if camera_name is not None:
            # check reference dictionary first, camera names are only unique within a station
            camera_key = (camera_name, station_id)
            if camera_key in self.camera_ref:
                return self.camera_ref[camera_key]
            try:
                row_cond = f"name={sql_text(camera_name)} AND station_id={int(station_id)}"
                camera_id = self.mpDB.select("camera", columns="id", row_cond=row_cond)[0][0]
            except IndexError:
                camera_id = self.mpDB.add_camera(str(camera_name), station_id)
                if camera_id is None:
                    raise RuntimeError(f"Failed to add camera '{camera_name}' (station_id: {station_id}), see log for database error")
            self.camera_ref[camera_key] = camera_id
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
                individual_id = self.mpDB.select("individual", columns="id", row_cond=f'name={sql_text(individual_name)}')[0][0]
            except IndexError:
                sex = None
                #TODO: limit sex to valid values
                if self.selected_columns["sex"] != "None":
                    sex = self._roi_value(roi, self.selected_columns["sex"])
                    sex = self._convert_sex(sex)
                individual_id = self.mpDB.add_individual(individual_name, sex)
            self.individual_ref[individual_name] = individual_id
        return individual_id

    def _convert_sex(self, listed_sex):
        """Convert sex to standard format, handling None and NaN"""
        if not pd.isna(listed_sex):
            sex = str(listed_sex).strip()
            if sex.lower() in ["male", "m"]:
                return "Male"
            elif sex.lower() in ["female", "f"]:
                return "Female"
            else:
                return None
        return None

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
            # no quote escaping here, sql_text and query parameters do that
            return str(value).strip()
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
    import_failed = pyqtSignal(str)  # Signal to report a fatal import error

    # How many files to process between progress signal emissions.
    PROGRESS_BATCH_SIZE = 10
    # Seconds between commits. Each commit waits for the disk (~15 ms), so committing with
    # every progress update cost more than adding the rows; a short interval keeps the write
    # lock from being held long. An interrupted import is resumed by importing again.
    COMMIT_INTERVAL = 1.0

    def __init__(self, parent, active_survey, data, station_level, camera_level):
        super().__init__()
        self.mpDB = parent.mpDB
        self.active_survey = active_survey
        self.data = data
        self.station_level = station_level
        self.camera_level = camera_level
        self.default_station = None
        self.thumbnail_dir = parent.cfg.THUMBNAIL_DIR
        self.station_ref = {}  # dictionary to store (station name, survey id) to id mapping
        self.camera_ref = {}  # dictionary to store (camera name, station id) to id mapping
        # get timezone for timestamp parsing

    def run(self):
        file_counter = 0  # progressbar counter
        emitted_counter = 0  # last value emitted, to batch signal emission
        last_commit = time.monotonic()
        thumbnails = ThumbnailQueue(self.mpDB)

        try:
            # get base directory for the files being imported
            base_dir = self._get_base_dir(self.data['filepath'].tolist())
            try:
                base_dir_id = self.mpDB.select("uploads", columns="id", row_cond=f'base_dir={sql_text(base_dir)}')[0][0]
            except IndexError:
                base_dir_id = self.mpDB.add_upload(base_dir)

            for _, file in self.data.iterrows():
                if self.isInterruptionRequested():
                    break

                file_counter += 1

                filepath = file['filepath']
                # check to see if file exists
                if not Path(filepath).exists():
                    logger.warning(f"File {filepath} does not exist")
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
                else:
                    # create default station if no station level and use for all media
                    station_id = self._default_station(survey_id)
                # add camera if camera level provided (also under the default station), else None
                camera_id = self.camera(filepath, station_id) if self.camera_level > 0 else None

                # insert into table, force type
                media_id = self.mpDB.add_media(base_dir_id,
                                               relative_path,
                                               hash,
                                               ext,
                                               str(timestamp),
                                               int(station_id),
                                               camera_id=int(camera_id) if camera_id is not None else None,
                                               sequence_id=None,
                                               external_id=None,
                                               comment=None,
                                               commit=False)
                if media_id == "duplicate_path":
                    logger.warning(f"A different file is already in the project at {filepath}, skipping import...")
                # save thumbnail, unless the file was already imported or failed to add
                elif media_id not in ("duplicate_hash", None):
                    thumbnails.add("media", media_id, save_media_thumbnail, self.thumbnail_dir, filepath, ext)

                # bank progress updates in batches, commit on an interval
                if file_counter - emitted_counter >= self.PROGRESS_BATCH_SIZE:
                    self.progress_update.emit(file_counter)
                    emitted_counter = file_counter
                if time.monotonic() - last_commit >= self.COMMIT_INTERVAL:
                    self.mpDB.db.commit()
                    last_commit = time.monotonic()

            thumbnails.finish()
            self.mpDB.db.commit()  # commit anything remaining

        except Exception as error:
            # an unhandled exception in a QThread aborts the whole app, report it instead
            self.mpDB.db.rollback()
            logger.exception("Import failed")
            self.import_failed.emit(str(error))
            return
        finally:
            thumbnails.close()

        # make sure the progress bar reaches its true final value
        if emitted_counter != file_counter:
            self.progress_update.emit(file_counter)

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

    def _default_station(self, survey_id):
        """Get or create the default station, for media without a station level"""
        if not self.default_station:
            self.default_station = self.mpDB.add_station("Default Station", None, None, int(survey_id))
        return self.default_station

    def station(self, filepath, survey_id):
        """Get or create station"""
        parts = Path(filepath).parts
        # levels are picked from one file, a shallower file has no folder at that level
        if self.station_level >= len(parts) - 1:
            logger.warning(f"File {filepath} has no station folder, using the default station")
            return self._default_station(survey_id)
        station_name = parts[self.station_level]
        station_name = str(station_name)
        # check reference dictionary first, station names are only unique within a survey
        station_key = (station_name, survey_id)
        if station_key in self.station_ref:
            return self.station_ref[station_key]
        try:
            row_cond = f'name={sql_text(station_name)} AND survey_id={int(survey_id)}'
            station_id = self.mpDB.select("station", columns="id", row_cond=row_cond)[0][0]
        except IndexError:
            station_id = self.mpDB.add_station(station_name, None, None, survey_id)
        self.station_ref[station_key] = station_id
        return station_id

    def camera(self, filepath, station_id):
        parts = Path(filepath).parts
        # levels are picked from one file, a shallower file has no folder at that level
        if self.camera_level >= len(parts) - 1:
            logger.warning(f"File {filepath} has no camera folder, adding it without a camera")
            return None
        camera_name = parts[self.camera_level]
        camera_name = str(camera_name)
        # check reference dictionary first, camera names are only unique within a station
        camera_key = (camera_name, station_id)
        if camera_key in self.camera_ref:
            return self.camera_ref[camera_key]
        try:
            row_cond = f"name={sql_text(camera_name)} AND station_id={int(station_id)}"
            camera_id = self.mpDB.select("camera", columns="id", row_cond=row_cond)[0][0]
        except IndexError:
            camera_id = self.mpDB.add_camera(camera_name, station_id)
        self.camera_ref[camera_key] = camera_id
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
