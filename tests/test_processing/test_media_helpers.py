"""
Tests for matchypatchy.database.media — ROI/media helper functions.

These tests cover pure-Python logic that does not require a display server
or any Qt widgets.  All database interactions use the tmp_db / populated_db
fixtures from conftest.py.
"""
import hashlib
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from matchypatchy.database.media import (
    COLUMNS,
    IMAGE_EXT,
    VIDEO_EXT,
    EditObject,
    fetch_individual,
    fetch_media,
    fetch_roi,
    get_roi_bbox,
    get_sequence,
    get_sha256,
    individual_roi_dict,
    media_count,
    sequence_roi_dict,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_image_ext_contains_jpg(self):
        assert ".jpg" in IMAGE_EXT
        assert ".jpeg" in IMAGE_EXT
        assert ".png" in IMAGE_EXT

    def test_video_ext_contains_mp4(self):
        assert ".mp4" in VIDEO_EXT
        assert ".avi" in VIDEO_EXT

    def test_extensions_are_lowercase(self):
        for ext in IMAGE_EXT + VIDEO_EXT:
            assert ext == ext.lower(), f"Extension {ext!r} should be lowercase"

    def test_columns_is_list_of_strings(self):
        assert isinstance(COLUMNS, list)
        assert all(isinstance(c, str) for c in COLUMNS)

    def test_columns_contains_expected_fields(self):
        for field in ("id", "frame", "bbox_x", "bbox_y", "bbox_w", "bbox_h",
                      "reviewed", "favorite", "individual_id"):
            assert field in COLUMNS, f"Expected column {field!r} in COLUMNS"


# ---------------------------------------------------------------------------
# EditObject dataclass
# ---------------------------------------------------------------------------

class TestEditObject:
    def test_creation(self):
        obj = EditObject(rid=1, mid=2, reference="name", previous_value="old", new_value="new")
        assert obj.rid == 1
        assert obj.mid == 2
        assert obj.reference == "name"
        assert obj.previous_value == "old"
        assert obj.new_value == "new"

    def test_fields_accessible(self):
        obj = EditObject(rid=10, mid=20, reference="sex", previous_value=None, new_value="F")
        assert obj.rid == 10
        assert obj.new_value == "F"

    def test_supports_none_values(self):
        obj = EditObject(rid=0, mid=0, reference="age", previous_value=None, new_value=None)
        assert obj.previous_value is None
        assert obj.new_value is None


# ---------------------------------------------------------------------------
# get_sha256
# ---------------------------------------------------------------------------

class TestGetSha256:
    def test_returns_hex_string_for_valid_file(self, tmp_path):
        f = tmp_path / "sample.bin"
        f.write_bytes(b"hello world")
        result = get_sha256(f)
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert result == expected

    def test_returns_none_for_missing_file(self, tmp_path):
        result = get_sha256(tmp_path / "nonexistent.jpg")
        assert result is None

    def test_different_files_yield_different_hashes(self, tmp_path):
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(b"content_a")
        f2.write_bytes(b"content_b")
        assert get_sha256(f1) != get_sha256(f2)

    def test_same_content_yields_same_hash(self, tmp_path):
        f1 = tmp_path / "x.bin"
        f2 = tmp_path / "y.bin"
        f1.write_bytes(b"identical")
        f2.write_bytes(b"identical")
        assert get_sha256(f1) == get_sha256(f2)

    def test_accepts_path_object(self, tmp_path):
        f = tmp_path / "p.bin"
        f.write_bytes(b"path object test")
        result = get_sha256(Path(f))
        assert isinstance(result, str)

    def test_accepts_string_path(self, tmp_path):
        f = tmp_path / "s.bin"
        f.write_bytes(b"string path test")
        result = get_sha256(str(f))
        assert isinstance(result, str)

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.bin"
        f.write_bytes(b"")
        result = get_sha256(f)
        assert result == hashlib.sha256(b"").hexdigest()


# ---------------------------------------------------------------------------
# fetch_media
# ---------------------------------------------------------------------------

class TestFetchMedia:
    def test_returns_dataframe(self, populated_db):
        db, _, ids = populated_db
        result = fetch_media(db)
        assert isinstance(result, pd.DataFrame)

    def test_dataframe_has_expected_columns(self, populated_db):
        db, _, ids = populated_db
        result = fetch_media(db)
        for col in ("id", "ext", "timestamp", "station_id"):
            assert col in result.columns

    def test_returns_correct_row_count(self, populated_db):
        db, _, ids = populated_db
        result = fetch_media(db)
        assert len(result) == 1

    def test_filter_by_ids(self, populated_db):
        db, _, ids = populated_db
        result = fetch_media(db, ids=[ids["media_id"]])
        assert len(result) == 1
        assert ids["media_id"] in result["id"].values

    def test_filter_by_nonexistent_id_returns_empty(self, populated_db):
        db, _, ids = populated_db
        result = fetch_media(db, ids=[99999])
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_empty_db_returns_empty_dataframe(self, tmp_db):
        db, _ = tmp_db
        result = fetch_media(db)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_filepath_column_present(self, populated_db):
        db, _, ids = populated_db
        result = fetch_media(db)
        assert "filepath" in result.columns


# ---------------------------------------------------------------------------
# fetch_roi
# ---------------------------------------------------------------------------

class TestFetchRoi:
    def test_returns_dataframe(self, populated_db):
        db, _, ids = populated_db
        result = fetch_roi(db)
        assert isinstance(result, pd.DataFrame)

    def test_has_bbox_columns(self, populated_db):
        db, _, ids = populated_db
        result = fetch_roi(db)
        for col in ("bbox_x", "bbox_y", "bbox_w", "bbox_h"):
            assert col in result.columns

    def test_returns_one_row(self, populated_db):
        db, _, ids = populated_db
        result = fetch_roi(db)
        assert len(result) == 1

    def test_filter_by_media_id(self, populated_db):
        db, _, ids = populated_db
        result = fetch_roi(db, media_id=ids["media_id"])
        assert len(result) == 1

    def test_filter_by_nonexistent_media_id_returns_empty(self, populated_db):
        db, _, ids = populated_db
        result = fetch_roi(db, media_id=99999)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_empty_db_returns_empty_dataframe(self, tmp_db):
        db, _ = tmp_db
        result = fetch_roi(db)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# fetch_individual
# ---------------------------------------------------------------------------

class TestFetchIndividual:
    def test_returns_dataframe(self, populated_db):
        db, _, ids = populated_db
        result = fetch_individual(db)
        assert isinstance(result, pd.DataFrame)

    def test_has_expected_columns(self, populated_db):
        db, _, ids = populated_db
        result = fetch_individual(db)
        for col in ("name", "sex", "age"):
            assert col in result.columns

    def test_returns_one_individual(self, populated_db):
        db, _, ids = populated_db
        result = fetch_individual(db)
        assert len(result) == 1

    def test_individual_name_correct(self, populated_db):
        db, _, ids = populated_db
        result = fetch_individual(db)
        assert "Ind-1" in result["name"].values

    def test_empty_db_returns_empty_dataframe(self, tmp_db):
        db, _ = tmp_db
        result = fetch_individual(db)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# get_roi_bbox
# ---------------------------------------------------------------------------

class TestGetRoiBbox:
    def _make_roi(self, bbox_x=0.1, bbox_y=0.2, bbox_w=0.3, bbox_h=0.4):
        return pd.DataFrame([{
            "id": 1, "bbox_x": bbox_x, "bbox_y": bbox_y,
            "bbox_w": bbox_w, "bbox_h": bbox_h, "reviewed": 0,
        }])

    def test_returns_bbox_when_all_present(self):
        roi = self._make_roi()
        result = get_roi_bbox(roi)
        assert result is not None

    def test_returns_none_when_bbox_missing(self):
        roi = pd.DataFrame([{"id": 1, "reviewed": 0}])
        result = get_roi_bbox(roi)
        assert result is None

    def test_returns_none_when_bbox_has_nan(self):
        roi = pd.DataFrame([{
            "id": 1, "bbox_x": None, "bbox_y": 0.2,
            "bbox_w": 0.3, "bbox_h": 0.4,
        }])
        result = get_roi_bbox(roi)
        assert result is None

    def test_bbox_values_correct(self):
        roi = self._make_roi(0.1, 0.2, 0.3, 0.4)
        result = get_roi_bbox(roi)
        assert float(result["bbox_x"].iloc[0]) == pytest.approx(0.1)
        assert float(result["bbox_y"].iloc[0]) == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# media_count
# ---------------------------------------------------------------------------

class TestMediaCount:
    def test_returns_zero_for_empty_survey(self, tmp_db):
        db, _ = tmp_db
        media, count = media_count(db, survey_id=1)
        assert count == 0

    def test_returns_correct_count_after_add(self, populated_db):
        db, _, ids = populated_db
        media, count = media_count(db, survey_id=ids["survey_id"])
        assert count == 1

    def test_returns_empty_for_nonexistent_survey(self, tmp_db):
        db, _ = tmp_db
        media, count = media_count(db, survey_id=99999)
        assert count == 0


# ---------------------------------------------------------------------------
# get_sequence / sequence_roi_dict / individual_roi_dict
# ---------------------------------------------------------------------------

class TestSequenceHelpers:
    def _build_roi_media(self, seq_id=1, ind_id=1):
        """Helper to create a minimal roi_media DataFrame."""
        return pd.DataFrame([
            {"id": 10, "sequence_id": seq_id, "individual_id": ind_id, "timestamp": "2024-01-01 10:00:00"},
            {"id": 11, "sequence_id": seq_id, "individual_id": ind_id, "timestamp": "2024-01-01 10:00:01"},
            {"id": 12, "sequence_id": 2,      "individual_id": 2,      "timestamp": "2024-01-01 11:00:00"},
        ]).set_index("id")

    def test_get_sequence_returns_list(self):
        roi_media = self._build_roi_media()
        result = get_sequence(10, roi_media)
        assert isinstance(result, list)

    def test_get_sequence_returns_correct_ids(self):
        roi_media = self._build_roi_media()
        result = get_sequence(10, roi_media)
        assert 10 in result
        assert 11 in result
        assert 12 not in result

    def test_sequence_roi_dict_keys_are_sequence_ids(self):
        roi_media = self._build_roi_media()
        d = sequence_roi_dict(roi_media)
        assert isinstance(d, dict)
        assert 1 in d
        assert 2 in d

    def test_sequence_roi_dict_values_contain_correct_ids(self):
        roi_media = self._build_roi_media()
        d = sequence_roi_dict(roi_media)
        assert 10 in d[1]
        assert 11 in d[1]
        assert 12 in d[2]

    def test_individual_roi_dict_keys_are_individual_ids(self):
        roi_media = self._build_roi_media()
        d = individual_roi_dict(roi_media)
        assert isinstance(d, dict)
        assert 1 in d
        assert 2 in d

    def test_individual_roi_dict_values_contain_correct_ids(self):
        roi_media = self._build_roi_media()
        d = individual_roi_dict(roi_media)
        assert 10 in d[1]
        assert 11 in d[1]
        assert 12 in d[2]
