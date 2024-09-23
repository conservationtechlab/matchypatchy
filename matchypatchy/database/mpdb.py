'''
Class Definition for MatchyPatchyDB
'''
import sqlite3
from . import setup
from .. import sqlite_vec 


class MatchyPatchyDB():
    def __init__(self, filepath='matchypatchy.db'):
        self.filepath = filepath
        self.initiate = setup.setup_database(self.filepath)
        print(self.validate())
    
    def validate(self):
        db = sqlite3.connect(self.filepath)
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        cursor = db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        cursor.execute(f"PRAGMA table_info(roi_emb)")
        columns = cursor.fetchall()
        print(columns)
        db.close()
        return tables
    
    def add_survey(self, name, year_start, year_end, region):
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = """INSERT INTO survey
                        (name, year_start, year_end, region) 
                        VALUES (?, ?, ?, ?);"""
            data_tuple = (name,  year_start, year_end, region)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            print("Failed to add survey", error)
            if db:
                db.close()
            return False
        
    def add_site(self, name, lat, long, survey_id):
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = """INSERT INTO site
                        (name, lat, long, survey_id) 
                        VALUES (?, ?, ?, ?);"""
            data_tuple = (name, lat, long, survey_id)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            print("Failed to add site", error)
            if db:
                db.close()
            return False
        
    def add_species(self, binomen, common):
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
            print("Failed to add site", error)
            if db:
                db.close()
            return False
        
    def add_media(self, filepath, ext, site_id, datetime=None, sequence_id=None, comment=None, favorite=0):
        """
        Media has 7 attributes not including id:
            id INTEGER PRIMARY KEY
            filepath TEXT NOT NULL: local filepath
            ext TEXT NOT NULL: file extension
            datetime TEXT: filemodifydate
            sequence_id INTEGER: sequence id to link media
            comment TEXT: any str value
            favorite INTEGER: 0 default, 1 if favorited
            site_id INTEGER NOT NULL: foreign key to site
        """
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = """INSERT INTO media
                        (filepath, ext, datetime, sequence_id, 
                        comment, favorite, site_id) 
                        VALUES (?, ?, ?, ?, ?, ?, ?);"""
            data_tuple = (filepath, ext, datetime, sequence_id, comment, favorite, site_id)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            print(f"Failed to add media: {filepath}.", error)
            if db:
                db.close()
            return False
        
    def add_roi(self, frame, bbox_x, bbox_y, bbox_w, bbox_h, media_id, species_id,
                viewpoint=None, reviewed=0, individual_id=0, emb_id=0):
        # Note difference in variable order, foreign keys
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = """INSERT INTO roi
                        (frame, bbox_x, bbox_y, bbox_w, bbox_h, viewpoint, reviewed,
                        media_id, species_id, individual_id, emb_id) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
            data_tuple = (frame, bbox_x, bbox_y, bbox_w, bbox_h, viewpoint, reviewed,
                          media_id, species_id, individual_id, emb_id)
            cursor.execute(command, data_tuple)
            id = cursor.lastrowid
            db.commit()
            db.close()
            return id
        except sqlite3.Error as error:
            print(f"Failed to add roi for media: {media_id}.", error)
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
            print("Failed to add embedding.", error)
            if db:
                db.close()
            return False
        
    def edit_row(self, table, id, replace):
        """
        Args
            - table (str):
            - id (int):
            - replace (dict): column:value pairs to update

        """
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            replace_values = ",".join(f"{k}={v}" for k,v in replace.items())
            command = f"UPDATE {table} SET {replace_values} WHERE id={id}"
            print(command)
            cursor.execute(command)
            db.commit()
            db.close()
            return True
        except sqlite3.Error as error:
            print("Failed to update table", error)
            if db:
                db.close()
            return False
    
    def select(self, table, columns="*", row_cond=None):
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
            print(command)
            cursor.execute(command)
            rows = cursor.fetchall()  # returns in tuple
            db.close()
            return rows
        except sqlite3.Error as error:
            print("Failed to fetch", error)
            if db:
                db.close()
            return False
    
    def select_join(self, table, join_table, join_cond, columns="*"):
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = f'SELECT {columns} FROM {table} INNER JOIN {join_table} ON {join_cond};'
            print(command)
            cursor.execute(command)
            rows = cursor.fetchall()  # returns in tuple
            db.close()
            return rows
        except sqlite3.Error as error:
            print("Failed to fetch", error)
            if db:
                db.close()
            return False

    def delete(self, table, cond):
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = f'DELETE FROM {table} WHERE {cond};'
            cursor.execute(command)
            db.commit()
            db.close()
            return True
        except sqlite3.Error as error:
            print("Failed to delete", error)
            if db:
                db.close()
            return False 
        
    def clear(self, table):
        try:
            db = sqlite3.connect(self.filepath)
            # enable clear vec database
            if table == "roi_emb":
                db.enable_load_extension(True)
                sqlite_vec.load(db)
                db.enable_load_extension(False)
            cursor = db.cursor()
            command = f'DELETE FROM {table};'
            cursor.execute(command)
            db.commit()
            db.close()
            return True
        except sqlite3.Error as error:
            print(f"Failed to clear {table}", error)
            if db:
                db.close()
            return False 
        
    def knn(self, query, k=3):
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
            data_tuple = (query,k)
            cursor.execute(command,data_tuple)
            results = cursor.fetchall()
            return results

        except sqlite3.Error as error:
            print(f"Failed to get knn for ROI", error)
            if db:
                db.close()
            return False 


"""SELECT
                            roi_emb.rowid,
                            distance,
                            roi.id,
                            iid,
                        FROM roi_emb
                        LEFT JOIN roi ON roi.emb_id = roi_emb.rowid
                        WHERE embedding MATCH ?
                            AND k = ?
                        ORDER BY distance
                        """