"""Tests for upgrading databases built by older versions of MatchyPatchy."""
import sqlite3

import pytest

from matchypatchy.database import setup
from matchypatchy.database.mpdb import MatchyPatchyDB
from matchypatchy.database.setup import SCHEMA_VERSION, setup_chromadb


KEY = "12345"

# Schema of a database built by a released version, before schema versioning
RELEASED_SCHEMA = """
CREATE TABLE metadata (
    id INTEGER PRIMARY KEY,
    mp_version TEXT NOT NULL,
    key TEXT UNIQUE NOT NULL );
CREATE TABLE region (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    timezone TEXT);
CREATE TABLE survey (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    region_id INTEGER,
    year_start INTEGER,
    year_end INTEGER,
    FOREIGN KEY (region_id) REFERENCES region (id) ON DELETE SET NULL);
CREATE TABLE station (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    lat REAL,
    long REAL,
    survey_id INTEGER NOT NULL,
    FOREIGN KEY (survey_id) REFERENCES survey (id) ON DELETE CASCADE);
CREATE TABLE camera (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    station_id INTEGER NOT NULL,
    FOREIGN KEY (station_id) REFERENCES station (id) ON DELETE CASCADE);
CREATE TABLE uploads (
    id INTEGER PRIMARY KEY,
    base_dir TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE media (
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
    FOREIGN KEY (base_dir_id) REFERENCES uploads (id) ON DELETE CASCADE,
    FOREIGN KEY (station_id) REFERENCES station (id) ON DELETE CASCADE,
    FOREIGN KEY (camera_id) REFERENCES camera (id) ON DELETE SET NULL,
    FOREIGN KEY (sequence_id) REFERENCES sequence (id) ON DELETE SET NULL);
CREATE TABLE roi (
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
    FOREIGN KEY(individual_id) REFERENCES individual (id) ON DELETE SET NULL);
CREATE TABLE individual (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    sex TEXT,
    age TEXT);
CREATE TABLE sequence (id INTEGER PRIMARY KEY);
CREATE TABLE media_thumbnails (
    id INTEGER PRIMARY KEY,
    fid INTEGER UNIQUE NOT NULL,
    filepath TEXT NOT NULL,
    FOREIGN KEY(fid) REFERENCES media (id) ON DELETE CASCADE);
CREATE TABLE roi_thumbnails (
    id INTEGER PRIMARY KEY,
    fid INTEGER UNIQUE NOT NULL,
    filepath TEXT NOT NULL,
    FOREIGN KEY(fid) REFERENCES roi (id) ON DELETE CASCADE);
"""

ROWS = """
INSERT INTO region (id, name, timezone) VALUES (1, 'Default Region', 'UTC');
INSERT INTO survey (id, name, region_id) VALUES (1, 'Default Survey', 1);
INSERT INTO station (id, name, survey_id) VALUES (1, 'Site01', 1);
INSERT INTO uploads (id, base_dir) VALUES (1, 'D:/2023');
INSERT INTO sequence (id) VALUES (1);
INSERT INTO individual (id, name, sex, age) VALUES (1, 'Jaguar-1', 'Female', 'Adult');
INSERT INTO media (id, base_dir_id, relative_path, sha256, ext, timestamp, station_id, sequence_id, comment)
    VALUES (1, 1, 'Site01/IMG_0001.JPG', 'hash1', '.jpg', '2023-01-01 00:00:00', 1, 1, 'first');
INSERT INTO roi (id, media_id, frame, bbox_x, bbox_y, bbox_w, bbox_h, viewpoint, reviewed, favorite, individual_id, emb)
    VALUES (1, 1, 0, 0.1, 0.2, 0.3, 0.4, 0, 1, 0, 1, 1);
INSERT INTO media_thumbnails (fid, filepath) VALUES (1, 'media1.jpg');
INSERT INTO roi_thumbnails (fid, filepath) VALUES (1, 'roi1.jpg');
-- never detected, or the detector found nothing
INSERT INTO media (id, base_dir_id, relative_path, sha256, ext, timestamp, station_id)
    VALUES (2, 1, 'Site01/IMG_0002.JPG', 'hash3', '.jpg', '2023-01-01 00:01:00', 1);
-- imported with a roi but no box
INSERT INTO media (id, base_dir_id, relative_path, sha256, ext, timestamp, station_id)
    VALUES (3, 1, 'Site01/IMG_0003.JPG', 'hash4', '.jpg', '2023-01-01 00:02:00', 1);
INSERT INTO roi (id, media_id, frame, bbox_x, bbox_y, bbox_w, bbox_h, reviewed, favorite, emb)
    VALUES (2, 3, 0, -1, -1, -1, -1, 0, 0, 0);
"""


def _old_database(path, schema_version=None):
    """
    Write a populated database as an older version built it, with its embedding database

    schema_version None is a released version, 1 an unreleased build that versioned the schema
    """
    conn = sqlite3.connect(path / "matchypatchy.db")
    conn.executescript(RELEASED_SCHEMA)
    if schema_version is None:
        conn.execute("INSERT INTO metadata (mp_version, key) VALUES ('1.0', ?)", (KEY,))
    else:
        conn.execute("ALTER TABLE metadata ADD COLUMN schema_version INTEGER NOT NULL DEFAULT 0")
        conn.execute("INSERT INTO metadata (mp_version, key, schema_version) VALUES ('1.1', ?, ?)",
                     (KEY, schema_version))
    conn.executescript(ROWS)
    # age was removed before schema versioning
    if schema_version is not None:
        conn.execute("ALTER TABLE individual DROP COLUMN age")
    conn.commit()
    conn.close()
    setup_chromadb(KEY, path / "emb.db")


@pytest.fixture(params=[None, 1], ids=["released", "unreleased-v1"])
def migrated_db(request, tmp_path, null_logger):
    _old_database(tmp_path, schema_version=request.param)
    db = MatchyPatchyDB(str(tmp_path), null_logger)
    yield db, tmp_path
    db.close()


class TestMigrateToCurrent:
    def test_opens_and_validates(self, migrated_db):
        db, _ = migrated_db
        assert db.key == KEY
        assert db.db.execute("SELECT schema_version FROM metadata").fetchone()[0] == SCHEMA_VERSION

    def test_backup_is_written(self, migrated_db):
        _, path = migrated_db
        assert list(path.glob("matchypatchy.db.schema*.bak"))

    def test_rows_are_kept(self, migrated_db):
        db, _ = migrated_db
        assert db.select("media", columns="id, base_dir_id, relative_path, sha256, sequence_id, comment",
                         row_cond="id=1") == [(1, 1, "Site01/IMG_0001.JPG", "hash1", 1, "first")]
        assert db.count("media") == 3
        assert db.select("roi", columns="id, media_id, individual_id") == [(1, 1, 1), (2, 3, None)]
        assert db.select("individual", columns="id, name, sex") == [(1, "Jaguar-1", "Female")]
        assert db.select("media_thumbnails", columns="fid, filepath") == [(1, "media1.jpg")]
        assert db.select("roi_thumbnails", columns="fid, filepath") == [(1, "roi1.jpg")]

    def test_age_is_dropped(self, migrated_db):
        db, _ = migrated_db
        columns = [c[1] for c in db.db.execute("PRAGMA table_info(individual)").fetchall()]
        assert "age" not in columns

    def test_foreign_keys_still_cascade(self, migrated_db):
        db, _ = migrated_db
        assert db.db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        db.delete("media", "id=1")
        assert db.select("roi", columns="id") == [(2,)]
        assert db.count("media_thumbnails") == 0
        assert db.count("roi_thumbnails") == 0

    def test_detection_done_marks_media_with_a_boxed_roi(self, migrated_db):
        db, _ = migrated_db
        # 1 has a boxed roi, 2 has no rois, 3 only a roi imported without a box
        assert db.select("media", columns="id, detection_done") == [(1, 1), (2, 0), (3, 0)]

    def test_same_relative_path_under_another_base_dir_is_added(self, migrated_db):
        db, _ = migrated_db
        base_dir_id = db.add_upload("D:/2024")
        media_id = db.add_media(base_dir_id, "Site01/IMG_0001.JPG", "hash2", ".jpg",
                                "2024-01-01 00:00:00", 1)
        assert media_id not in ("duplicate_error", None)
        assert db.count("media") == 4


class TestInterruptedMigration:
    @pytest.mark.parametrize("schema_version", [None, 1], ids=["released", "unreleased-v1"])
    def test_reopens_after_crash_before_version_bump(self, tmp_path, null_logger, monkeypatch, schema_version):
        _old_database(tmp_path, schema_version=schema_version)
        migrate_1_to_2 = setup.MIGRATIONS[1]

        def crash_after_step(db):
            migrate_1_to_2(db)
            raise RuntimeError("process killed")

        # the step finishes but the process dies before its version bump is written
        monkeypatch.setitem(setup.MIGRATIONS, 1, crash_after_step)
        conn = sqlite3.connect(tmp_path / "matchypatchy.db")
        with pytest.raises(RuntimeError):
            setup.migrate_database(conn, tmp_path / "matchypatchy.db", null_logger)
        conn.close()
        monkeypatch.setitem(setup.MIGRATIONS, 1, migrate_1_to_2)

        db = MatchyPatchyDB(str(tmp_path), null_logger)
        try:
            assert db.key == KEY
            assert db.db.execute("SELECT schema_version FROM metadata").fetchone()[0] == SCHEMA_VERSION
            assert db.count("media") == 3
            assert db.select("roi", columns="id, media_id, individual_id") == [(1, 1, 1), (2, 3, None)]
        finally:
            db.close()


class TestRelativePathUniqueness:
    def test_same_relative_path_in_two_base_dirs(self, tmp_db):
        db, _ = tmp_db
        station_id = db.add_station("Site01", None, None, 1)
        dir_2023 = db.add_upload("D:/2023")
        dir_2024 = db.add_upload("D:/2024")

        first = db.add_media(dir_2023, "Site01/IMG_0001.JPG", "hash1", ".jpg", "2023-01-01", station_id)
        second = db.add_media(dir_2024, "Site01/IMG_0001.JPG", "hash2", ".jpg", "2024-01-01", station_id)

        assert first not in ("duplicate_error", None)
        assert second not in ("duplicate_error", None)
        assert first != second

    def test_same_relative_path_in_one_base_dir_is_a_duplicate(self, tmp_db):
        db, _ = tmp_db
        station_id = db.add_station("Site01", None, None, 1)
        base_dir_id = db.add_upload("D:/2023")

        db.add_media(base_dir_id, "Site01/IMG_0001.JPG", "hash1", ".jpg", "2023-01-01", station_id)
        again = db.add_media(base_dir_id, "Site01/IMG_0001.JPG", "hash2", ".jpg", "2023-01-01", station_id)

        assert again == "duplicate_error"
        assert db.count("media") == 1
