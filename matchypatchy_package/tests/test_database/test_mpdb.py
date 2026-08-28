"""
Tests for matchypatchy.database.mpdb — MatchyPatchyDB class and thread safety.
"""
import threading
import sqlite3

import numpy as np
import pytest

from matchypatchy.database.mpdb import MatchyPatchyDB


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestInitialisation:
    def test_creates_sqlite_file(self, tmp_db):
        db, path = tmp_db
        assert (path / "matchypatchy.db").is_file()

    def test_creates_chroma_directory(self, tmp_db):
        db, path = tmp_db
        assert (path / "emb.db").is_dir()

    def test_key_is_set(self, tmp_db):
        db, _ = tmp_db
        assert db.key is not None
        assert len(db.key) > 0

    def test_default_region_created(self, tmp_db):
        db, _ = tmp_db
        rows = db.select("region")
        assert len(rows) >= 1
        names = [r[1] for r in rows]
        assert "Default Region" in names

    def test_default_survey_created(self, tmp_db):
        db, _ = tmp_db
        rows = db.select("survey")
        assert len(rows) >= 1
        names = [r[1] for r in rows]
        assert "Default Survey" in names

    def test_reopen_existing_database(self, tmp_path, null_logger):
        """Opening the same directory a second time should reuse the existing DB."""
        db1 = MatchyPatchyDB(str(tmp_path), null_logger)
        original_key = db1.key
        db1.close()

        db2 = MatchyPatchyDB(str(tmp_path), null_logger)
        assert db2.key == original_key
        db2.close()


# ---------------------------------------------------------------------------
# Thread-local connections
# ---------------------------------------------------------------------------

class TestThreadLocalConnections:
    def test_main_thread_gets_connection(self, tmp_db):
        db, _ = tmp_db
        conn = db.db
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)

    def test_different_threads_get_different_connections(self, tmp_db):
        db, _ = tmp_db
        main_conn = db.db

        thread_conn_holder = []

        def get_conn():
            thread_conn_holder.append(db.db)
            db.close()  # close thread-local connection

        t = threading.Thread(target=get_conn)
        t.start()
        t.join()

        assert thread_conn_holder[0] is not main_conn

    def test_concurrent_reads(self, populated_db):
        """Multiple threads reading from the database should not raise."""
        db, _, ids = populated_db
        errors = []

        def read_media():
            try:
                rows = db.select("media")
                assert rows is not None
            except Exception as exc:
                errors.append(exc)
            finally:
                db.close()

        threads = [threading.Thread(target=read_media) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"

    def test_concurrent_writes(self, tmp_db):
        """Multiple threads writing unique records should all succeed."""
        db, _ = tmp_db
        survey_id = 1
        errors = []
        station_ids = []
        lock = threading.Lock()

        def add_station(idx):
            try:
                sid = db.add_station(f"Station-{idx}", float(idx), float(idx), survey_id)
                with lock:
                    station_ids.append(sid)
            except Exception as exc:
                errors.append(exc)
            finally:
                db.close()

        threads = [threading.Thread(target=add_station, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
        assert len(station_ids) == 10


# ---------------------------------------------------------------------------
# CRUD — region / survey / station / individual
# ---------------------------------------------------------------------------

class TestCRUD:
    def test_add_region(self, tmp_db):
        db, _ = tmp_db
        rid = db.add_region("Test Region", "UTC")
        assert isinstance(rid, int)
        rows = db.select("region", row_cond=f"id={rid}")
        assert len(rows) == 1
        assert rows[0][1] == "Test Region"
        assert rows[0][2] == "UTC"

    def test_add_region_none_timezone(self, tmp_db):
        """Passing timezone=None should default to the system timezone."""
        db, _ = tmp_db
        rid = db.add_region("NoTZ Region", None)
        assert isinstance(rid, int)
        row = db.select("region", row_cond=f"id={rid}")[0]
        assert row[2] is not None  # timezone was set automatically

    def test_add_survey(self, tmp_db):
        db, _ = tmp_db
        rid = db.add_region("Survey Region", "UTC")
        sid = db.add_survey("My Survey", rid, 2020, 2025)
        assert isinstance(sid, int)
        rows = db.select("survey", row_cond=f"id={sid}")
        assert len(rows) == 1
        assert rows[0][1] == "My Survey"

    def test_add_station(self, tmp_db):
        db, _ = tmp_db
        survey_id = 1
        st_id = db.add_station("Station Alpha", 10.5, -73.2, survey_id)
        assert isinstance(st_id, int)
        rows = db.select("station", row_cond=f"id={st_id}")
        assert len(rows) == 1
        assert rows[0][1] == "Station Alpha"
        assert rows[0][2] == pytest.approx(10.5)
        assert rows[0][3] == pytest.approx(-73.2)

    def test_add_individual(self, tmp_db):
        db, _ = tmp_db
        iid = db.add_individual("Lion-42", "F", "Juvenile")
        assert isinstance(iid, int)
        rows = db.select("individual", row_cond=f"id={iid}")
        assert len(rows) == 1
        name, sex, age = rows[0][1], rows[0][2], rows[0][3]
        assert name == "Lion-42"
        assert sex == "F"
        assert age == "Juvenile"

    def test_add_media(self, tmp_db):
        db, _ = tmp_db
        station_id = db.add_station("S", 0, 0, 1)
        upload_id = db.add_upload("/img")
        mid = db.add_media(upload_id, "test.jpg", "sha" * 20, ".jpg",
                           "2024-06-01 10:00:00", station_id)
        assert isinstance(mid, int)
        rows = db.select("media", row_cond=f"id={mid}")
        assert len(rows) == 1
        assert rows[0][2] == "test.jpg"

    def test_add_media_duplicate_filepath_returns_error(self, tmp_db):
        db, _ = tmp_db
        station_id = db.add_station("S2", 0, 0, 1)
        upload_id = db.add_upload("/img")
        sha1 = "aaa" * 22
        sha2 = "bbb" * 22
        db.add_media(upload_id, "dup.jpg", sha1, ".jpg", "2024-01-01", station_id)
        result = db.add_media(upload_id, "dup.jpg", sha2, ".jpg", "2024-01-02", station_id)
        assert result == "duplicate_error"

    def test_add_media_duplicate_sha256_returns_error(self, tmp_db):
        db, _ = tmp_db
        station_id = db.add_station("S3", 0, 0, 1)
        upload_id = db.add_upload("/img")
        sha = "ccc" * 22
        db.add_media(upload_id, "original.jpg", sha, ".jpg", "2024-01-01", station_id)
        result = db.add_media(upload_id, "copy.jpg", sha, ".jpg", "2024-01-01", station_id)
        assert result == "duplicate_error"

    def test_add_roi(self, tmp_db):
        db, _ = tmp_db
        station_id = db.add_station("S4", 0, 0, 1)
        upload_id = db.add_upload("/img")
        mid = db.add_media(upload_id, "roi.jpg", "ddd" * 22, ".jpg", "2024-01-01", station_id)
        rid = db.add_roi(mid, 0, 0.1, 0.2, 0.3, 0.4)
        assert isinstance(rid, int)
        rows = db.select("roi", row_cond=f"id={rid}")
        assert len(rows) == 1
        assert rows[0][1] == mid

    def test_add_roi_rounds_bbox(self, tmp_db):
        db, _ = tmp_db
        station_id = db.add_station("S5", 0, 0, 1)
        upload_id = db.add_upload("/img")
        mid = db.add_media(upload_id, "round.jpg", "eee" * 22, ".jpg", "2024-01-01", station_id)
        rid = db.add_roi(mid, 0, 0.123456789, 0.987654321, 0.5, 0.5)
        rows = db.select("roi", row_cond=f"id={rid}")
        assert rows[0][3] == pytest.approx(0.1235, abs=1e-4)

    def test_add_sequence(self, tmp_db):
        db, _ = tmp_db
        seq_id = db.add_sequence()
        assert isinstance(seq_id, int)

    def test_add_camera(self, tmp_db):
        db, _ = tmp_db
        station_id = db.add_station("CamStation", 0, 0, 1)
        cam_id = db.add_camera("Cam-01", station_id)
        assert isinstance(cam_id, int)
        rows = db.select("camera", row_cond=f"id={cam_id}")
        assert rows[0][1] == "Cam-01"

    def test_add_thumbnail(self, tmp_db):
        db, _ = tmp_db
        station_id = db.add_station("TmbStation", 0, 0, 1)
        upload_id = db.add_upload("/img")
        mid = db.add_media(upload_id, "thumb.jpg", "fff" * 22, ".jpg", "2024-01-01", station_id)
        tid = db.add_thumbnail("media", mid, "/thumbs/thumb_1.jpg")
        assert isinstance(tid, int)

    def test_add_thumbnail_duplicate_returns_error(self, tmp_db):
        db, _ = tmp_db
        station_id = db.add_station("TmbStation2", 0, 0, 1)
        upload_id = db.add_upload("/img")
        mid = db.add_media(upload_id, "thumb2.jpg", "ggg" * 22, ".jpg", "2024-01-01", station_id)
        db.add_thumbnail("media", mid, "/thumbs/t.jpg")
        result = db.add_thumbnail("media", mid, "/thumbs/t.jpg")
        assert result == "duplicate_error"


# ---------------------------------------------------------------------------
# Select / Edit / Delete / Count
# ---------------------------------------------------------------------------

class TestSelectEditDeleteCount:
    def test_select_all(self, populated_db):
        db, _, ids = populated_db
        rows = db.select("region")
        assert rows is not None
        assert len(rows) >= 1

    def test_select_with_row_cond(self, populated_db):
        db, _, ids = populated_db
        rows = db.select("region", row_cond=f"id={ids['region_id']}")
        assert len(rows) == 1

    def test_select_specific_columns(self, populated_db):
        db, _, ids = populated_db
        rows = db.select("region", columns="name")
        assert all(len(row) == 1 for row in rows)

    def test_count(self, populated_db):
        db, _, ids = populated_db
        assert db.count("media") == 1
        assert db.count("roi") == 1

    def test_edit_row(self, populated_db):
        db, _, ids = populated_db
        result = db.edit_row("individual", ids["individual_id"], {"sex": "F"})
        assert result is True
        row = db.select("individual", row_cond=f"id={ids['individual_id']}")[0]
        assert row[2] == "F"

    def test_edit_row_sets_null(self, populated_db):
        db, _, ids = populated_db
        result = db.edit_row("individual", ids["individual_id"], {"sex": None}, allow_none=True)
        assert result is True

    def test_edit_row_sets_null_not_allowed(self, populated_db):
        db, _, ids = populated_db
        result = db.edit_row("individual", ids["individual_id"], {"sex": None})
        assert result is False

    def test_delete(self, populated_db):
        db, _, ids = populated_db
        result = db.delete("individual", f"id={ids['individual_id']}")
        assert result is True
        rows = db.select("individual", row_cond=f"id={ids['individual_id']}")
        assert rows == []

    def test_clear(self, populated_db):
        db, _, ids = populated_db
        db.add_individual("ToBeCleared", None, None)
        result = db.clear("individual")
        assert result is True
        assert db.count("individual") == 0

    def test_command(self, populated_db):
        db, _, ids = populated_db
        rows = db._command("SELECT COUNT(*) FROM media;")
        assert rows is not None
        assert rows[0][0] == 1

    def test_select_join(self, populated_db):
        db, _, ids = populated_db
        rows, columns = db.select_join(
            "roi", "media", "roi.media_id = media.id",
            columns="roi.id, media.relative_path",
        )
        assert rows is not None
        assert len(rows) >= 1


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

class TestEmbeddings:
    def _make_embedding(self, dim=128):
        vec = np.random.rand(dim).tolist()
        return vec

    def test_add_and_retrieve_embedding(self, populated_db):
        db, _, ids = populated_db
        emb = self._make_embedding()
        db.add_emb(ids["roi_id"], emb)

        result = db.collection.get(
            ids=[str(ids["roi_id"])], include=["embeddings"]
        )
        assert len(result["embeddings"]) == 1
        assert len(result["embeddings"][0]) == 128

    def test_delete_embedding(self, populated_db):
        db, _, ids = populated_db
        emb = self._make_embedding()
        db.add_emb(ids["roi_id"], emb)
        db.delete_emb(ids["roi_id"])

        result = db.collection.get(ids=[str(ids["roi_id"])], include=["embeddings"])
        assert len(result["embeddings"]) == 0

    def test_knn_returns_empty_for_nonexistent_id(self, populated_db):
        db, _, ids = populated_db
        result = db.knn(query_id=99999)
        assert result["ids"] == [[]]
        assert result["distances"] == [[]]

    def test_knn_returns_neighbors(self, tmp_db):
        db, _ = tmp_db
        station_id = db.add_station("KnnStation", 0, 0, 1)
        upload_id = db.add_upload("/img")

        roi_ids = []
        for i in range(5):
            mid = db.add_media(
                upload_id, f"knn_{i}.jpg", f"knn_sha_{i}" * 5, ".jpg",
                "2024-01-01", station_id,
            )
            rid = db.add_roi(mid, 0, 0.1, 0.2, 0.3, 0.4)
            roi_ids.append(rid)

        dim = 64
        emb = np.random.rand(dim).tolist()
        for rid in roi_ids:
            db.add_emb(rid, emb)

        result = db.knn(query_id=roi_ids[0], k=3)
        assert len(result["ids"][0]) > 0

    def test_calculate_similarity(self, tmp_db):
        db, _ = tmp_db
        station_id = db.add_station("SimStation", 0, 0, 1)
        upload_id = db.add_upload("/img")
        mid1 = db.add_media(upload_id, "s1.jpg", "sim_sha_1" * 7, ".jpg", "2024-01-01", station_id)
        mid2 = db.add_media(upload_id, "s2.jpg", "sim_sha_2" * 7, ".jpg", "2024-01-01", station_id)
        rid1 = db.add_roi(mid1, 0, 0.1, 0.2, 0.3, 0.4)
        rid2 = db.add_roi(mid2, 0, 0.1, 0.2, 0.3, 0.4)

        vec = np.ones(32).tolist()
        db.add_emb(rid1, vec)
        db.add_emb(rid2, vec)

        similarity = db.calculate_similarity(rid1, rid2)
        assert similarity is not None
        assert abs(similarity - 1.0) < 1e-4  # identical vectors → cosine sim ≈ 1

    def test_clear_emb(self, populated_db):
        db, _, ids = populated_db
        db.add_emb(ids["roi_id"], np.random.rand(64).tolist())
        db.clear_emb()
        result = db.collection.get(ids=[str(ids["roi_id"])], include=["embeddings"])
        assert len(result["embeddings"]) == 0


# ---------------------------------------------------------------------------
# Foreign key constraints / cascade behaviour
# ---------------------------------------------------------------------------

class TestForeignKeyConstraints:
    def test_delete_media_cascades_to_roi(self, populated_db):
        db, _, ids = populated_db
        db.delete("media", f"id={ids['media_id']}")
        rows = db.select("roi", row_cond=f"media_id={ids['media_id']}")
        assert rows == []

    def test_delete_station_cascades_to_media(self, populated_db):
        db, _, ids = populated_db
        db.delete("station", f"id={ids['station_id']}")
        rows = db.select("media", row_cond=f"station_id={ids['station_id']}")
        assert rows == []

    def test_delete_survey_cascades_to_station(self, populated_db):
        db, _, ids = populated_db
        db.delete("survey", f"id={ids['survey_id']}")
        rows = db.select("station", row_cond=f"survey_id={ids['survey_id']}")
        assert rows == []


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

class TestExportHelpers:
    def test_all_media_returns_rows(self, populated_db):
        db, _, ids = populated_db
        rows, columns = db.all_media()
        assert rows is not None
        assert len(rows) >= 1
        assert "filepath" in columns or "id" in columns

    def test_all_media_with_row_cond(self, populated_db):
        db, _, ids = populated_db
        rows, _ = db.all_media(row_cond=f"roi.id={ids['roi_id']}")
        assert len(rows) == 1

    def test_export_data(self, populated_db):
        db, _, ids = populated_db
        df = db.export_data()
        assert df is not None
        assert not df.empty

    def test_retrieve_key(self, tmp_db):
        db, _ = tmp_db
        version, mpkey, chromakey = db.retrieve_key()
        assert mpkey == chromakey
        assert mpkey == db.key

    def test_stations_join(self, populated_db):
        db, _, ids = populated_db
        rows, columns = db.stations()
        assert rows is not None
        assert len(rows) >= 1
