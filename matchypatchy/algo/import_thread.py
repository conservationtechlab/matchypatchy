"""
QThreads for Importing Data

"""
from pathlib import Path
import logging

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.config import load_cfg
from matchypatchy.database.thumbnails import save_media_thumbnail, save_roi_thumbnail


class CSVImportThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar

    def __init__(self, mpDB, unique_images, selected_columns):
        super().__init__()
        self.mpDB = mpDB
        self.unique_images = unique_images
        self.selected_columns = selected_columns
        self.thumbnail_dir = load_cfg('THUMBNAIL_DIR')

    def run(self):
        roi_counter = 0  # progressbar counter
        for filepath, group in self.unique_images:

            if not self.isInterruptionRequested():
                # check to see if file exists
                if not Path(filepath).exists():
                    print(f"File {filepath} does not exist")
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

                # insert into table
                media_id = self.mpDB.add_media(filepath,
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

    def __init__(self, mpDB, active_survey, data, station_level):
        super().__init__()
        self.mpDB = mpDB
        self.active_survey = active_survey
        self.data = data
        self.station_level = station_level
        self.default_station = None
        self.thumbnail_dir = load_cfg('THUMBNAIL_DIR')

    def run(self):
        for i, file in self.data.iterrows():
            if not self.isInterruptionRequested():
                filepath = file['filepath']
                timestamp = file['datetime']

                # check to see if file exists
                if not Path(filepath).exists():
                    logging.warning(f"File {filepath} does not exist")
                    continue

                # get file extension
                ext = Path(filepath).suffix.lower()

                # get remaining information
                if self.station_level > 0:
                    station_name = Path(filepath).parts[self.station_level]
                    try:
                        station_id = self.mpDB.select("station", columns='id', row_cond=f'name="{station_name}"')[0][0]
                    except IndexError:
                        station_id = self.mpDB.add_station(str(station_name), None, None, int(self.active_survey[0]))
                else:
                    if not self.default_station:
                        self.default_station = self.mpDB.add_station("None", None, None, int(self.active_survey[0]))
                    station_id = self.default_station

                # insert into table, force type
                media_id = self.mpDB.add_media(filepath,
                                               ext,
                                               str(timestamp),
                                               int(station_id),
                                               camera_id=None,
                                               sequence_id=None,
                                               external_id=None,
                                               comment=None)
                # save thumbnail
                thumbnail_path = save_media_thumbnail(self.thumbnail_dir, filepath, ext)
                self.mpDB.add_thumbnail("media", media_id, thumbnail_path)

                self.progress_update.emit(i)

        # finished adding media
        self.finished.emit()
