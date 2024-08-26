import sqlite3
from matchypatchy import sqlite_vec
# fetch from master table
#cursor.execute("SELECT name FROM sqlite_master")


def setup_database(filepath='matchypatchy.db'):
    # Connect to SQLite database
    db = sqlite3.connect(filepath)
    cursor = db.cursor()
    
    # EMBEDDING
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS roi_emb USING vec0 (embedding float[2152])")
    
    # SURVEY
    cursor.execute('''CREATE TABLE IF NOT EXISTS survey (
                        survey_id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        year_start INTEGER NOT NULL,
                        year_end INTEGER,
                        region TEXT NOT NULL )''')

    # SITE
    cursor.execute('''CREATE TABLE IF NOT EXISTS site (
                        site_id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        lat REAL NOT NULL,
                        long REAL NOT NULL,
                        survey_id INTEGER NOT NULL,
                        FOREIGN KEY (survey_id) REFERENCES survey (survey_id) )''')

    # MEDIA
    cursor.execute('''CREATE TABLE IF NOT EXISTS media (
                        file_id INTEGER PRIMARY KEY,
                        filepath TEXT NOT NULL,
                        ext TEXT NOT NULL,
                        datetime TEXT,
                        comment TEXT,
                        site_id INTEGER NOT NULL,
                        FOREIGN KEY (site_id) REFERENCES site (site_id) )''')

    # ROI
    cursor.execute('''CREATE TABLE IF NOT EXISTS roi (
                        rid INTEGER PRIMARY KEY,
                        frame INTEGER NOT NULL,
                        bbox_x REAL NOT NULL,
                        bbox_y REAL NOT NULL,
                        bbox_w REAL NOT NULL,
                        bbox_h REAL NOT NULL,
                        file_id INTEGER NOT NULL,
                        species_id TEXT NOT NULL,
                        reviewed INTEGER NOT NULL,
                        iid INTEGER,
                        emb_id INTEGER,
                        FOREIGN KEY(file_id) REFERENCES media (file_id)
                        FOREIGN KEY(species_id) REFERENCES species (species_id)
                        FOREIGN KEY(iid) REFERENCES individual (iid)
                        FOREIGN KEY(emb_id) REFERENCES roi_emb (rowid) )''')
    
    # SPECIES
    cursor.execute('''CREATE TABLE IF NOT EXISTS species (
                        species_id INTEGER PRIMARY KEY,
                        binomen TEXT NOT NULL,
                        common TEXT NOT NULL )''')
    
    # INDIVIDUAL
    cursor.execute('''CREATE TABLE IF NOT EXISTS individual (
                        iid INTEGER PRIMARY KEY,
                        species_id INT NOT NULL,
                        name TEXT NOT NULL,
                        sex TEXT,
                        FOREIGN KEY(species_id) REFERENCES species (species_id)
                    )''')


    # Commit changes and close connection
    db.commit()
    print('Database initiated.')
    db.close()


class MatchyPatchyDB():
    def __init__(self, filepath='matchypatchy.db'):
        self.filepath = filepath
        setup_database(self.filepath)
    
    def validate(self):
        db = sqlite3.connect(self.filepath)
        cursor = db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        db.close()
        return tables


if __name__ == "__main__":
    setup_database()
