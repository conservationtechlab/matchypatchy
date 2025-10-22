"""
QThreads for Importing Data

"""
from pathlib import Path
import logging
from PyQt6.QtCore import QThread, pyqtSignal
from matchypatchy.database.media import VIDEO_EXT


class CSVImportThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar

    def __init__(self, mpDB, unique_images, selected_columns):
        super().__init__()
        self.mpDB = mpDB
        self.unique_images = unique_images
        self.selected_columns = selected_columns
        print(selected_columns)

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

                media_id = self.mpDB.add_media(filepath,
                                               ext, 
                                               timestamp, 
                                               station_id,
                                               camera_id=camera_id,
                                               sequence_id=sequence_id,
                                               external_id=external_id,
                                               comment=comment)
                # image already added
                if media_id == "duplicate_error":
                    media_id = self.mpDB.select("media", columns="id", row_cond=f'filepath="{filepath}"')[0][0]

                if ext in VIDEO_EXT:
                    continue  # skip adding rois for videos

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

                    # species and individual
                    species_id = self.species(roi)
                    individual_id = self.individual(roi, species_id)

                    # viewpoint
                    viewpoint = int(roi[self.selected_columns["viewpoint"]]) if self.selected_columns["viewpoint"] != "None" else None

                    # set reviewed to 1 for named images
                    reviewed = 1 if individual_id is not None else 0

                    # do not add emb_id, to be determined later
                    roi_id = self.mpDB.add_roi(media_id,
                                               frame,
                                               bbox_x, bbox_y, bbox_w, bbox_h,
                                               species_id,
                                               viewpoint=viewpoint,
                                               reviewed=reviewed,
                                               individual_id=individual_id,
                                               emb=0)
                    roi_counter += 1
                    self.progress_update.emit(roi_counter)
    
        if not self.isInterruptionRequested():
            # finished adding media
            self.finished.emit()

    def survey(self, exemplar):
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
        # get or create station
        station_name = exemplar[self.selected_columns["station"]].item()
        try:
            station_id = self.mpDB.select("station", columns="id", row_cond=f'name="{station_name}"')[0][0]
        except IndexError:
            station_id = self.mpDB.add_station(str(station_name), None, None, survey_id)
        return station_id

    def camera(self, exemplar, station_id):
        # get or create station
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

    def species(self, roi):
        if self.selected_columns["species"] != "None":
            species_name = roi[self.selected_columns["species"]]
            try:
                species_id = self.mpDB.select("species", columns="id", row_cond=f'common="{species_name}"')[0][0]
            except IndexError:
                species_id = self.mpDB.add_species("Taxon not specified", str(species_name))
        else:  # no species
            species_id = None
        return species_id

    def individual(self, roi, species_id):
        # individual
        if self.selected_columns["individual"] != "None":
            individual = roi[self.selected_columns["individual"]]
            try:
                individual_id = self.mpDB.select("individual", columns="id", row_cond=f'name="{individual}"')[0][0]
            except IndexError:
                individual_id = self.mpDB.add_individual(species_id, str(individual))
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
                if media_id == "duplicate_error":
                    print(f"File {filepath} already in database, skipping")
                    logging.info(f"File {filepath} already in database, skipping")

                self.progress_update.emit(i)

        # finished adding media
        self.finished.emit()
