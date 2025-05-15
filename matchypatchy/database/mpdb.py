'''
Class Definition for MatchyPatchyDB
'''
import logging
from typing import Optional
import sqlite3
import chromadb
from pathlib import Path
from random import randrange

from matchypatchy.database.setup import setup_database, setup_chromadb
from matchypatchy import sqlite_vec


class MatchyPatchyDB():
    def __init__(self, DB_PATH):
        self.filepath = Path(DB_PATH) / 'matchypatchy.db'
        self.chroma_filepath = Path(DB_PATH) / 'emb.db'
        if self.filepath.is_file() and self.chroma_filepath.is_dir():
            self.key = self.validate()
        else:
            self.key = '{:05}'.format(randrange(1, 10 ** 5))
            setup_database(self.key, self.filepath)
            setup_chromadb(self.key, self.chroma_filepath)

    def update_paths(self, DB_PATH):
        filepath = Path(DB_PATH) / 'matchypatchy.db'
        chroma_filepath = Path(DB_PATH) / 'emb.db'
        if filepath.is_file() and chroma_filepath.is_dir():
            valid = self.validate()
            if valid:
                self.key = valid
                self.filepath = filepath
                self.chroma_filepath = chroma_filepath
                return True
            else:
                return False
        else:
            self.filepath = filepath
            self.chroma_filepath = chroma_filepath
            self.key = '{:05}'.format(randrange(1, 10 ** 5))
            setup_database(self.key, self.filepath)
            setup_chromadb(self.key, self.chroma_filepath)
            return True

    def retrieve_key(self):
        db = sqlite3.connect(self.filepath)
        cursor = db.cursor()
        cursor.execute("SELECT key FROM metadata WHERE id=1;")
        mpdb_key = cursor.fetchone()[0]
        db.close()

        client = chromadb.PersistentClient(str(self.chroma_filepath))
        collection = client.get_collection(name="embedding_collection")
        chroma_key = collection.metadata['key']
        
        return mpdb_key, chroma_key

    def info(self):
        """
        Validate All Tables Are Present
        """
        db = sqlite3.connect(self.filepath)
        cursor = db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        logging.info(tables)
        cursor.execute("SELECT COUNT(id) FROM media")
        media = cursor.fetchone()[0]
        print(f"Media: {media}")
        logging.info(f"Media: {media}")
        cursor.execute("SELECT COUNT(id) FROM roi;")
        roi = cursor.fetchone()[0]
        print(f"ROI: {roi}")
        logging.info(f"ROI: {roi}")
        db.close()

    def validate(self):
        db = sqlite3.connect(self.filepath)
        cursor = db.cursor()
        cursor.execute("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table', 'index', 'view', 'trigger')")
        schema = cursor.fetchall()
        db.close()

        s = ""
        for name, obj_type, sql in schema:
            s = s + (f"{obj_type.upper()}: {name}\n{sql}\n")

        with open('schema', 'r') as file:
            content = file.read()
    
        match_schema = (content==s)
        mpkey, chromakey = self.retrieve_key()
        if match_schema and mpkey == chromakey:
            return mpkey
        else:
            return False

    def _command(self, command):
        """
        Execute a specific sql query to fetch data
        Meant for one-time use
        """
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            cursor.execute(command)
            rows = cursor.fetchall()
            db.commit()
            db.close()
            return rows
        except sqlite3.Error as error:
            logging.error("Failed to execute fetch.", error)
            if db:
                db.close()
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
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = """INSERT INTO survey
                        (name, region_id, year_start, year_end) 
                        VALUES (?, ?, ?, ?);"""
            data_tuple = (name, region_id, year_start, year_end)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            logging.error("Failed to add survey: ", error)
            if db:
                db.close()
            return None
        
    def add_region(self, name: str):
        """
        Add a region with
            - name (str) Not Null
        """
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = """INSERT INTO region (name) VALUES (?);"""
            data_tuple = (name,)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            logging.error("Failed to add region: ", error)
            if db:
                db.close()
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
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = """INSERT INTO station
                        (name, lat, long, survey_id) 
                        VALUES (?, ?, ?, ?);"""
            data_tuple = (name, lat, long, survey_id)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            logging.error("Failed to add station: ", error)
            if db:
                db.close()
            return None

    def add_species(self, binomen: str, common: str):
        """
        Add species with
            - binomen (str) NOT NULL: Scientific name
            - common (str) NOT NULL: common name
        """
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = """INSERT INTO species
                        (binomen, common) 
                        VALUES (?, ?);"""
            data_tuple = (binomen, common)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            logging.error("Failed to add species: ", error)
            if db:
                db.close()
            return None

    def add_individual(self, name: str, species_id: Optional[int]=None,
                       sex: Optional[str]=None, age: Optional[str]=None):
        """
        Add an individual with
            - name (str)
            - species_id (int)
            - sex (str)
            - age (str)
        """
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = """INSERT INTO individual
                        (name, species_id, sex, age) 
                        VALUES (?, ?, ?, ?);"""
            data_tuple = (name, species_id, sex, age)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            logging.error("Failed to add individual: ", error)
            if db:
                db.close()
            return None

    def add_media(self, filepath: str, ext: str, timestamp: str, station_id: int,
                  sequence_id: Optional[int]=None, external_id: Optional[int]=None, 
                  comment: Optional[str]=None, favorite: int=0):
        """
        Media has 9 attributes not including id:
            id INTEGER PRIMARY KEY,
            filepath TEXT UNIQUE NOT NULL,
            ext TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            station_id INTEGER NOT NULL,
            sequence_id INTEGER,
            external_id INTEGER,
            comment TEXT,
            favorite INTEGER,
        """
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = """INSERT INTO media
                        (filepath, ext, timestamp, station_id,
                        sequence_id, external_id, comment, favorite) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?);"""
            data_tuple = (filepath, ext, timestamp, station_id, 
                          sequence_id, external_id, comment, favorite)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
    
        # filepath already exists
        except sqlite3.IntegrityError as error:
            if error.sqlite_errorname == "SQLITE_CONSTRAINT_UNIQUE":
                logging.error("Failed to add media, already exists in database.")
                if db:
                    db.close()
                return "duplicate_error"
        
        except sqlite3.Error as error:
            logging.error("Failed to add media: ", error)
            if db:
                db.close()
            return None

    def add_roi(self, media_id: int, frame: int, bbox_x: float, bbox_y: float, bbox_w: float, bbox_h: float,
                species_id: Optional[int]=None, viewpoint: Optional[str]=None, reviewed: int=0, 
                individual_id: Optional[int]=None, emb: int=0):
        # Note difference in variable order, foreign keys

        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = """INSERT INTO roi
                        (media_id, frame, bbox_x, bbox_y, bbox_w, bbox_h,
                         species_id, viewpoint, reviewed, individual_id, emb) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
            data_tuple = (media_id, frame, bbox_x, bbox_y, bbox_w, bbox_h,
                          species_id, viewpoint, reviewed, individual_id, emb)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            logging.error(f"Failed to add roi for media: {media_id}.", error)
            if db:
                db.close()
            return None

    def add_sequence(self):
        # Note difference in variable order, foreign keys
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = """INSERT INTO sequence DEFAULT VALUES;"""
            cursor.execute(command)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            logging.error("Failed to add sequence: ", error)
            if db:
                db.close()
            return None
        
    def add_thumbnail(self, table, fid, filepath):
        # Note difference in variable order, foreign keys
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = f"""INSERT INTO {table}_thumbnails (fid, filepath) VALUES (?, ?);"""
            data_tuple = (fid, filepath)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            logging.error("Failed to add sequence: ", error)
            if db:
                db.close()
            return None
        
    def copy(self, table, id):
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = f"""INSERT INTO {table} SELECT * FROM table WHERE id={id};"""
            cursor.execute(command)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            logging.error("Failed to copy row: ", error)
            if db:
                db.close()
            return None

    # EDIT ---------------------------------------------------------------------
    def edit_row(self, table: str, id: int, replace: dict, allow_none=False, quiet=True):
        """
        Edit a row in place 

        Args
            - table (str):
            - id (int):
            - replace (dict): column:value captures to update
        """
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            # convert empty values to SQL NULL
            for key, value in replace.items():
                if value in (None, ''):
                    replace[key] = 'NULL'
            replace_values = ",".join(f"{k}={v}" for k, v in replace.items())
            command = f"UPDATE {table} SET {replace_values} WHERE id={id}"
            if not quiet: print(command)
            cursor.execute(command)
            db.commit()
            db.close()
            return True
        except sqlite3.Error as error:
            logging.error("Failed to update table: ", error)
            if db:
                db.close()
            return False

    def select(self, table: str, columns: str="*", row_cond: Optional[str]=None, quiet=True):
        """
        Select columns based on optional row_cond
        Returns each row as a tuple
        """
        try:
            db = sqlite3.connect(self.filepath)
            if table == "roi_emb":
                db.enable_load_extension(True)
                sqlite_vec.load(db)
                db.enable_load_extension(False)
            cursor = db.cursor()
            if row_cond:
                command = f'SELECT {columns} FROM {table} WHERE {row_cond};'
            else:
                command = f'SELECT {columns} FROM {table};'
            if not quiet: print(command)
            cursor.execute(command)
            rows = cursor.fetchall()  
            db.close()
            return rows
        except sqlite3.Error as error:
            logging.error("Failed fetch: ", error)
            if db:
                db.close()
            return None
    
    def select_join(self, table, join_table, join_cond, columns="*", row_cond: Optional[str]=None, quiet=True):
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            if row_cond:
                command = f'SELECT {columns} FROM {table} INNER JOIN {join_table} ON {join_cond} WHERE {row_cond};'
            else:
                command = f'SELECT {columns} FROM {table} INNER JOIN {join_table} ON {join_cond};'
            if not quiet: print(command)
            cursor.execute(command)
            column_names = [description[0] for description in cursor.description]
            rows = cursor.fetchall()  # returns in tuple
            db.close()
            return rows, column_names
        except sqlite3.Error as error:
            logging.error("Failed fetch: ", error)
            if db:
                db.close()
            return None, None

    def all_media(self, row_cond: Optional[str]=None):
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            columns = """roi.id, frame, bbox_x ,bbox_y, bbox_w, bbox_h, viewpoint, reviewed,
                         roi.media_id, roi.species_id, roi.individual_id, emb, filepath, ext, timestamp,
                         station_id, sequence_id, external_id, comment, favorite, binomen, common, name, sex, age"""
            if row_cond:
                command = f"""SELECT {columns} FROM roi INNER JOIN media ON roi.media_id = media.id
                                            LEFT JOIN species ON roi.species_id = species.id
                                            LEFT JOIN individual ON roi.individual_id = individual.id
                                            WHERE {row_cond};"""
            else:
                command = f"""SELECT {columns} FROM roi INNER JOIN media ON roi.media_id = media.id
                                            LEFT JOIN species ON roi.species_id = species.id
                                            LEFT JOIN individual ON roi.individual_id = individual.id;"""
            cursor.execute(command)
            column_names = [description[0] for description in cursor.description]
            rows = cursor.fetchall()  # returns in tuple
            db.close()
            return rows, column_names
        except sqlite3.Error as error:
            logging.error("Failed all_media fetch:", error)
            if db:
                db.close()
            return None, None
        
    def stations(self, row_cond=None):
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            columns = """station.id, station.name, lat, long, station.survey_id, survey.name, region.name"""
            if row_cond:
                command = f"""SELECT {columns} FROM station LEFT JOIN survey ON station.survey_id = survey.id
                                                LEFT JOIN region ON survey.region_id = region.id
                                                WHERE {row_cond};"""
            else:
                command = f"""SELECT {columns} FROM station LEFT JOIN survey ON station.survey_id = survey.id
                                                LEFT JOIN region ON survey.region_id = region.id;"""
            cursor.execute(command)
            column_names = columns.split(", ")
            rows = cursor.fetchall()  # returns in tuple
            db.close()
            return rows, column_names
        except sqlite3.Error as error:
            logging.error("Failed all_media fetch:", error)
            if db:
                db.close()
            return None, None

    def count(self, table):
        """
        Return the number of entries in a given table
        """
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]
            db.close()
            return row_count
        except sqlite3.Error as error:
            logging.error(f"Failed to count for {table}:", error)
            if db:
                db.close()
            return None

    # DELETE -------------------------------------------------------------------
    def delete(self, table, cond):
        """
        Delete Entries From table Given condition
        """
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = f'DELETE FROM {table} WHERE {cond};'
            print(command)
            cursor.execute(command)
            db.commit()
            db.close()
            return True
        except sqlite3.Error as error:
            logging.error("Failed delete: ", error)
            if db:
                db.close()
            return False

    def clear(self, table):
        """
        Clear a table without dropping it
        """
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = f'DELETE FROM {table};'
            cursor.execute(command)
            db.commit()
            db.close()
            return True
        except sqlite3.Error as error:
            logging.error(f"Failed to clear {table}: ", error)
            if db:
                db.close()
            return False

    # EMBEDDINGS ===============================================================

    def add_emb(self, embedding):
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = """INSERT INTO roi_emb (embedding)
                        VALUES (?);"""
            cursor.execute(command, [embedding])
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            logging.error("Failed to add embedding: ", error)
            if db:
                db.close()
            return None
        
    def add_emb_chroma(self, id, embedding):
        client = chromadb.PersistentClient(str(self.chroma_filepath))
        collection = client.get_collection(name="embedding_collection")
        collection.add(embeddings=[embedding], ids=[str(id)])

    def knn_chroma(self, query_id, k=3):
        client = chromadb.PersistentClient(str(self.chroma_filepath))
        collection = client.get_collection(name="embedding_collection")
        query = collection.get(ids=[str(query_id)], include=['embeddings'])['embeddings']
        knn = collection.query(query_embeddings=query, n_results=k+1)
        return knn

    def knn(self, query, k=3, metric='cosine'):
        """
        Return the knn for a query embedding
        """
        try:
            db = sqlite3.connect(self.filepath)
            db.enable_load_extension(True)
            sqlite_vec.load(db)
            db.enable_load_extension(False)
            cursor = db.cursor()
            if metric == 'Cosine':
                command = """SELECT
                                rowid,
                                vec_distance_cosine(embedding, ?) as dist_cos
                                FROM roi_emb
                                ORDER by dist_cos
                                LIMIT ?;
                            """
            elif metric == 'L2':
                command = f"""SELECT
                            rowid,
                            distance
                        FROM roi_emb
                        WHERE embedding MATCH ?
                        ORDER BY distance
                        LIMIT ?
                        """
            else:
                return
            data_tuple = (query, k+1)
            cursor.execute(command, data_tuple)
            results = cursor.fetchall()
            db.close()
            return results
        except sqlite3.Error as error:
            logging.error("Failed to get knn for ROI", error)
            if db:
                db.close()
            return None

    def clear_emb(self):
        """
        Clear vector database and rebuild (no way to delete)
        """
        client = chromadb.PersistentClient(str(self.chroma_filepath))
        client.delete_collection(name="embedding_collection")
        setup_chromadb(self.key, self.chroma_filepath)