"""
Tests for matchypatchy.database.setup — database initialisation.
"""
import sqlite3

import chromadb
import pytest

from matchypatchy.database.setup import setup_database, setup_chromadb


EXPECTED_TABLES = {
    "metadata",
    "region",
    "survey",
    "station",
    "media",
    "roi",
    "individual",
    "sequence",
    "camera",
    "media_thumbnails",
    "roi_thumbnails",
}


# ---------------------------------------------------------------------------
# setup_database
# ---------------------------------------------------------------------------

class TestSetupDatabase:
    def test_creates_all_tables(self, tmp_path):
        db_file = tmp_path / "test.db"
        setup_database("TEST_KEY", db_file)

        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert EXPECTED_TABLES.issubset(tables)

    def test_metadata_row_inserted(self, tmp_path):
        db_file = tmp_path / "test.db"
        setup_database("MY_KEY", db_file)

        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT key FROM metadata WHERE id=1;")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "MY_KEY"

    def test_accepts_existing_connection(self, tmp_path):
        """setup_database should reuse a provided connection and not close it."""
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(db_file)
        returned = setup_database("KEY2", db_file, db=conn)
        # The provided connection should be returned unchanged
        assert returned is conn
        # And the connection should still be usable
        cursor = conn.cursor()
        cursor.execute("SELECT key FROM metadata;")
        assert cursor.fetchone() is not None
        conn.close()

    def test_foreign_keys_enabled_after_connect(self, tmp_path):
        db_file = tmp_path / "test.db"
        setup_database("FK_TEST", db_file)

        conn = sqlite3.connect(db_file)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        # Insert a region first, then a survey that references it
        cursor.execute("INSERT INTO region (name, timezone) VALUES ('R', 'UTC')")
        region_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO survey (name, region_id, year_start, year_end) VALUES (?, ?, ?, ?)",
            ("S", region_id, 2020, 2021),
        )
        conn.commit()

        # Deleting the region should set survey.region_id to NULL (ON DELETE SET NULL)
        cursor.execute(f"DELETE FROM region WHERE id={region_id}")
        conn.commit()
        cursor.execute("SELECT region_id FROM survey WHERE name='S';")
        assert cursor.fetchone()[0] is None
        conn.close()

    def test_station_cascade_delete(self, tmp_path):
        db_file = tmp_path / "test.db"
        setup_database("CAS_TEST", db_file)

        conn = sqlite3.connect(db_file)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        cursor.execute("INSERT INTO region (name) VALUES ('R')")
        region_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO survey (name, region_id) VALUES (?, ?)", ("S", region_id)
        )
        survey_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO station (name, survey_id) VALUES (?, ?)", ("ST", survey_id)
        )
        station_id = cursor.lastrowid
        conn.commit()

        # Deleting the survey should cascade to the station
        cursor.execute(f"DELETE FROM survey WHERE id={survey_id}")
        conn.commit()
        cursor.execute(f"SELECT id FROM station WHERE id={station_id};")
        assert cursor.fetchone() is None
        conn.close()


# ---------------------------------------------------------------------------
# setup_chromadb
# ---------------------------------------------------------------------------

class TestSetupChromadb:
    def test_creates_collection(self, tmp_path):
        chroma_dir = tmp_path / "emb.db"
        client = setup_chromadb("CKEY", chroma_dir)

        collection = client.get_collection("embedding_collection")
        assert collection is not None

    def test_collection_metadata_contains_key(self, tmp_path):
        chroma_dir = tmp_path / "emb.db"
        setup_chromadb("MKEY", chroma_dir)

        client = chromadb.PersistentClient(str(chroma_dir))
        collection = client.get_collection("embedding_collection")
        assert collection.metadata["key"] == "MKEY"

    def test_collection_uses_cosine_space(self, tmp_path):
        chroma_dir = tmp_path / "emb.db"
        setup_chromadb("CSPACE", chroma_dir)

        client = chromadb.PersistentClient(str(chroma_dir))
        collection = client.get_collection("embedding_collection")
        assert collection.metadata.get("hnsw:space") == "cosine"
