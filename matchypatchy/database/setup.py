"""
Set Up matchypatchy Database
"""
import logging
import sqlite3
from matchypatchy import sqlite_vec


def setup_database(filepath='matchypatchy.db'):
    # Connect to SQLite database
    db = sqlite3.connect(filepath)
    cursor = db.cursor()
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    cursor.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS roi_emb USING vec0 (embedding float[2152]);''')

    # REGION
    # Corresponds to "Site" in CameraBase
    cursor.execute('''CREATE TABLE IF NOT EXISTS region (
                        id INTEGER PRIMARY KEY,
                        name TEXT UNIQUE NOT NULL );''')

    # SURVEY
    cursor.execute('''CREATE TABLE IF NOT EXISTS survey (
                        id INTEGER PRIMARY KEY,
                        name TEXT UNIQUE NOT NULL,
                        region_id INTEGER NOT NULL,
                        year_start INTEGER,
                        year_end INTEGER,
                        FOREIGN KEY (region_id) REFERENCES region (id) );''')

    # STATION
    cursor.execute('''CREATE TABLE IF NOT EXISTS station (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        lat REAL,
                        long REAL,
                        survey_id INTEGER NOT NULL,
                        FOREIGN KEY (survey_id) REFERENCES survey (id) );''')

    # MEDIA
    cursor.execute('''CREATE TABLE IF NOT EXISTS media (
                        id INTEGER PRIMARY KEY,
                        filepath TEXT UNIQUE NOT NULL,
                        ext TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        station_id INTEGER NOT NULL,
                        sequence_id INTEGER,
                        external_id INTEGER,
                        comment TEXT,
                        favorite INTEGER NOT NULL,
                        FOREIGN KEY (station_id) REFERENCES station (id),
                        FOREIGN KEY (sequence_id) REFERENCES sequence (id) );''')

    # ROI
    cursor.execute('''CREATE TABLE IF NOT EXISTS roi (
                        id INTEGER PRIMARY KEY,
                        media_id INTEGER NOT NULL,
                        frame INTEGER NOT NULL,
                        bbox_x REAL NOT NULL,
                        bbox_y REAL NOT NULL,
                        bbox_w REAL NOT NULL,
                        bbox_h REAL NOT NULL,
                        species_id INTEGER,
                        viewpoint INTEGER,
                        reviewed INTEGER NOT NULL,
                        individual_id INTEGER,
                        emb_id INTEGER,
                        FOREIGN KEY(media_id) REFERENCES media (id)
                        FOREIGN KEY(species_id) REFERENCES species (id)
                        FOREIGN KEY(individual_id) REFERENCES individual (id)
                        FOREIGN KEY(emb_id) REFERENCES roi_emb (rowid) );''')

    # SPECIES
    cursor.execute('''CREATE TABLE IF NOT EXISTS species (
                        id INTEGER PRIMARY KEY,
                        binomen TEXT NOT NULL,
                        common TEXT NOT NULL );''')

    # INDIVIDUAL
    cursor.execute('''CREATE TABLE IF NOT EXISTS individual (
                        id INTEGER PRIMARY KEY,
                        species_id INTEGER,
                        name TEXT NOT NULL,
                        sex TEXT,
                        age TEXT,
                        FOREIGN KEY(species_id) REFERENCES species (id));''')

    # SEQUENCE
    cursor.execute('''CREATE TABLE IF NOT EXISTS sequence (
                        id INTEGER PRIMARY KEY);''')

    # VIEWPOINT
    cursor.execute('''DROP TABLE IF EXISTS viewpoint;''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS viewpoint (
                        id INTEGER PRIMARY KEY,
                        value TEXT
                        name TEXT);''')

    # THUMBNAILS
    cursor.execute('''DROP TABLE IF EXISTS media_thumbnails;''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS media_thumbnails (
                        id INTEGER PRIMARY KEY,
                        fid INTEGER NOT NULL,
                        filepath TEXT NOT NULL,
                        FOREIGN KEY(fid) REFERENCES media (id));''')

    cursor.execute('''DROP TABLE IF EXISTS roi_thumbnails;''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS roi_thumbnails (
                        id INTEGER PRIMARY KEY,
                        fid INTEGER NOT NULL,
                        filepath TEXT NOT NULL,
                        FOREIGN KEY(fid) REFERENCES roi (id));''')

    # Commit changes and close connection
    db.commit()
    logging.info('Database initiated.')
    db.close()
    return True


if __name__ == "__main__":
    setup_database()
