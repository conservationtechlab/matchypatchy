"""
Set Up matchypatchy Database
"""
from contextlib import contextmanager
from datetime import datetime
import shutil
import sqlite3
import chromadb
from chromadb.config import Settings

from matchypatchy import __version__

# Increment when the SQLite schema changes and add a matching entry to MIGRATIONS.
# Databases created before schema versioning have no schema_version column and are treated as version 1.
SCHEMA_VERSION = 2

# Tables rebuilt by a migration, {name} lets the migration create them under a temporary name.
# A relative path is only unique within its base directory: D:/2023/Site01/IMG_0001.JPG and
# D:/2024/Site01/IMG_0001.JPG are both Site01/IMG_0001.JPG
# detection_done is 1 once a file has been run through the detector, or given a full-image roi
# when no detector was selected, so later processing only runs the files that still need it
MEDIA_TABLE = '''CREATE TABLE IF NOT EXISTS {name} (
                id INTEGER PRIMARY KEY,
                base_dir_id INTEGER NOT NULL,
                relative_path TEXT NOT NULL,
                sha256 TEXT UNIQUE NOT NULL,
                ext TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                station_id INTEGER NOT NULL,
                camera_id INTEGER,
                sequence_id INTEGER,
                external_id INTEGER,
                comment TEXT,
                detection_done INTEGER NOT NULL DEFAULT 0,
                UNIQUE (base_dir_id, relative_path),
                FOREIGN KEY (base_dir_id) REFERENCES uploads (id) ON DELETE CASCADE,
                FOREIGN KEY (station_id) REFERENCES station (id) ON DELETE CASCADE,
                FOREIGN KEY (camera_id) REFERENCES camera (id) ON DELETE SET NULL,
                FOREIGN KEY (sequence_id) REFERENCES sequence (id) ON DELETE SET NULL);'''

INDIVIDUAL_TABLE = '''CREATE TABLE IF NOT EXISTS {name} (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                sex TEXT);'''


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

    try:
        cursor = db.cursor()

        # add key to database
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY,
                mp_version TEXT NOT NULL,
                key TEXT UNIQUE NOT NULL,
                schema_version INTEGER NOT NULL DEFAULT 0);''')
        cursor.execute("INSERT INTO metadata (mp_version, key, schema_version) VALUES (?, ?, ?);",
                       (__version__, key, SCHEMA_VERSION))

        # REGION
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS region (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                timezone TEXT);''')

        # SURVEY
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS survey (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                region_id INTEGER,
                year_start INTEGER,
                year_end INTEGER,
                FOREIGN KEY (region_id) REFERENCES region (id) ON DELETE SET NULL);''')

        # STATION
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS station (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                lat REAL,
                long REAL,
                survey_id INTEGER NOT NULL,
                FOREIGN KEY (survey_id) REFERENCES survey (id) ON DELETE CASCADE);''')

        # CAMERA
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS camera (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                station_id INTEGER NOT NULL,
                FOREIGN KEY (station_id) REFERENCES station (id) ON DELETE CASCADE);''')

        # UPLOADS
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY,
                base_dir TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);''')

        # MEDIA
        cursor.execute(MEDIA_TABLE.format(name="media"))

        # ROI
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS roi (
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
        cursor.execute(INDIVIDUAL_TABLE.format(name="individual"))

        # SEQUENCE
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS sequence (id INTEGER PRIMARY KEY);''')

        # THUMBNAILS
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS media_thumbnails (
                id INTEGER PRIMARY KEY,
                fid INTEGER UNIQUE NOT NULL,
                filepath TEXT NOT NULL,
                FOREIGN KEY(fid) REFERENCES media (id) ON DELETE CASCADE);''')

        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS roi_thumbnails (
                id INTEGER PRIMARY KEY,
                fid INTEGER UNIQUE NOT NULL,
                filepath TEXT NOT NULL,
                FOREIGN KEY(fid) REFERENCES roi (id) ON DELETE CASCADE);''')

        # Commit changes and close connection
        db.commit()

    finally:
        # Only close if we created the connection
        if created_connection:
            db.close()

    return db


def schema_signature(db):
    """Structural description of a SQLite schema (columns, foreign keys, unique constraints per table)

    Compared instead of the raw CREATE statements, which SQLite rewrites after ALTER TABLE
    """
    cursor = db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    signature = {}
    for (table,) in cursor.fetchall():
        # (name, type, notnull, default, pk)
        columns = [(c[1], c[2].upper(), c[3], c[4], c[5])
                   for c in cursor.execute(f'PRAGMA table_info("{table}")').fetchall()]
        # (referenced table, from, to, on_update, on_delete)
        foreign_keys = sorted((f[2], f[3], f[4], f[5], f[6])
                              for f in cursor.execute(f'PRAGMA foreign_key_list("{table}")').fetchall())
        uniques = []
        for index in cursor.execute(f'PRAGMA index_list("{table}")').fetchall():
            if index[2]:  # unique
                uniques.append(tuple(i[2] for i in cursor.execute(f'PRAGMA index_info("{index[1]}")').fetchall()))
        signature[table] = {"columns": columns, "foreign_keys": foreign_keys, "unique": sorted(uniques)}
    return signature


def expected_schema_signature():
    """Schema signature of a freshly created database"""
    db = sqlite3.connect(":memory:")
    try:
        setup_database("00000", None, db=db)
        return schema_signature(db)
    finally:
        db.close()


# MIGRATIONS ===================================================================
def get_schema_version(db):
    """Get schema version of an existing database, 1 if it predates schema versioning"""
    columns = [c[1] for c in db.execute("PRAGMA table_info(metadata)").fetchall()]
    if "schema_version" not in columns:
        return 1
    return db.execute("SELECT schema_version FROM metadata WHERE id=1;").fetchone()[0]


# Migration functions
def _rebuild_table(db, table, create):
    """
    Recreate a table from its current CREATE statement, keeping its rows

    SQLite cannot change a table's constraints in place. Columns the new table
    no longer has are dropped. Foreign keys must be off, or dropping the old
    table cascades to the rows that reference it.
    """
    db.execute(create.format(name=f"{table}_new"))
    new_columns = [c[1] for c in db.execute(f'PRAGMA table_info("{table}_new")').fetchall()]
    old_columns = [c[1] for c in db.execute(f'PRAGMA table_info("{table}")').fetchall()]
    columns = ", ".join(c for c in new_columns if c in old_columns)
    db.execute(f"INSERT INTO {table}_new ({columns}) SELECT {columns} FROM {table};")
    db.execute(f"DROP TABLE {table};")
    db.execute(f"ALTER TABLE {table}_new RENAME TO {table};")


@contextmanager
def _schema_change(db):
    """
    Run a migration as one transaction with foreign keys off

    Rebuilding a table drops the old one, which would otherwise cascade to the
    rows that reference it. Foreign keys can't be switched inside a transaction.
    """
    db.commit()
    foreign_keys = db.execute("PRAGMA foreign_keys;").fetchone()[0]
    db.execute("PRAGMA foreign_keys = OFF;")
    try:
        db.execute("BEGIN;")
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.execute(f"PRAGMA foreign_keys = {foreign_keys};")


def _migrate_1_to_2(db):
    """
    Bring a database from before schema versioning up to date

    Adds metadata.schema_version, drops the unused individual.age, makes
    media.relative_path unique within its base directory instead of across all of
    them, and adds media.detection_done
    """
    with _schema_change(db):
        metadata_columns = [c[1] for c in db.execute("PRAGMA table_info(metadata)").fetchall()]
        if "schema_version" not in metadata_columns:
            db.execute("ALTER TABLE metadata ADD COLUMN schema_version INTEGER NOT NULL DEFAULT 0;")
        _rebuild_table(db, "individual", INDIVIDUAL_TABLE)
        _rebuild_table(db, "media", MEDIA_TABLE)
        # a roi with a box came from a detector (or the full-image fallback); media without
        # one, either no rois or only rois imported without a box, still need detection
        db.execute("""UPDATE media SET detection_done = 1
                      WHERE EXISTS (SELECT 1 FROM roi WHERE roi.media_id = media.id AND roi.bbox_w != -1);""")


MIGRATIONS = {1: _migrate_1_to_2}


def migrate_database(db, filepath, logger):
    """Upgrade an existing database to SCHEMA_VERSION, backing up the file first

    Returns the schema version of the database after migration
    """
    version = get_schema_version(db)
    if version >= SCHEMA_VERSION:
        return version

    backup_path = filepath.with_name(f"{filepath.name}.schema{version}.bak")
    shutil.copy2(filepath, backup_path)
    logger.info(f"Migrating database schema from version {version} to {SCHEMA_VERSION}, backup saved to {backup_path}")

    while version < SCHEMA_VERSION:
        MIGRATIONS[version](db)
        version += 1
        db.execute("UPDATE metadata SET schema_version=? WHERE id=1;", (version,))
        db.commit()
        logger.info(f"Database schema migrated to version {version}")
    return version


def setup_chromadb(key, filepath):
    """Set up ChromaDB vector database for embeddings"""
    client = chromadb.PersistentClient(str(filepath), settings=Settings(anonymized_telemetry=False))
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
