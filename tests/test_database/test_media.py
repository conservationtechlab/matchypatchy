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


class TestSaveEdits:
    def _edit(self, rid, mid, reference, new_value):
        from matchypatchy.database.media import EditObject
        return EditObject(rid=rid, mid=mid, reference=reference, previous_value=None, new_value=new_value)

    def test_sex_follows_a_name_change_in_the_same_save(self, tmp_db):
        from matchypatchy.database.media import save_edits
        db, _ = tmp_db
        station = db.add_station("S", None, None, 1)
        mid = db.add_media(db.add_upload("/a"), "x.jpg", "h", ".jpg", "2024-01-01 10:00:00", station)
        old, new = db.add_individual("Old", "Male"), db.add_individual("New")
        rid = db.add_roi(mid, 0, 0.1, 0.1, 0.1, 0.1, individual_id=old)
        failed = save_edits(db, [self._edit(rid, mid, "individual_id", new), self._edit(rid, mid, "sex", "Female"),
                                 self._edit(rid, mid, "comment", "O'Neil saw it")],
                            individual_of=lambda r: old)
        assert failed == []
        assert db.select("individual", "id, sex") == [(old, "Male"), (new, "Female")]
        assert db.select("media", "comment") == [("O'Neil saw it",)]

    def test_name_change_sets_reviewed(self, tmp_db):
        from matchypatchy.database.media import save_edits
        db, _ = tmp_db
        station = db.add_station("S", None, None, 1)
        mid = db.add_media(db.add_upload("/a"), "x.jpg", "h", ".jpg", "2024-01-01 10:00:00", station)
        iid = db.add_individual("New")
        named, unknown = db.add_roi(mid, 0, 0.1, 0.1, 0.1, 0.1), db.add_roi(mid, 0, 0.2, 0.1, 0.1, 0.1, individual_id=iid, reviewed=1)
        failed = save_edits(db, [self._edit(named, mid, "individual_id", iid), self._edit(unknown, mid, "individual_id", None)],
                            individual_of=lambda r: None)
        assert failed == []
        assert db.select("roi", "id, individual_id, reviewed") == [(named, iid, 1), (unknown, None, 0)]

    def test_failed_edit_is_returned(self, tmp_db):
        from matchypatchy.database.media import save_edits
        db, _ = tmp_db
        bad_column = self._edit(1, 1, "not_a_column", 1)
        assert save_edits(db, [bad_column], individual_of=lambda r: None) == [bad_column]


class TestMatchingAndLookups:
    def _media(self, db, name, rois=1):
        station = db.add_station("S", None, None, 1)
        mid = db.add_media(db.add_upload(f"/{name}"), name, name, ".jpg", "2024-01-01 10:00:00", station)
        return mid, [db.add_roi(mid, 0, 0.1 * (i + 1), 0.1, 0.1, 0.1) for i in range(rois)]

    def test_assign_and_clear_individual(self, tmp_db):
        from matchypatchy.database.media import assign_individual, clear_individual
        db, _ = tmp_db
        _, (a, b) = self._media(db, "x.jpg", rois=2)
        iid = db.add_individual("A")
        assert assign_individual(db, [a, b], iid) is True
        assert db.select("roi", "individual_id, reviewed") == [(iid, 1), (iid, 1)]
        assert clear_individual(db, [a]) is True
        assert db.select("roi", "id, individual_id, reviewed") == [(a, None, 0), (b, iid, 1)]

    def test_media_without_rois(self, tmp_db):
        from matchypatchy.database.media import media_without_rois
        db, _ = tmp_db
        self._media(db, "with.jpg", rois=1)
        empty, _ = self._media(db, "empty.jpg", rois=0)
        assert media_without_rois(db) == [empty]

    def test_uploads_with_media_counts(self, tmp_db):
        from matchypatchy.database.media import uploads_with_media_counts
        db, _ = tmp_db
        self._media(db, "x.jpg")
        unused = db.add_upload("/unused")
        counts = {base_dir: n for _, base_dir, _, n in uploads_with_media_counts(db)}
        assert counts == {"/x.jpg": 1, "/unused": 0}
        assert unused in [row[0] for row in uploads_with_media_counts(db)]


class TestFilepathSeparators:
    """relative_path keeps the importing OS's separators, filepaths use the current OS's"""

    @pytest.mark.parametrize("base_dir", ["H:\\Images", "H:/Images"])
    @pytest.mark.parametrize("relative_path", ["7\\a.jpg", "7/a.jpg"])
    def test_filepath_uses_current_separator(self, tmp_db, base_dir, relative_path):
        import os
        db, _ = tmp_db
        station = db.add_station("S", None, None, 1)
        mid = db.add_media(db.add_upload(base_dir), relative_path, "h", ".jpg", "2024-01-01 10:00:00", station)
        db.add_roi(mid, 0, 0.1, 0.1, 0.1, 0.1)
        expected = os.sep.join(["H:", "Images", "7", "a.jpg"])
        assert fetch_media(db).loc[0, "filepath"] == expected
        assert fetch_media(db, counts=True).loc[0, "filepath"] == expected
        assert fetch_roi(db).loc[0, "filepath"] == expected
        assert db.get_full_path(mid) == expected
        rows, columns = db.all_media()
        assert rows[0][columns.index("filepath")] == expected

    @pytest.mark.parametrize("relative_path", ["7\\a.jpg", "7/a.jpg"])
    def test_native_relative_path(self, relative_path):
        import os
        from matchypatchy.database.media import native_relative_path
        assert native_relative_path(relative_path) == os.sep.join(["7", "a.jpg"])
