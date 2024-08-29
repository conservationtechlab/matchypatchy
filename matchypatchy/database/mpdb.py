'''
Class Definition for MatchyPatchyDB
'''
import sqlite3

from . import setup

class MatchyPatchyDB():
    def __init__(self, filepath='matchypatchy.db'):
        self.filepath = filepath
        self.initiate = setup.setup_database(self.filepath)
    
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
            insert_survey = """INSERT INTO survey
                            (name, year_start, year_end, region) 
                            VALUES (?, ?, ?, ?);"""
            data_tuple = (name,  year_start, year_end, region)
            cursor.execute(insert_survey, data_tuple)
            db.commit()
            db.close()
            return True
        except sqlite3.Error as error:
            print("Failed to add survey", error)
            if db:
                db.close()
            return False
        
    def add_site(self, name, lat, long, survey_id):
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            insert_survey = """INSERT INTO site
                            (name, lat, long, survey_id) 
                            VALUES (?, ?, ?, ?);"""
            data_tuple = (name,  lat, long, survey_id)
            cursor.execute(insert_survey, data_tuple)
            db.commit()
            db.close()
            return True
        except sqlite3.Error as error:
            print("Failed to add site", error)
            if db:
                db.close()
            return False
        
    def add_media(self, filepath, ext, site_id, datetime=None, comment=None):
        try:
            db = sqlite3.connect(self.filepath)
            cursor = db.cursor()
            insert_survey = """INSERT INTO site
                            (filepath, ext, datetime, comment, site_id) 
                            VALUES (?, ?, ?, ?, ?);"""
            data_tuple = (filepath, ext, datetime, comment, site_id)
            cursor.execute(insert_survey, data_tuple)
            db.commit()
            db.close()
            return True
        except sqlite3.Error as error:
            print(f"Failed to add media: {filepath}.", error)
            if db:
                db.close()
            return False
        
    def fetch_table(self, table):
        db = sqlite3.connect(self.filepath)
        cursor = db.cursor()
        cursor.execute(f'SELECT * FROM {table};')
        rows = cursor.fetchall()
        db.close()
        return rows
    
    def fetch_columns(self, table, columns):
        # check if columns is list, concat
        db = sqlite3.connect(self.filepath)
        cursor = db.cursor()
        cursor.execute(f'SELECT id, {columns} FROM {table};')
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
            print(command)
            cursor.execute(command)
            db.commit()
            db.close()
            return True
        except sqlite3.Error as error:
            print("Failed to delete", error)
            if db:
                db.close()
            return False
        