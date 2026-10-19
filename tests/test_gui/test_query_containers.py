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
        "viewpoint": [1, 0, 1, None, 0],
        "emb": [1, 1, 1, 1, 1],
    }).set_index("id")
    return df.astype(object).replace({float("nan"): None})


def _container(kind):
    parent = MagicMock()
    if kind == "qc":
        from matchypatchy.gui.qc_query import QC_QueryContainer as cls
        module = "matchypatchy.gui.qc_query"
        args = ()
    else:
        from matchypatchy.gui.manual_query import ManualQueryContainer as cls
        module = "matchypatchy.gui.manual_query"
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
        container.mpDB.edit_row.assert_called_once_with(
            "roi", 11, {"individual_id": None, "reviewed": 0}, allow_none=True, quiet=True)
        # DisplayCompare refreshes through these after match / unmatch
        module = type(container).__module__
        with patch(f"{module}.db_roi.fetch_roi_media", side_effect=lambda *a, **k: _roi_media()):
            container.update_partial_sequences([100])
            container.update_sequences_in_place(100, 101)


class TestRefreshData:
    def test_keeps_the_filtered_rows(self):
        container = _container("manual")
        container.data = container.data.loc[[10, 12]]
        with patch("matchypatchy.gui.manual_query.db_roi.fetch_roi_media",
                   side_effect=lambda *a, **k: _roi_media()):
            container.refresh_data()
        assert sorted(container.data.index) == [10, 12]


class TestLookupFallback:
    def test_info_for_roi_outside_the_filter(self, container):
        """Favorites may lie outside the filter; their info comes from the unfiltered data"""
        container.data = container.data.loc[[10]]
        assert container.get_info(12, "sequence_id") == 101
        assert container.get_info(12)["sequence_id"] == 101
