"""
Set Up matchypatchy Database
"""
import sqlite3
import chromadb
from datetime import datetime
from matchypatchy import __version__


def setup_database(key, filepath, db=None):
    """Set up SQLite database with required tables
    
    Args:
        key: Database key/version identifier
        filepath: Path to SQLite database file
        db: Optional existing connection (for thread-local usage)
    """
    # Use provided connection or create new one
    created_connection = db is None
    
    # Use provided connection or create new one
    if created_connection:
        db = sqlite3.connect(filepath)
    
    cursor = db.cursor()

    # add key to database
    cursor.execute('''CREATE TABLE IF NOT EXISTS metadata (
                        id INTEGER PRIMARY KEY,
                        mp_version TEXT NOT NULL,
                        key TEXT UNIQUE NOT NULL );''')
    cursor.execute(f"""INSERT INTO metadata (mp_version, key) VALUES ('{__version__}', '{key}');""")

    # REGION
    # Corresponds to "Site" in CameraBase
    cursor.execute('''CREATE TABLE IF NOT EXISTS region (
                        id INTEGER PRIMARY KEY,
                        name TEXT UNIQUE NOT NULL,
                        timezone TEXT);''')

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

    # UPLOADS
    cursor.execute('''CREATE TABLE IF NOT EXISTS uploads (
                        id INTEGER PRIMARY KEY,
                        base_dir TEXT UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);''')

    # MEDIA
    cursor.execute('''CREATE TABLE IF NOT EXISTS media (
                        id INTEGER PRIMARY KEY,
                        base_dir_id INTEGER NOT NULL,
                        relative_path TEXT UNIQUE NOT NULL,
                        sha256 TEXT UNIQUE NOT NULL,
                        ext TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        station_id INTEGER NOT NULL,
                        camera_id INTEGER,
                        sequence_id INTEGER,
                        external_id INTEGER,
                        comment TEXT,
                        FOREIGN KEY (base_dir_id) REFERENCES uploads (id),
                        FOREIGN KEY (station_id) REFERENCES station (id),
                        FOREIGN KEY (camera_id) REFERENCES camera (id),
                        FOREIGN KEY (sequence_id) REFERENCES sequence (id));''')

    # ROI
    cursor.execute('''CREATE TABLE IF NOT EXISTS roi (
                        id INTEGER PRIMARY KEY,
                        media_id INTEGER NOT NULL,
                        frame INTEGER NOT NULL,
                        bbox_x REAL NOT NULL,
                        bbox_y REAL NOT NULL,
                        bbox_w REAL NOT NULL,
                        bbox_h REAL NOT NULL,
                        viewpoint INTEGER,
                        reviewed INTEGER NOT NULL,
                        favorite INTEGER NOT NULL,
                        individual_id INTEGER,
                        emb INTEGER,
                        FOREIGN KEY(media_id) REFERENCES media (id) ON DELETE CASCADE,
                        FOREIGN KEY(individual_id) REFERENCES individual (id) ON DELETE SET NULL);''')

    # INDIVIDUAL
    cursor.execute('''CREATE TABLE IF NOT EXISTS individual (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        sex TEXT,
                        age TEXT);''')

    # SEQUENCE
    cursor.execute('''CREATE TABLE IF NOT EXISTS sequence (
                        id INTEGER PRIMARY KEY);''')

    # CAMERA
    cursor.execute('''CREATE TABLE IF NOT EXISTS camera (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        station_id INTEGER NOT NULL,
                        FOREIGN KEY (station_id) REFERENCES station (id));''')

    # THUMBNAILS
    cursor.execute('''CREATE TABLE IF NOT EXISTS media_thumbnails (
                        id INTEGER PRIMARY KEY,
                        fid INTEGER UNIQUE NOT NULL,
                        filepath TEXT NOT NULL,
                        FOREIGN KEY(fid) REFERENCES media (id) ON DELETE CASCADE);''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS roi_thumbnails (
                        id INTEGER PRIMARY KEY,
                        fid INTEGER UNIQUE NOT NULL,
                        filepath TEXT NOT NULL,
                        FOREIGN KEY(fid) REFERENCES roi (id) ON DELETE CASCADE);''')

    # Commit changes and close connection
    db.commit()
    # Only close if we created the connection
    if created_connection:
        db.close()

    return db


def setup_chromadb(key, filepath):
    """Set up ChromaDB vector database for embeddings"""
    client = chromadb.PersistentClient(str(filepath))
    client.create_collection(
        name="embedding_collection",
        metadata={
            "description": "Embedding Collection",
            "created": str(datetime.now()),
            "hnsw:space": "cosine",
            "key": key
        }
    )
    return client
