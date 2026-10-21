"""
Match actions in the QC and manual query containers

DisplayCompare's Match / Unmatch call the same container methods in every
compare mode, so QC and manual must support them like the default container.
"""
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


def _roi_media():
    """
    roi_media as fetch_roi_media returns it (indexed by roi id, nulls as None)

    individual 1: rois 10, 11 (sequence 100)
    individual 2: rois 12, 13 (sequence 101)
    unnamed:      roi 14 (sequence 102)
    """
    df = pd.DataFrame({
        "id": [10, 11, 12, 13, 14],
        "individual_id": [1.0, 1.0, 2.0, 2.0, None],
        "sequence_id": [100, 100, 101, 101, 102],
        "station_id": [1, 1, 1, 1, 1],
        "viewpoint": [0, 1, 0, None, 1],
        "emb": [1, 1, 1, 1, 1],
    }).set_index("id")
    return df.astype(object).replace({float("nan"): None})


def _container(kind):
    parent = MagicMock()
    if kind == "qc":
        from matchypatchy.gui.query_qc import QC_QueryContainer as cls
        module = "matchypatchy.gui.query_qc"
        args = ()
    else:
        from matchypatchy.gui.query_manual import ManualQueryContainer as cls
        module = "matchypatchy.gui.query_manual"
        args = ([10, 11, 12, 13, 14],)
    with patch(f"{module}.load_model", return_value={}):
        container = cls(parent, *args)
    with patch(f"{module}.db_roi.fetch_roi_media", side_effect=lambda *a, **k: _roi_media()):
        container.load_data()
    container.filter()
    return container


@pytest.fixture(params=["qc", "manual"])
def container(request):
    return _container(request.param)


class TestMatchActions:
    """Every method DisplayCompare.confirm_match / unmatch calls exists and works"""

    def test_sequence_ids(self, container):
        container.current_query_rid, container.current_match_rid = 10, 12
        assert container.get_query_sequence_id() == 100
        assert container.get_match_sequence_id() == 101

    def test_both_unnamed(self, container):
        container.current_query_rid, container.current_match_rid = 14, 14
        assert container.both_unnamed() is True
        container.current_query_rid, container.current_match_rid = 14, 10
        assert container.both_unnamed() is False

    def test_merge_keeps_lower_id_and_moves_all_rois_of_the_other(self, container):
        """Query individual 2, match individual 1: individual 2's rois all become 1"""
        container.current_query_rid, container.current_match_rid = 12, 10
        container.merge()
        updates = container.mpDB.batch_edit.call_args.args[1]
        assert {rid: u["individual_id"] for rid, u in updates.items()} == {10: 1, 12: 1, 13: 1}
        assert container.data.loc[13, "individual_id"] == 1

    def test_merge_unnamed_query_into_named_match(self, container):
        container.current_query_rid, container.current_match_rid = 14, 12
        container.merge()
        updates = container.mpDB.batch_edit.call_args.args[1]
        assert {rid: u["individual_id"] for rid, u in updates.items()} == {14: 2, 12: 2}

    def test_unmatch_then_refresh(self, container):
        container.current_query_rid, container.current_match_rid = 11, 10
        container.unmatch()
        # only the roi on screen, not the rest of the individual
        container.mpDB.batch_edit.assert_called_once_with(
            "roi", {11: {"individual_id": None, "reviewed": 0}}, allow_none=True, quiet=True)
        # DisplayCompare refreshes through these after match / unmatch
        module = type(container).__module__
        with patch(f"{module}.db_roi.fetch_roi_media", side_effect=lambda *a, **k: _roi_media()):
            container.update_partial_sequences([100])
            container.update_sequences_in_place(100, 101)


class TestRefreshData:
    def test_keeps_the_filtered_rows(self):
        container = _container("manual")
        container.data = container.data.loc[[10, 12]]
        with patch("matchypatchy.gui.query_manual.db_roi.fetch_roi_media",
                   side_effect=lambda *a, **k: _roi_media()):
            container.refresh_data()
        assert sorted(container.data.index) == [10, 12]


class TestLookupFallback:
    def test_info_for_roi_outside_the_filter(self, container):
        """Favorites may lie outside the filter; their info comes from the unfiltered data"""
        container.data = container.data.loc[[10]]
        assert container.get_info(12, "sequence_id") == 101
        assert container.get_info(12)["sequence_id"] == 101


VIEWPOINTS = {"Any": "Any", "None": "None", "0": "Left", "1": "Right"}
LEFT, ANY, RIGHT = 0, 1, 2  # compare view toggle positions


@pytest.fixture
def viewpoint_labels():
    with patch("matchypatchy.threads.match_object.load_model", return_value=VIEWPOINTS):
        yield


class TestViewpointToggle:
    """Stored viewpoints: 10 Left(0), 11 Right(1), 12 Left(0), 13 None, 14 Right(1)"""

    def test_toggle_positions_follow_model_labels(self, viewpoint_labels):
        from matchypatchy.threads.match_object import toggle_viewpoint_value
        assert toggle_viewpoint_value(LEFT) == 0
        assert toggle_viewpoint_value(RIGHT) == 1
        assert toggle_viewpoint_value(ANY) is None

    def test_match_object_left_shows_left_labelled_rois(self, viewpoint_labels):
        from matchypatchy.threads.match_object import MatchObject
        query = pd.DataFrame({"id": [10, 11], "viewpoint": [0, 1]})
        matches = pd.DataFrame({"id": [12, 14], "viewpoint": [0, 1]})
        mo = MatchObject(1, [(12, 0.1), (14, 0.2)], query, matches)
        mo.og_ranked_query_rids, mo.og_ranked_matches = [10, 11], [(12, 0.1), (14, 0.2)]
        assert mo.show_viewpoint(LEFT) is True
        assert mo.ranked_query_rids == [10] and mo.ranked_matches == [(12, 0.1)]
        assert mo.show_viewpoint(RIGHT) is True
        assert mo.ranked_query_rids == [11] and mo.ranked_matches == [(14, 0.2)]

    def test_manual_left_then_any_restores(self, viewpoint_labels):
        container = _container("manual")
        container.set_query(0)  # query roi 10 (Left), matches all rois
        assert container.toggle_viewpoint(LEFT) is True
        assert container.current_query_rois == [10]
        assert container.current_match_rois == [10, 12]
        assert container.toggle_viewpoint(ANY) is True
        assert container.current_match_rois == [10, 11, 12, 13, 14]

    def test_manual_unavailable_viewpoint_keeps_all(self, viewpoint_labels):
        container = _container("manual")
        container.set_query(0)  # roi 10 is Left, so no Right query
        assert container.toggle_viewpoint(RIGHT) is False
        assert container.current_query_rois == [10]
        assert container.current_match_rois == [10, 11, 12, 13, 14]
        # navigation still works afterwards
        container.set_match(container.current_match + 1)

    def test_qc_left_then_any_restores(self, viewpoint_labels):
        container = _container("qc")
        container.set_query(0)
        all_rois = list(container.current_query_rois)
        assert container.toggle_viewpoint(LEFT) is True
        assert all(container.data.loc[r, "viewpoint"] == 0 for r in container.current_query_rois)
        assert container.toggle_viewpoint(ANY) is True
        assert container.current_query_rois == all_rois


class TestNoSelfComparison:
    def test_manual_match_is_never_the_query(self):
        container = _container("manual")
        for n in range(container.n_queries):
            container.set_query(n)
            for _ in range(len(container.current_match_rois)):
                assert container.current_match_rid != container.current_query_rid
                container.set_match(container.current_match + 1)

    def test_backwards_navigation_skips_query_too(self):
        container = _container("manual")
        container.set_query(2)  # query roi 12
        for _ in range(len(container.current_match_rois)):
            container.set_match(container.current_match - 1)
            assert container.current_match_rid != 12

    def test_qc_moving_query_moves_match_off_it(self):
        container = _container("qc")
        container.set_query(0)  # individual with two rois
        container.set_within_query_sequence(1)
        assert container.current_match_rid != container.current_query_rid

    def test_qc_distance_is_query_match_similarity(self):
        container = _container("qc")
        container.current_query_rid, container.current_match_rid = 10, 11
        container.mpDB.calculate_similarity.return_value = 0.75
        assert container.current_distance() == pytest.approx(0.25)
        container.mpDB.calculate_similarity.assert_called_with(10, 11)
        container.mpDB.calculate_similarity.return_value = None
        assert container.current_distance() is None


def _qc_filters(individual):
    return {"active_region": (0,), "active_survey": (0,),
            "active_station": (0,), "active_individual": (individual,)}


class TestQCIndividualFilter:
    def test_individual_filter_keeps_its_rois(self):
        container = _container("qc")
        assert container.filter(_qc_filters(2), {1: "A"}) is True
        assert list(container.individuals) == [2]
        assert sorted(container.data.index) == [12, 13]

    def test_individual_without_rois_has_no_data(self):
        """An individual emptied by a merge is still listed in the filterbar"""
        container = _container("qc")
        assert container.filter(_qc_filters(3), {1: "A"}) is False
        assert container.individuals == {}
