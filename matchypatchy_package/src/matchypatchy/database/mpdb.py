'''
Class Definition for MatchyPatchyDB
'''
import datetime
from typing import Optional
import sqlite3
import chromadb
import threading
from pathlib import Path
from random import randrange
import numpy as np
import pandas as pd

from matchypatchy.database.setup import setup_database, setup_chromadb
from matchypatchy.config import asset_path
from matchypatchy.database.location import TZ_CONVERT_DICT
from matchypatchy import __version__

class MatchyPatchyDB():
    def __init__(self, DB_PATH, logger):
        self.filepath = Path(DB_PATH) / 'matchypatchy.db'
        self.chroma_filepath = Path(DB_PATH) / 'emb.db'
        self.logger = logger
        self.local = threading.local()  # Thread-local storage
        
        # load existing databases if they exist
        if self.filepath.is_file() and self.chroma_filepath.is_dir():
            # initialize
            self.chroma = chromadb.PersistentClient(str(self.chroma_filepath))
            self.collection = self.chroma.get_collection(name="embedding_collection")
            # check key
            self.key = self.validate()

        # initialize new databases
        else:
            self.key = '{:05}'.format(randrange(1, 10 ** 5))
            self._setup_new_databases()

    def _setup_new_databases(self):
        """Helper to set up new databases (uses thread-local db via property)"""
        self.db  # Trigger property initialization
        setup_database(self.key, self.filepath, self.db)
        self.chroma = setup_chromadb(self.key, self.chroma_filepath)
        self.collection = self.chroma.get_collection(name="embedding_collection")
        # add default region and survey
        timezone = str(datetime.datetime.now().astimezone().tzname())
        timezone = TZ_CONVERT_DICT.get(timezone, timezone)
        id = self.add_region("Default Region", timezone)
        self.add_survey("Default Survey", id, None, None)

    @property
    def db(self):
        """Get or create a connection for the current thread"""
        if not hasattr(self.local, 'db') or self.local.db is None:
            self.local.db = sqlite3.connect(self.filepath)
            self.local.db.execute("PRAGMA foreign_keys = ON")
        return self.local.db
    
    def close(self):
        """Close the thread-local connection"""
        if hasattr(self.local, 'db') and self.local.db:
            self.local.db.close()
            self.local.db = None

    def update_paths(self, DB_PATH):
        """Update database paths, create new database if not found"""
        filepath = Path(DB_PATH) / 'matchypatchy.db'
        chroma_filepath = Path(DB_PATH) / 'emb.db'
        if filepath.is_file() and chroma_filepath.is_dir():
            valid = self.validate()
            if valid:
                self.key = valid
                self.filepath = filepath
                self.chroma_filepath = chroma_filepath
                self.db = sqlite3.connect(self.filepath)
                self.db.execute("PRAGMA foreign_keys = ON")
                self.chroma = chromadb.PersistentClient(str(self.chroma_filepath))
                return True
            else:
                return False
        else:
            # create new databases
            self.filepath = filepath
            self.chroma_filepath = chroma_filepath
            self.key = '{:05}'.format(randrange(1, 10 ** 5))
            self.db = setup_database(self.key, self.filepath)
            self.chroma = setup_chromadb(self.key, self.chroma_filepath)
            return True

    def retrieve_key(self):
        """Retrieve key from both databases to confirm match"""
        cursor = self.db.cursor()
        cursor.execute("SELECT mp_version, key FROM metadata WHERE id=1;")
        db_build_version, mpkey = cursor.fetchone()

        collection = self.chroma.get_collection(name="embedding_collection")
        chroma_key = collection.metadata['key']

        return db_build_version, mpkey, chroma_key

    def info(self):
        """Get current counts of media and roi in database"""
        cursor = self.db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        self.logger.info(tables)
        cursor.execute("SELECT COUNT(id) FROM media")
        media = cursor.fetchone()[0]
        print(f"Media: {media}")
        self.logger.info(f"Media: {media}")
        cursor.execute("SELECT COUNT(id) FROM roi;")
        roi = cursor.fetchone()[0]
        print(f"ROI: {roi}")
        self.logger.info(f"ROI: {roi}")

    def validate(self):
        """Confirm that the database schema matches expected schema"""
        cursor = self.db.cursor()
        cursor.execute("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table', 'index', 'view', 'trigger')")
        schema = cursor.fetchall()

        # compare schema to expected schema
        s = ""
        for name, obj_type, sql in schema:
            s = s + (f"{obj_type.upper()}: {name}\n{sql}\n")

        schema_path = asset_path('schema.txt')
        with open(schema_path, 'r') as file:
            content = file.read()
        match_schema = (content==s)

        # Check that the database build version and key match
        db_build_version, mpkey, chromakey = self.retrieve_key()

        if match_schema:
            # confirm databases match
            if mpkey == chromakey:
                return mpkey
            else:
                self.logger.error("Key mismatch for Image DB and Emb DB.")
                return False
        else:
            if db_build_version != __version__:
                self.logger.error(f"""Schema of selected DB invalid. Database was built with MatchyPatchy version 
                                  {db_build_version} does not match current version {__version__}.""")
            else:
                self.logger.error("Schema of selected DB invalid. Database content does not match expected schema.")
            print(s)
            return False

    def _command(self, command, quiet=True):
        """
        Execute a specific sql query to fetch data
        Meant for one-time use
        """
        try:
            if not quiet:
                print(command)
            cursor = self.db.cursor()
            cursor.execute(command)
            self.logger.info(f"Executed command: {command}")
            rows = cursor.fetchall()
            self.db.commit()
            return rows
        except sqlite3.OperationalError as error:
            if not quiet:
                print(f"Operational error executing command: {error}")  
            self.logger.error(f"Operational error executing command: {error}")
            return None
        except sqlite3.Error as error:
            if not quiet:
                print(f"Failed to execute command: {error}")
            self.logger.error("Failed to execute command.", error)
            return None

    # INSERT -------------------------------------------------------------------
    def add_survey(self, name: str, region_id: int, year_start: int, year_end: int):
        """
        Add a survey with
            - name (str) Not Null
            - region_id (int)
            - year_start (int)
            - year_end (int)
        """
        try:
            cursor = self.db.cursor()
            command = """INSERT INTO survey
                        (name, region_id, year_start, year_end)
                        VALUES (?, ?, ?, ?);"""
            data_tuple = (name, region_id, year_start, year_end)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            self.db.commit()
            self.logger.info(f"Added survey: {name} with region_id: {region_id}, year_start: {year_start}, year_end: {year_end}")
            return id
        except sqlite3.Error as error:
            self.logger.error(f"Failed to add survey: {error}")
            return None

    def add_region(self, name: str, timezone: str):
        """
        Add a region with
            - name (str) Not Null
            - timezone (str) Optional
        """
        if timezone is None:
            timezone = str(datetime.datetime.now().astimezone().tzname())
            timezone = TZ_CONVERT_DICT.get(timezone, timezone)
        try:
            cursor = self.db.cursor()
            command = """INSERT INTO region (name, timezone) VALUES (?, ?);"""
            data_tuple = (name, timezone)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            self.db.commit()
            self.logger.info(f"Added region: {name} with timezone: {timezone}")
            return id
        except sqlite3.Error as error:
            self.logger.error(f"Failed to add region: {error}")
            return None

    def add_station(self, name: str, lat: float, long: float, survey_id: int):
        """
        Add a station with
            - name (str) NOT NULL
            - lat (float): latitude
            - long (float): longitude
            - survey_id (int) NOT NULL
        """
        try:
            cursor = self.db.cursor()
            command = """INSERT INTO station
                        (name, lat, long, survey_id)
                        VALUES (?, ?, ?, ?);"""
            data_tuple = (name, lat, long, survey_id)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            self.db.commit()
            self.logger.info(f"Added station: {name} with lat: {lat}, long: {long}, survey_id: {survey_id}")
            return id
        except sqlite3.Error as error:
            self.logger.error(f"Failed to add station: {error}")
            return None

    def add_individual(self, name: str, sex: Optional[str] = None, age: Optional[str] = None):
        """
        Add an individual with
            - name (str)
            - sex (str)
            - age (str)
        """
        try:
            cursor = self.db.cursor()
            command = """INSERT INTO individual
                        (name, sex, age)
                        VALUES (?, ?, ?);"""
            data_tuple = (name, sex, age)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            self.db.commit()
            return id
        except sqlite3.Error as error:
            self.logger.error(f"Failed to add individual: {error}")
            return None

    def add_media(self,
                  filepath: str,
                  sha256: str,
                  ext: str,
                  timestamp: str,
                  station_id: int,
                  camera_id: Optional[int] = None,
                  sequence_id: Optional[int] = None,
                  external_id: Optional[int] = None,
                  comment: Optional[str] = None):
        """
        Media has 10 attributes not including id:
            id INTEGER PRIMARY KEY,
            filepath TEXT UNIQUE NOT NULL,
            sha256 TEXT UNIQUE NOT NULL,
            ext TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            station_id INTEGER NOT NULL,
            camera_id INTEGER,
            sequence_id INTEGER,
            external_id INTEGER,
            comment TEXT,
        """
        try:
            cursor = self.db.cursor()
            command = """INSERT INTO media
                        (filepath, sha256, ext, timestamp, station_id,
                        camera_id, sequence_id, external_id, comment)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"""
            data_tuple = (str(filepath),
                          str(sha256),
                          str(ext),
                          str(timestamp),
                          int(station_id),
                          camera_id, 
                          sequence_id,
                          external_id,
                          comment)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            self.db.commit()
            return id

        # filepath already exists
        except sqlite3.IntegrityError as error:
            if 'UNIQUE constraint failed: media.filepath' in error.args[0]:
                self.logger.error(f"Failed to add {filepath}, already exists in database.")
                return "duplicate_error"
            
            if 'UNIQUE constraint failed: media.sha256' in error.args[0]:
                self.logger.error(f"Failed to add {filepath}, file is a duplicate.")
                return "duplicate_error"

        except sqlite3.Error as error:
            self.logger.error(f"Failed to add media: {error}")
            return None

    def add_roi(self,
                media_id: int,
                frame: int,
                bbox_x: float, bbox_y: float, bbox_w: float, bbox_h: float,
                viewpoint: Optional[str] = None,
                reviewed: int = 0,
                favorite: int = 0,
                individual_id: Optional[int] = None, 
                emb: int = 0):
        """
        Add a roi with:
            - media_id (int) NOT NULL
            - frame (int) NOT NULL
            - bbox_x (float) NOT NULL
            - bbox_y (float) NOT NULL
            - bbox_w (float) NOT NULL
            - bbox_h (float) NOT NULL
            - viewpoint (int)
            - reviewed (int) NOT NULL
            - favorite (int) NOT NULL
            - individual_id (int) references individual(id)
            - emb (int) references chroma embedding id
        """
        try:
            cursor = self.db.cursor()
            command = """INSERT INTO roi
                        (media_id, frame, bbox_x, bbox_y, bbox_w, bbox_h,
                         viewpoint, reviewed, favorite, individual_id, emb)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
            data_tuple = (int(media_id), 
                          int(frame), 
                          float(round(bbox_x, 4)), 
                          float(round(bbox_y, 4)),
                          float(round(bbox_w, 4)),
                          float(round(bbox_h, 4)),
                          viewpoint, 
                          int(reviewed), 
                          int(favorite), 
                          individual_id, 
                          emb)
            
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            self.db.commit()
            return id
        except sqlite3.Error as error:
            self.logger.error(f"Failed to add roi for media: {media_id}. {error}")
            return None

    def add_sequence(self):
        """Increase sequence counter table, return value"""
        try:
            cursor = self.db.cursor()
            command = """INSERT INTO sequence DEFAULT VALUES;"""
            cursor.execute(command)
            id = cursor.lastrowid
            self.db.commit()
            return id
        except sqlite3.Error as error:
            self.logger.error(f"Failed to add sequence: {error}")
            return None

    def add_camera(self, name: str, station_id: int):
        """
        Add a camera with:
            - name (str) NOT NULL
            - station_id (int) NOT NULL
        """
        try:
            cursor = self.db.cursor()
            command = """INSERT INTO camera (name, station_id) VALUES (?, ?);"""
            data_tuple = (name, station_id)
            cursor.execute(command, data_tuple)
            camera_id = cursor.lastrowid
            self.db.commit()
            return camera_id
        except sqlite3.Error as error:
            self.logger.error(f"Failed to add camera: {error}")
            return None

    def add_thumbnail(self, table, fid, filepath):
        """Add a thumbnail entry to media_thumbnails or roi_thumbnails table

        Args:
            - table (str): "media" or "roi"
            - fid (int): id of media or roi
            - filepath (str): path to thumbnail image
        """
        try:
            cursor = self.db.cursor()
            command = f"""INSERT INTO {table}_thumbnails (fid, filepath) VALUES (?, ?);"""
            data_tuple = (fid, filepath)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            self.db.commit()
            return id
        
        # filepath already exists
        except sqlite3.IntegrityError as error:
            if 'UNIQUE constraint failed: media_thumbnails.fid' in error.args[0]:
                self.logger.error("Failed to add thumbnail, already exists in database.")
                return "duplicate_error"
            if 'UNIQUE constraint failed: roi_thumbnails.fid' in error.args[0]:
                self.logger.error("Failed to add thumbnail, already exists in database.")
                return "duplicate_error"
        except sqlite3.Error as error:
            self.logger.error(f"Failed to add thumbnail: {error}")
            return None

    def copy(self, table, id):
        """Copy a row from a table by id"""
        try:
            cursor = self.db.cursor()
            command = f"""INSERT INTO {table} SELECT * FROM table WHERE id={id};"""
            cursor.execute(command)
            id = cursor.lastrowid
            self.db.commit()
            return id
        except sqlite3.Error as error:
            self.logger.error(f"Failed to copy row: {error}")
            return None

    # EDIT ---------------------------------------------------------------------
    def edit_row(self, table: str, id: int, replace: dict, allow_none=False, quiet=True):
        """
        Edit a row in place

        Args
            - table (str):
            - id (int):
            - replace (dict): column:value captures to update
            - allow_none (bool): if True, allows replacing with None
            - quiet (bool): if False, prints the executed command
        """
        try:
            cursor = self.db.cursor()
            # convert empty values to SQL NULL
            for key, value in replace.items():
                if value in (None, ''):
                    replace[key] = 'NULL'
                if isinstance(value, str):
                    replace[key] = f"'{value}'"

            replace_values = ",".join(f"{k}={v}" for k, v in replace.items())

            command = f"UPDATE {table} SET {replace_values} WHERE id={id}"
            if not quiet:
                print(command)
            cursor.execute(command)
            self.db.commit()
            return True
        except sqlite3.Error as error:
            self.logger.error(f"Failed to update table: {error}")
            return False

    def select(self, table: str, columns: str = "*", row_cond: Optional[str] = None, quiet=True):
        """
        Select columns based on optional row_cond
        Returns each row as a tuple
        
        Args
            - table (str): table name
            - columns (str): columns to select, default "*"
            - row_cond (str): optional condition for WHERE clause
            - quiet (bool): if False, prints the executed command
        """
        try:
            cursor = self.db.cursor()
            if row_cond is not None:
                command = f'SELECT {columns} FROM {table} WHERE {row_cond};'
            else:
                command = f'SELECT {columns} FROM {table};'
            if not quiet:
                print(command)
            cursor.execute(command)
            rows = cursor.fetchall()
            return rows
        except sqlite3.Error as error:
            self.logger.error("Failed fetch: ", error)
            return None

    def select_join(self, table, join_table, join_cond, columns="*", row_cond: Optional[str] = None, quiet=True):
        """
        Select columns based on optional row_cond with inner join of join_table
        Returns each row as a tuple

        Args
            - table (str): main table name
            - join_table (str): table to join
            - join_cond (str): condition for JOIN clause
            - columns (str): columns to select, default "*"
            - row_cond (str): optional condition for WHERE clause
            - quiet (bool): if False, prints the executed command
        """
        try:
            cursor = self.db.cursor()
            if row_cond is not None:
                command = f'SELECT {columns} FROM {table} INNER JOIN {join_table} ON {join_cond} WHERE {row_cond};'
            else:
                command = f'SELECT {columns} FROM {table} INNER JOIN {join_table} ON {join_cond};'
            if not quiet:
                print(command)
            cursor.execute(command)
            column_names = [description[0] for description in cursor.description]
            rows = cursor.fetchall()  # returns in tuple
            return rows, column_names
        except sqlite3.Error as error:
            self.logger.error(f"Failed fetch: {error}")
            return None, None

    def stations(self, row_cond=None):
        """Return joined station, survey, region info"""
        try:
            cursor = self.db.cursor()
            columns = """station.id, station.name, lat, long, station.survey_id, survey.name, region.name"""
            if row_cond is not None:
                command = f"""SELECT {columns} FROM station LEFT JOIN survey ON station.survey_id = survey.id
                                                LEFT JOIN region ON survey.region_id = region.id
                                                WHERE {row_cond};"""
            else:
                command = f"""SELECT {columns} FROM station LEFT JOIN survey ON station.survey_id = survey.id
                                                LEFT JOIN region ON survey.region_id = region.id;"""
            cursor.execute(command)
            column_names = columns.split(", ")
            rows = cursor.fetchall()  # returns in tuple
            return rows, column_names
        except sqlite3.Error as error:
            self.logger.error(f"Failed all_media fetch: {error}")
            return None, None

    def count(self, table):
        """Return the number of entries in a given table"""
        try:
            cursor = self.db.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]
            return row_count
        except sqlite3.Error as error:
            self.logger.error(f"Failed to count for {table}: {error}")
            return None

    # EXPORT -------------------------------------------------------------------
    def all_media(self, row_cond: Optional[str] = None):
        """Return joined roi and media info for Media Table"""
        try:
            cursor = self.db.cursor()
            columns = """roi.id, frame, bbox_x ,bbox_y, bbox_w, bbox_h, viewpoint, reviewed,
                         roi.media_id, roi.individual_id, emb, filepath, ext, timestamp,
                         station_id, sequence_id, camera_id, external_id, comment, favorite, name, sex, age"""
            if row_cond is not None:
                command = f"""SELECT {columns} FROM roi INNER JOIN media ON roi.media_id = media.id
                                            LEFT JOIN individual ON roi.individual_id = individual.id
                                            WHERE {row_cond};"""
            else:
                command = f"""SELECT {columns} FROM roi INNER JOIN media ON roi.media_id = media.id
                                            LEFT JOIN individual ON roi.individual_id = individual.id;"""
            cursor.execute(command)
            column_names = [description[0] for description in cursor.description]
            rows = cursor.fetchall()  # returns in tuple
            return rows, column_names
        except sqlite3.Error as error:
            self.logger.error("Failed all_media fetch:", error)
            return None, None

    def export_data(self):
        """
        Fetch Info for Media Table
        columns = ['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
                   'reviewed', 'favorite', 'media_id', 'individual_id', 'emb',
                   'filepath', 'ext', 'timestamp', 'sequence_id', 'external_id', 'comment', 
                   'name', 'sex', 'age',
                   'station_id', 'station_name', 'lat', 'long', 
                   'station_survey_id', 'survey_name', 'region_name', 
                   'camera_id', 'camera_name']
        """
        media, column_names = self.all_media()
        rois = pd.DataFrame(media, columns=column_names)
        rois['viewpoint'] = pd.to_numeric(rois['viewpoint'], errors='coerce').astype('Int64')
        # merge with stations
        stations, column_names = self.stations()
        stations = pd.DataFrame(stations, columns=column_names)
        stations.columns = stations.columns.str.replace('.', '_')
        # get camera names
        cameras = self.select("camera")
        if not rois.empty:
            export_data = pd.merge(rois, stations, on="station_id")
            # add camera name
            if cameras:
                cameras = pd.DataFrame(cameras, columns=["id", "camera_name", "station_id"])
                export_data = pd.merge(export_data, cameras[["id", "camera_name"]], left_on="camera_id", right_on="id")
            else:
                # no camera, set column to blank
                export_data['camera_name'] = None
            export_data = export_data.replace({float('nan'): None})
            # rename columns to avoid issues with '.' in column names when importing
            export_data.columns = export_data.columns.str.replace('.', '_')
            return export_data
        else:
            return None

    # DELETE -------------------------------------------------------------------
    def delete(self, table, cond):
        """Delete Entries From table Given condition"""
        try:
            cursor = self.db.cursor()
            command = f'DELETE FROM {table} WHERE {cond};'
            print(command)
            cursor.execute(command)
            self.db.commit()
            self.logger.info(f"Deleted from {table} where {cond}")
            return True
        except sqlite3.Error as error:
            self.logger.error(f"Failed delete: {error}")
            return False

    def clear(self, table):
        """Clear a table without dropping it"""
        try:
            cursor = self.db.cursor()
            command = f'DELETE FROM {table};'
            cursor.execute(command)
            self.db.commit()
            self.logger.info(f"Cleared table {table}")
            return True
        except sqlite3.Error as error:
            self.logger.error(f"Failed to clear {table}: {error}")
            return False

    # EMBEDDINGS ===============================================================
    def add_emb(self, id, embedding):
        """Add embedding to chroma vector database"""
        self.collection.add(embeddings=[embedding], ids=[str(id)])

    def delete_emb(self, id):
        """Delete embedding from chroma vector database"""
        self.collection.delete(ids=[str(id)])

    def knn(self, query_id, k=3):
        """Get k nearest neighbors of a query ROI from chroma vector database"""
        query = self.collection.get(ids=[str(query_id)], include=['embeddings'])['embeddings']
        # Check if query is empty, ie false positives
        if len(query) == 0:
            return {'ids': [[]], 'distances': [[]]}
        knn = self.collection.query(query_embeddings=query, n_results=k + 1)
        return knn

    def calculate_similarity(self, query_id, match_id):
        results1 = self.collection.get(ids=[str(query_id)], include=["embeddings"])
        results2 = self.collection.get(ids=[str(match_id)], include=["embeddings"])

        emb1 = results1['embeddings'][0]
        emb2 = results2['embeddings'][0]

        if emb1 is None or emb2 is None:
            return None

        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        similarity = dot_product / (norm1 * norm2) if norm1 != 0 and norm2 != 0 else 0
        return float(similarity)

    def clear_emb(self):
        """Clear vector database and rebuild (no way to delete)"""
        self.chroma.delete_collection(name="embedding_collection")
        self.chroma = setup_chromadb(self.key, self.chroma_filepath)
        self.collection = self.chroma.get_collection(name="embedding_collection")
        self.logger.info("Chroma vector database cleared and rebuilt.")
