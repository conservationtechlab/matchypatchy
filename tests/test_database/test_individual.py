"""Tests for matchypatchy.database.individual"""
from matchypatchy.database import individual


def _roi(db, individual_id=None):
    station = db.add_station("S", None, None, 1)
    mid = db.add_media(db.add_upload(f"/u{individual_id}"), "x.jpg", f"h{individual_id}", ".jpg", "2024", station)
    return db.add_roi(mid, 0, 0.1, 0.1, 0.1, 0.1, individual_id=individual_id)


class TestIndividuals:
    def test_names(self, tmp_db):
        db, _ = tmp_db
        a = db.add_individual("O'Malley")
        assert individual.individual_names(db) == [(a, "O'Malley")]

    def test_roi_counts_include_individuals_without_rois(self, tmp_db):
        db, _ = tmp_db
        a, b = db.add_individual("A"), db.add_individual("B")
        _roi(db, a)
        _roi(db, None)
        assert sorted(individual.individual_roi_counts(db)) == [(a, "A", 1), (b, "B", 0)]
        assert individual.unidentified_roi_count(db) == 1

    def test_unidentified_count_empty_database(self, tmp_db):
        db, _ = tmp_db
        assert individual.unidentified_roi_count(db) == 0

    def test_get_and_update(self, tmp_db):
        db, _ = tmp_db
        a = db.add_individual("A", "Male")
        assert individual.get_individual(db, a) == ("A", "Male")
        assert individual.update_individual(db, a, "B", None) is True
        assert individual.get_individual(db, a) == ("B", None)
        assert individual.get_individual(db, 999) is None

    def test_name_exists(self, tmp_db):
        db, _ = tmp_db
        db.add_individual("O'Malley")
        assert individual.individual_name_exists(db, "O'Malley") is True
        assert individual.individual_name_exists(db, "Other") is False
