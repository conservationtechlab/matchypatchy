"""
Tests for matchypatchy.database.media — media/ROI helper functions.
"""
import hashlib
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from matchypatchy.database.media import (
    fetch_media,
    fetch_roi,
    fetch_roi_media,
    fetch_individual,
    get_sha256,
    get_roi_bbox,
    media_count,
)


# ---------------------------------------------------------------------------
# get_sha256
# ---------------------------------------------------------------------------

class TestGetSha256:
    def test_returns_hex_string(self, tmp_path):
        f = tmp_path / "sample.bin"
        f.write_bytes(b"hello world")
        result = get_sha256(f)
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 produces 64 hex chars

    def test_correct_hash(self, tmp_path):
        content = b"matchypatchy test"
        f = tmp_path / "hash.bin"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert get_sha256(f) == expected

    def test_nonexistent_file_returns_none(self, tmp_path):
        result = get_sha256(tmp_path / "does_not_exist.jpg")
        assert result is None

    def test_accepts_string_path(self, tmp_path):
        f = tmp_path / "str_path.bin"
        f.write_bytes(b"data")
        result = get_sha256(str(f))
        assert result is not None


# ---------------------------------------------------------------------------
# fetch_media
# ---------------------------------------------------------------------------

class TestFetchMedia:
    def test_returns_dataframe(self, populated_db):
        db, _, ids = populated_db
        df = fetch_media(db)
        assert isinstance(df, pd.DataFrame)

    def test_has_expected_columns(self, populated_db):
        db, _, ids = populated_db
        df = fetch_media(db)
        for col in ["id", "filepath", "sha256", "ext", "timestamp", "station_id"]:
            assert col in df.columns

    def test_returns_correct_row_count(self, populated_db):
        db, _, ids = populated_db
        df = fetch_media(db)
        assert len(df) == 1

    def test_empty_table_returns_empty_dataframe(self, tmp_db):
        db, _ = tmp_db
        df = fetch_media(db)
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_filter_by_ids(self, populated_db):
        db, _, ids = populated_db
        df = fetch_media(db, ids=[ids["media_id"]])
        assert len(df) == 1

    def test_filter_by_ids_nonexistent(self, populated_db):
        db, _, ids = populated_db
        df = fetch_media(db, ids=[99999])
        assert df.empty

    def test_filter_by_empty_ids_returns_nothing(self, populated_db):
        db, _, ids = populated_db
        df = fetch_media(db, ids=[])
        assert df.empty

    def test_counts_mode(self, populated_db):
        db, _, ids = populated_db
        df = fetch_media(db, counts=True)
        assert "roi_count" in df.columns
        assert df.loc[0, "roi_count"] == 1


# ---------------------------------------------------------------------------
# fetch_roi
# ---------------------------------------------------------------------------

class TestFetchRoi:
    def test_returns_dataframe(self, populated_db):
        db, _, ids = populated_db
        df = fetch_roi(db)
        assert isinstance(df, pd.DataFrame)

    def test_has_expected_columns(self, populated_db):
        db, _, ids = populated_db
        df = fetch_roi(db)
        for col in ["roi_id", "media_id", "bbox_x", "bbox_y", "bbox_w", "bbox_h"]:
            assert col in df.columns

    def test_filter_by_media_id(self, populated_db):
        db, _, ids = populated_db
        df = fetch_roi(db, media_id=ids["media_id"])
        assert len(df) == 1
        assert df.iloc[0]["media_id"] == ids["media_id"]

    def test_filter_by_wrong_media_id(self, populated_db):
        db, _, ids = populated_db
        df = fetch_roi(db, media_id=99999)
        assert df.empty

    def test_empty_table_returns_empty_dataframe(self, tmp_db):
        db, _ = tmp_db
        df = fetch_roi(db)
        assert isinstance(df, pd.DataFrame)
        assert df.empty


# ---------------------------------------------------------------------------
# fetch_roi_media
# ---------------------------------------------------------------------------

class TestFetchRoiMedia:
    def test_returns_dataframe(self, populated_db):
        db, _, ids = populated_db
        df = fetch_roi_media(db)
        assert isinstance(df, pd.DataFrame)

    def test_index_is_roi_id(self, populated_db):
        db, _, ids = populated_db
        df = fetch_roi_media(db)
        assert df.index.name == "id"
        assert ids["roi_id"] in df.index

    def test_filter_by_rids(self, populated_db):
        db, _, ids = populated_db
        df = fetch_roi_media(db, rids=[ids["roi_id"]])
        assert len(df) == 1

    def test_filter_by_empty_rids_returns_nothing(self, populated_db):
        db, _, ids = populated_db
        df = fetch_roi_media(db, rids=[])
        assert df.empty
        assert df.index.name == "id"

    def test_filter_by_empty_sequence_ids_returns_nothing(self, populated_db):
        db, _, ids = populated_db
        df = fetch_roi_media(db, sequence_ids=[])
        assert df.empty

    def test_no_reset_index(self, populated_db):
        db, _, ids = populated_db
        df = fetch_roi_media(db, reset_index=False)
        assert "id" in df.columns


# ---------------------------------------------------------------------------
# fetch_individual
# ---------------------------------------------------------------------------

class TestFetchIndividual:
    def test_returns_dataframe(self, populated_db):
        db, _, ids = populated_db
        df = fetch_individual(db)
        assert isinstance(df, pd.DataFrame)

    def test_index_is_id(self, populated_db):
        db, _, ids = populated_db
        df = fetch_individual(db)
        assert df.index.name == "id"
        assert ids["individual_id"] in df.index

    def test_empty_table_returns_empty_dataframe(self, tmp_db):
        db, _ = tmp_db
        df = fetch_individual(db)
        assert df.empty

    def test_has_name_sex_column(self, populated_db):
        db, _, ids = populated_db
        df = fetch_individual(db)
        for col in ["name", "sex"]:
            assert col in df.columns


# ---------------------------------------------------------------------------
# get_roi_bbox
# ---------------------------------------------------------------------------

class TestGetRoiBbox:
    def test_returns_bbox_when_present(self, populated_db):
        db, _, ids = populated_db
        df = fetch_roi(db)
        df = df.rename(columns={"roi_id": "id"}).set_index("id")
        bbox = get_roi_bbox(df)
        assert bbox is not None

    def test_returns_none_when_bbox_missing(self):
        df = pd.DataFrame({"other_col": [1]})
        result = get_roi_bbox(df)
        assert result is None


# ---------------------------------------------------------------------------
# media_count
# ---------------------------------------------------------------------------

class TestMediaCount:
    def test_returns_correct_count(self, populated_db):
        db, _, ids = populated_db
        _, count = media_count(db, ids["survey_id"])
        assert count == 1

    def test_returns_zero_for_empty_survey(self, tmp_db):
        db, _ = tmp_db
        # Default survey has no media
        result = media_count(db, 1)
        _, count = result
        assert count == 0


class TestEditsAndDeletes:
    def _roi(self, db, name="x.jpg"):
        station = db.add_station("S", None, None, 1)
        mid = db.add_media(db.add_upload(f"/{name}"), name, name, ".jpg", "2024-01-01 10:00:00", station)
        rid = db.add_roi(mid, 0, 0.1, 0.1, 0.1, 0.1)
        db.add_emb(rid, [0.1, 0.2, 0.3])
        return mid, rid

    def _has_emb(self, db, rid):
        return db.collection.get(ids=[str(rid)])["ids"] != []

    def test_delete_rois_removes_rows_and_embeddings(self, tmp_db):
        from matchypatchy.database.media import delete_rois
        db, _ = tmp_db
        _, a = self._roi(db, "a.jpg")
        _, b = self._roi(db, "b.jpg")
        assert delete_rois(db, [a]) is True
        assert db.select("roi", "id") == [(b,)]
        assert not self._has_emb(db, a)
        assert self._has_emb(db, b)

    def test_delete_media_removes_its_rois_and_embeddings(self, tmp_db):
        from matchypatchy.database.media import delete_media
        db, _ = tmp_db
        mid, rid = self._roi(db)
        assert delete_media(db, [mid]) is True
        assert db.count("media") == 0
        assert db.count("roi") == 0
        assert not self._has_emb(db, rid)

    def test_deleting_nothing_succeeds(self, tmp_db):
        from matchypatchy.database.media import delete_media, delete_rois
        db, _ = tmp_db
        assert delete_rois(db, []) is True
        assert delete_media(db, []) is True

    def test_update_roi_box_drops_the_embedding(self, tmp_db):
        from matchypatchy.database.media import update_roi_box
        db, _ = tmp_db
        _, rid = self._roi(db)
        db.edit_row("roi", rid, {"emb": 1, "favorite": 1})
        assert update_roi_box(db, rid, 2, 0.123456, 0.2, 0.3, 0.4) is True
        assert db.select("roi", "frame, bbox_x, bbox_w, emb, favorite", row_cond="id=?", params=(rid,)) == [(2, 0.1235, 0.3, 0, 1)]
        assert not self._has_emb(db, rid)

    def test_set_favorite(self, tmp_db):
        from matchypatchy.database.media import set_favorite
        db, _ = tmp_db
        _, rid = self._roi(db)
        assert set_favorite(db, rid, True) is True
        assert db.select("roi", "favorite", row_cond="id=?", params=(rid,)) == [(1,)]

    def test_clear_project_data_keeps_locations(self, tmp_db):
        from matchypatchy.database.media import clear_project_data
        db, _ = tmp_db
        _, rid = self._roi(db)
        db.add_individual("A")
        assert clear_project_data(db) is True
        assert [db.count(t) for t in ("media", "roi", "individual")] == [0, 0, 0]
        assert db.count("station") == 1
        assert not self._has_emb(db, rid)
