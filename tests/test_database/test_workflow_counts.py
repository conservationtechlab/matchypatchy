"""
Tests for matchypatchy.database.media.workflow_counts, which feeds the overview page
"""
from matchypatchy.database.media import WorkflowCounts, workflow_counts


def _add_media(db, upload_id, station_id, name):
    return db.add_media(base_dir_id=upload_id, relative_path=name, sha256=name * 8, ext=".jpg",
                        timestamp="2024-01-01 12:00:00", station_id=station_id)


class TestWorkflowCounts:
    def test_populated_survey(self, populated_db):
        db, _, ids = populated_db
        counts = workflow_counts(db, ids["survey_id"])
        assert counts.stations == 1
        assert counts.media == 1
        assert counts.rois == 1
        # not through detection or re-id yet, no viewpoint, but identified
        assert counts.undetected == 1
        assert counts.unembedded == 1
        assert counts.missing_viewpoint == 1
        assert counts.unidentified == 0
        assert counts.individuals == 1

    def test_counts_each_state(self, populated_db):
        db, _, ids = populated_db
        upload_id = db.add_upload("/other")
        done = _add_media(db, upload_id, ids["station_id"], "a.jpg")
        db.mark_detection_done([done, ids["media_id"]])
        db.add_roi(done, 0, 0.1, 0.1, 0.2, 0.2, viewpoint="0", emb=1)
        # a media without rois counts as media but adds no rois
        _add_media(db, upload_id, ids["station_id"], "b.jpg")
        counts = workflow_counts(db, ids["survey_id"])
        assert counts.media == 3
        assert counts.undetected == 1
        assert counts.rois == 2
        assert counts.unembedded == 1
        assert counts.missing_viewpoint == 1
        assert counts.unidentified == 1
        assert counts.individuals == 1

    def test_other_survey_is_not_counted(self, populated_db):
        db, _, ids = populated_db
        other = db.add_survey("Other", ids["region_id"], None, None)
        counts = workflow_counts(db, other)
        assert counts == WorkflowCounts()

    def test_unknown_survey_gives_zeros(self, tmp_db):
        db, _ = tmp_db
        assert workflow_counts(db, 999) == WorkflowCounts()
