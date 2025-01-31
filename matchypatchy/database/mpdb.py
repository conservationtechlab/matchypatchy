'''
Class Definition for MatchyPatchyDB
'''
import logging
from typing import Optional
import sqlite3

from matchypatchy.database.setup import setup_database
from matchypatchy import sqlite_vec


class MatchyPatchyDB():
    def __init__(self, filepath='matchypatchy.db'):
        self.filepath = filepath
        self.initiate = setup_database(self.filepath)

    def info(self):
        """
        Validate All Tables Are Present
        """
        db = sqlite3.connect(self.filepath)
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
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
        cursor.execute("SELECT COUNT(rowid) FROM roi_emb")
        emb = cursor.fetchone()[0]
        print(f"Emb: {emb}")
        logging.info(f"Emb: {emb}")
        db.close()

    def validate(self):
        db = sqlite3.connect(self.filepath)
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        cursor = db.cursor()
        cursor.execute("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table', 'index', 'view', 'trigger')")
        schema = cursor.fetchall()

        for name, obj_type, sql in schema:
            print(f"{obj_type.upper()}: {name}\n{sql}\n")

        #table_check = tables == [('sqlite_sequence',), ('region',), ('survey',), ('station',), 
        #                 ('media',), ('roi',), ('species',), ('individual',), ('sequence',), 
        #                 ('roi_emb',), ('roi_emb_chunks',), ('roi_emb_rowids',), ('roi_emb_vector_chunks00',), ('thumbnails',)]
        #print(table_check)
        

    def _command(self, command):
        """
        Execute a specific sql query to fetch data
        Meant for one-time use
        """
        try:
            db = sqlite3.connect(self.filepath)
            db.enable_load_extension(True)
            sqlite_vec.load(db)
            db.enable_load_extension(False)
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
            return False

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
            return False
        
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
            print(data_tuple)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            logging.error("Failed to add region: ", error)
            if db:
                db.close()
            return False


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
            return False

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
            return False

    def add_individual(self, species_id: int, name: str, sex: Optional[str]=None):
        """
        Add an individual with
            - species_id (int)
            - name (str)
            - sex (str)
        """
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = """INSERT INTO individual
                        (species_id, name, sex) 
                        VALUES (?, ?, ?);"""
            data_tuple = (species_id, name, sex)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            logging.error("Failed to add individual: ", error)
            if db:
                db.close()
            return False

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
        except sqlite3.Error as error:
            logging.error("Failed to add media: ", error)
            if db:
                db.close()
            return False

    def add_roi(self, media_id: int, frame: int, bbox_x: float, bbox_y: float, bbox_w: float, bbox_h: float,
                species_id: Optional[int]=None, viewpoint: Optional[str]=None, reviewed: int=0, 
                individual_id: Optional[int]=None, emb_id: int=0):
        # Note difference in variable order, foreign keys

        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = """INSERT INTO roi
                        (media_id, frame, bbox_x, bbox_y, bbox_w, bbox_h,
                         species_id, viewpoint, reviewed, individual_id, emb_id) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
            data_tuple = (media_id, frame, bbox_x, bbox_y, bbox_w, bbox_h,
                          species_id, viewpoint, reviewed, individual_id, emb_id)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            logging.error(f"Failed to add roi for media: {media_id}.", error)
            if db:
                db.close()
            return False

    def add_emb(self, embedding):
        try:
            db = sqlite3.connect(self.filepath)
            db.enable_load_extension(True)
            sqlite_vec.load(db)
            db.enable_load_extension(False)
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
            return False

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
            return False
        
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
            return False

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
            return False
    
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
            return False

    def all_media(self, row_cond: Optional[str]=None):
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            columns = """roi.id, frame, bbox_x ,bbox_y, bbox_w, bbox_h, viewpoint, reviewed, 
                         roi.media_id, roi.species_id, roi.individual_id, emb_id, filepath, ext, timestamp, 
                         station_id, sequence_id, external_id, comment, favorite, binomen, common, name, sex"""
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
            return False

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
        
    def clear_emb(self):
        """
        Clear vector database and rebuild (no way to delete)
        """
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            db.enable_load_extension(True)
            sqlite_vec.load(db)
            db.enable_load_extension(False)
            cursor.execute("DROP TABLE IF EXISTS roi_emb;")
            cursor.execute("DROP TABLE IF EXISTS roi_emb_chunks;")
            cursor.execute("DROP TABLE IF EXISTS roi_emb_rowids;")
            cursor.execute("DROP TABLE IF EXISTS roi_emb_vector_chunks00;")
            db.commit()
            cursor.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS roi_emb USING vec0 (embedding float[2152]);''')
            db.commit()
            db.close()
            return True
        except sqlite3.Error as error:
            logging.error(f"Failed to clear roi_emb: ", error)
            if db:
                db.close()
            return False 
        
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
            return False 
        
    def knn(self, query, k=3):
        """
        Return the knn for a query embedding
        """
        try:
            db = sqlite3.connect(self.filepath)
            db.enable_load_extension(True)
            sqlite_vec.load(db)
            db.enable_load_extension(False)
            cursor = db.cursor()
            command = f"""SELECT
                            rowid,
                            distance
                        FROM roi_emb
                        WHERE embedding MATCH ?
                        ORDER BY distance
                        LIMIT ?
                        """
            data_tuple = (query, k+1)
            cursor.execute(command, data_tuple)
            results = cursor.fetchall()
            db.close()
            return results
        except sqlite3.Error as error:
            logging.error("Failed to get knn for ROI", error)
            if db:
                db.close()
            return False 
