"""Deleting rows that cascade to rois also deletes the rois' embeddings from chroma."""
import pytest

from matchypatchy.database.mpdb import MatchyPatchyDB


def _embedded_ids(db):
    return sorted(int(i) for i in db.collection.get(include=[])["ids"])


@pytest.fixture
def two_surveys(tmp_db):
    """
    Two surveys, each with a station, an upload, one image and two embedded rois

    Returns the db and {survey: {"survey", "station", "upload", "media", "rois"}}
    """
    db, _ = tmp_db
    ids = {}
    for n, year in enumerate(("2023", "2024")):
        survey_id = db.add_survey(f"Survey {year}", None, None, None)
        station_id = db.add_station("Site01", None, None, survey_id)
        upload_id = db.add_upload(f"D:/{year}")
        media_id = db.add_media(upload_id, f"{year}.jpg", f"hash{year}", ".jpg", f"{year}-01-01", station_id)
        rois = [db.add_roi(media_id, 0, 0.1, 0.1, 0.2, 0.2, emb=1) for _ in range(2)]
        for roi_id in rois:
            db.add_emb(roi_id, [float(n), float(roi_id), 1.0])
        ids[year] = {"survey": survey_id, "station": station_id, "upload": upload_id,
                     "media": media_id, "rois": rois}
    return db, ids


@pytest.mark.parametrize("table", ["survey", "station", "upload", "media"])
def test_cascading_delete_removes_embeddings(two_surveys, table):
    db, ids = two_surveys
    sql_table = "uploads" if table == "upload" else table

    assert db.delete(sql_table, f"id={ids['2023'][table]}")

    assert db.count("roi") == 2
    assert _embedded_ids(db) == sorted(ids["2024"]["rois"])


def test_deleting_a_roi_removes_its_embedding(two_surveys):
    db, ids = two_surveys
    gone, kept = ids["2023"]["rois"]

    assert db.delete("roi", f"id={gone}")

    assert gone not in _embedded_ids(db)
    assert kept in _embedded_ids(db)


def test_rois_without_an_embedding_are_fine(two_surveys):
    db, ids = two_surveys
    # a roi that was never processed
    db.add_roi(ids["2023"]["media"], 0, 0.5, 0.5, 0.1, 0.1)

    assert db.delete("survey", f"id={ids['2023']['survey']}")

    assert _embedded_ids(db) == sorted(ids["2024"]["rois"])


def test_failed_delete_keeps_embeddings(two_surveys):
    db, ids = two_surveys
    before = _embedded_ids(db)

    assert db.delete("survey", "no_such_column=1") is False

    assert _embedded_ids(db) == before


def test_delete_from_other_tables_leaves_embeddings(two_surveys):
    db, _ = two_surveys
    before = _embedded_ids(db)
    individual_id = db.add_individual("Jaguar-1")

    assert db.delete("individual", f"id={individual_id}")

    assert _embedded_ids(db) == before


def test_orphaned_embeddings_are_pruned_on_open(tmp_path, null_logger):
    db = MatchyPatchyDB(str(tmp_path))
    station_id = db.add_station("Site01", None, None, 1)
    upload_id = db.add_upload("D:/2023")
    media_id = db.add_media(upload_id, "a.jpg", "hash", ".jpg", "2023-01-01", station_id)
    roi_id = db.add_roi(media_id, 0, 0.1, 0.1, 0.2, 0.2, emb=1)
    db.add_emb(roi_id, [1.0, 0.0, 0.0])
    # left behind by a station delete before embeddings were cleaned up with their rois
    db.add_emb(999, [0.0, 1.0, 0.0])
    db.close()

    db = MatchyPatchyDB(str(tmp_path))

    assert db.key
    assert _embedded_ids(db) == [roi_id]
    db.close()
