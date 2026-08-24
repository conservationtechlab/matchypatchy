"""
Tests for matchypatchy.database.location — region, survey, and station helpers.
"""
import pandas as pd
import pytest

from matchypatchy.database.location import (
    fetch_surveys,
    fetch_regions,
    fetch_stations,
    fetch_station_names_from_id,
)


# ---------------------------------------------------------------------------
# fetch_regions
# ---------------------------------------------------------------------------

class TestFetchRegions:
    def test_returns_dataframe(self, tmp_db):
        db, _ = tmp_db
        df = fetch_regions(db)
        assert isinstance(df, pd.DataFrame)

    def test_has_id_and_name_columns(self, tmp_db):
        db, _ = tmp_db
        df = fetch_regions(db)
        assert "id" in df.columns
        assert "name" in df.columns
        assert "timezone" in df.columns

    def test_default_region_present(self, tmp_db):
        db, _ = tmp_db
        df = fetch_regions(db)
        assert "Default Region" in df["name"].values

    def test_added_region_appears(self, tmp_db):
        db, _ = tmp_db
        db.add_region("Amazon Basin", "America/Manaus")
        df = fetch_regions(db)
        assert "Amazon Basin" in df["name"].values

    def test_empty_after_clear(self, tmp_db):
        db, _ = tmp_db
        db.clear("region")
        df = fetch_regions(db)
        assert df.empty


# ---------------------------------------------------------------------------
# fetch_surveys
# ---------------------------------------------------------------------------

class TestFetchSurveys:
    def test_returns_dataframe(self, tmp_db):
        db, _ = tmp_db
        df = fetch_surveys(db)
        assert isinstance(df, pd.DataFrame)

    def test_has_expected_columns(self, tmp_db):
        db, _ = tmp_db
        df = fetch_surveys(db)
        for col in ["id", "name", "region", "year_start", "year_end"]:
            assert col in df.columns

    def test_default_survey_present(self, tmp_db):
        db, _ = tmp_db
        df = fetch_surveys(db)
        assert "Default Survey" in df["name"].values

    def test_added_survey_appears(self, tmp_db):
        db, _ = tmp_db
        rid = db.add_region("New Region", "UTC")
        db.add_survey("Winter Survey", rid, 2023, 2024)
        df = fetch_surveys(db)
        assert "Winter Survey" in df["name"].values

    def test_empty_after_clear(self, tmp_db):
        db, _ = tmp_db
        db.clear("survey")
        df = fetch_surveys(db)
        assert df.empty


# ---------------------------------------------------------------------------
# fetch_stations
# ---------------------------------------------------------------------------

class TestFetchStations:
    def test_returns_dataframe(self, populated_db):
        db, _, ids = populated_db
        df = fetch_stations(db)
        assert isinstance(df, pd.DataFrame)

    def test_has_expected_columns(self, populated_db):
        db, _, ids = populated_db
        df = fetch_stations(db)
        for col in ["id", "name", "lat", "long", "survey_id"]:
            assert col in df.columns

    def test_filter_by_survey_id(self, populated_db):
        db, _, ids = populated_db
        df = fetch_stations(db, survey_id=ids["survey_id"])
        assert len(df) >= 1
        assert all(df["survey_id"] == ids["survey_id"])

    def test_filter_by_nonexistent_survey_returns_empty(self, populated_db):
        db, _, ids = populated_db
        df = fetch_stations(db, survey_id=99999)
        assert df.empty

    def test_empty_when_no_stations(self, tmp_db):
        db, _ = tmp_db
        df = fetch_stations(db)
        assert df.empty

    def test_station_coordinates_stored_correctly(self, tmp_db):
        db, _ = tmp_db
        db.add_station("Precise Station", 12.3456, -98.7654, 1)
        df = fetch_stations(db)
        row = df[df["name"] == "Precise Station"].iloc[0]
        assert row["lat"] == pytest.approx(12.3456, abs=1e-4)
        assert row["long"] == pytest.approx(-98.7654, abs=1e-4)


# ---------------------------------------------------------------------------
# fetch_station_names_from_id
# ---------------------------------------------------------------------------

class TestFetchStationNamesFromId:
    def test_returns_expected_keys(self, populated_db):
        db, _, ids = populated_db
        result = fetch_station_names_from_id(db, ids["station_id"])
        for key in ["station_name", "suvery_id", "survey_name", "region_id", "region_name"]:
            assert key in result

    def test_station_name_correct(self, populated_db):
        db, _, ids = populated_db
        result = fetch_station_names_from_id(db, ids["station_id"])
        assert result["station_name"] == "Test Station"

    def test_survey_name_correct(self, populated_db):
        db, _, ids = populated_db
        result = fetch_station_names_from_id(db, ids["station_id"])
        assert result["survey_name"] == "Default Survey"

    def test_region_name_correct(self, populated_db):
        db, _, ids = populated_db
        result = fetch_station_names_from_id(db, ids["station_id"])
        assert result["region_name"] == "Default Region"


# ---------------------------------------------------------------------------
# Cascade delete behaviour
# ---------------------------------------------------------------------------

class TestCascadeDeletes:
    def test_delete_region_sets_survey_region_id_null(self, tmp_db):
        """
        Deleting a region should set survey.region_id to NULL
        (ON DELETE SET NULL), not remove the survey.
        """
        db, _ = tmp_db
        rid = db.add_region("To Delete", "UTC")
        sid = db.add_survey("Orphan Survey", rid, 2020, 2021)
        db.delete("region", f"id={rid}")

        rows = db.select("survey", row_cond=f"id={sid}")
        assert len(rows) == 1
        # region_id column (index 2) should be NULL
        assert rows[0][2] is None

    def test_delete_survey_cascades_to_station(self, tmp_db):
        db, _ = tmp_db
        sid = db.add_survey("CascadeSurvey", 1, 2022, 2023)
        st_id = db.add_station("CascadeStation", 0.0, 0.0, sid)
        db.delete("survey", f"id={sid}")

        rows = db.select("station", row_cond=f"id={st_id}")
        assert rows == []

    def test_delete_station_cascades_to_media_and_roi(self, tmp_db):
        db, _ = tmp_db
        st_id = db.add_station("MediaStation", 0.0, 0.0, 1)
        upload_id = db.add_upload("/img")
        mid = db.add_media(upload_id, "cascade.jpg", "cascade_sha" * 6, ".jpg",
                           "2024-01-01", st_id)
        rid = db.add_roi(mid, 0, 0.1, 0.2, 0.3, 0.4)

        db.delete("station", f"id={st_id}")

        assert db.select("media", row_cond=f"id={mid}") == []
        assert db.select("roi", row_cond=f"id={rid}") == []

    def test_delete_individual_sets_roi_individual_id_null(self, tmp_db):
        db, _ = tmp_db
        st_id = db.add_station("IndStation", 0.0, 0.0, 1)
        iid = db.add_individual("Wolf-7", "M", None)
        upload_id = db.add_upload("/img")
        mid = db.add_media(upload_id, "ind.jpg", "ind_sha" * 8, ".jpg",
                           "2024-01-01", st_id)
        rid = db.add_roi(mid, 0, 0.1, 0.2, 0.3, 0.4, individual_id=iid)

        db.delete("individual", f"id={iid}")

        rows = db.select("roi", row_cond=f"id={rid}")
        # individual_id (index 10) should be NULL after ON DELETE SET NULL
        assert rows[0][10] is None
