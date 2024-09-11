'''
Class Definition for MatchyPatchyDB
'''
import sqlite3
from . import setup


class MatchyPatchyDB():
    def __init__(self, filepath='matchypatchy.db'):
        self.filepath = filepath
        self.initiate = setup.setup_database(self.filepath)
        print(self.validate())
    
    def validate(self):
        db = sqlite3.connect(self.filepath)
        cursor = db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
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
                viewpoint=None, reviewed=0, iid=None, emb_id=None):
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            command = """INSERT INTO roi
                        (frame, bbox_x, bbox_y, bbox_w, bbox_h, viewpoint,
                        media_id, species_id, reviewed, iid, emb_id) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
            data_tuple = (frame, bbox_x, bbox_y, bbox_w, bbox_h, viewpoint,
                          media_id, species_id, reviewed, iid, emb_id)
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
            # db.load_extension("vec0")
            db.load_extension("C:/Users/tswanson/matchypatchy/matchypatchy/sqlite_vec/vec0")
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
        
    def fetch_table(self, table):
        db = sqlite3.connect(self.filepath)
        cursor = db.cursor()
        command = f'SELECT * FROM {table};'
        cursor.execute(command)
        rows = cursor.fetchall()
        db.close()
        return rows
    
    def fetch_columns(self, table, columns):
        # check if columns is list, concat
        db = sqlite3.connect(self.filepath)
        cursor = db.cursor()
        command = f'SELECT id, {columns} FROM {table};'
        cursor.execute(command)
        rows = cursor.fetchall()  # returns in tuple
        db.close()
        return rows
    
    def fetch_rows(self, table, row_cond, columns="*"):
        db = sqlite3.connect(self.filepath)
        cursor = db.cursor()
        command = f'SELECT {columns} FROM {table} WHERE {row_cond};'
        print(command)
        cursor.execute(command)
        rows = cursor.fetchall()  # returns in tuple
        db.close()
        return rows
    

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