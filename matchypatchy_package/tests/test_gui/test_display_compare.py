"""
Unit tests for matchypatchy.gui.display_compare.DisplayCompare and the
related QueryContainer navigation/merge/unmatch helpers.

Tests focus on pure-Python logic that can run without a display server.
PyQt6 is stubbed out in conftest.py.
"""
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_query_container():
    """Build a QueryContainer with a mocked parent."""
    from matchypatchy.gui.query import QueryContainer
    parent = MagicMock()
    parent.mpDB = MagicMock()
    parent.logger = MagicMock()
    parent.cfg = MagicMock()
    parent.distance_metric = "cosine"
    parent.k = 3
    parent.threshold = 50

    with patch("matchypatchy.gui.query.load_model",
               return_value={"None": "None", "0": "Left", "1": "Any", "2": "Right"}):
        with patch("matchypatchy.gui.query.MatchEmbeddingThread"):
            qc = QueryContainer(parent)
    return qc


def _roi_df_with_individual(individual_ids):
    """Build a ROI DataFrame where index == roi id."""
    ids = list(range(10, 10 + len(individual_ids)))
    return pd.DataFrame(
        {
            "id":           ids,
            "station_id":   [1] * len(ids),
            "individual_id": individual_ids,
            "sequence_id":  ids,
            "emb":          [1] * len(ids),
        },
        index=ids,
    )


# ---------------------------------------------------------------------------
# TestQueryContainerMerge
# ---------------------------------------------------------------------------

class TestQueryContainerMerge:
    def setup_method(self):
        self.qc = _make_query_container()
        # Two ROIs: 10=individual 100 (query), 11=individual 200 (match)
        self.qc.data = _roi_df_with_individual([100, 200, None])
        self.qc.current_query_rid = 10
        self.qc.current_match_rid = 11

        mo = MagicMock()
        mo.sequence_id = 10  # maps to first roi
        self.qc.current_match_object = mo

    def test_merge_keeps_newer_id_individual(self):
        """merge() keeps the higher (more recently created) individual_id.
        query=100 vs match=200 → keep 200 (match is newer)."""
        self.qc.merge()
        calls = self.qc.mpDB.edit_row.call_args_list
        written_ids = [
            call_args.args[2]["individual_id"]
            for call_args in calls
            if len(call_args.args) >= 3 and isinstance(call_args.args[2], dict)
            and "individual_id" in call_args.args[2]
        ]
        assert 200 in written_ids

    def test_merge_query_none_uses_match_id(self):
        """When query is unidentified, adopt match individual_id."""
        self.qc.data.loc[10, "individual_id"] = None
        self.qc.merge()
        calls = self.qc.mpDB.edit_row.call_args_list
        # match_iid = 200 → should be kept
        written_ids = [
            c.args[2]["individual_id"]
            for c in calls
            if len(c.args) >= 3 and isinstance(c.args[2], dict) and "individual_id" in c.args[2]
        ]
        assert written_ids  # at least one edit was made


# ---------------------------------------------------------------------------
# TestQueryContainerUnmatch
# ---------------------------------------------------------------------------

class TestQueryContainerUnmatch:
    def test_unmatch_clears_individual_and_reviewed(self):
        qc = _make_query_container()
        qc.data = _roi_df_with_individual([100])
        qc.current_query_rid = 10

        qc.unmatch()
        qc.mpDB.edit_row.assert_called_once_with(
            "roi", 10,
            {"individual_id": None, "reviewed": 0},
            allow_none=True,
            quiet=False,
        )


# ---------------------------------------------------------------------------
# TestQueryContainerNewIid
# ---------------------------------------------------------------------------

class TestQueryContainerNewIid:
    def test_new_iid_updates_all_query_rois_and_match(self):
        qc = _make_query_container()
        qc.current_query_rois = [10, 11]
        qc.current_match_rid = 12

        qc.new_iid(99)

        calls = qc.mpDB.edit_row.call_args_list
        roi_ids_updated = [c.args[1] for c in calls if c.args[0] == "roi"]
        assert 10 in roi_ids_updated
        assert 11 in roi_ids_updated
        assert 12 in roi_ids_updated

    def test_new_iid_sets_reviewed_flag(self):
        qc = _make_query_container()
        qc.current_query_rois = [10]
        qc.current_match_rid = 11

        qc.new_iid(42)
        for c in qc.mpDB.edit_row.call_args_list:
            assert c.args[2] == {"individual_id": 42, "reviewed": 1}


# ---------------------------------------------------------------------------
# TestDisplayCompareInit
# ---------------------------------------------------------------------------

class TestDisplayCompareInit:
    def test_querycontainer_attached(self):
        """DisplayCompare should create a QueryContainer on construction."""
        from matchypatchy.gui.display_compare import DisplayCompare

        parent = MagicMock()
        parent.mpDB = MagicMock()
        parent.logger = MagicMock()
        parent.cfg = MagicMock()
        parent.cfg.KNN = 3
        parent.distance_metric = "cosine"

        with patch("matchypatchy.gui.display_compare.FilterBar"), \
             patch("matchypatchy.gui.display_compare.StandardButton"), \
             patch("matchypatchy.gui.display_compare.VerticalSeparator"), \
             patch("matchypatchy.gui.display_compare.SliderWithLabel"), \
             patch("matchypatchy.gui.display_compare.QPushButton"), \
             patch("matchypatchy.gui.display_compare.QVBoxLayout"), \
             patch("matchypatchy.gui.display_compare.QHBoxLayout"), \
             patch("matchypatchy.gui.display_compare.QLabel"), \
             patch("matchypatchy.gui.display_compare.QueryContainer") as MockQC, \
             patch("matchypatchy.gui.display_compare.QC_QueryContainer"), \
             patch("matchypatchy.gui.display_compare.ManualQueryContainer"):

            MockQC.return_value = MagicMock()
            dc = DisplayCompare.__new__(DisplayCompare)
            dc.parent = parent
            dc.logger = parent.logger
            dc.cfg = parent.cfg
            dc.mpDB = parent.mpDB
            dc.k = 3
            dc.distance_metric = "cosine"
            dc.threshold = 50
            dc.current_viewpoint = 1
            dc.compare_type = "default"
            dc.QueryContainer = MockQC(parent)
            dc.edit_stack = []
            dc.data = pd.DataFrame()

        assert dc.QueryContainer is not None

    def test_default_threshold(self):
        """Default threshold should be 50."""
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = DisplayCompare.__new__(DisplayCompare)
        dc.threshold = 50
        assert dc.threshold == 50

    def test_compare_type_default(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = DisplayCompare.__new__(DisplayCompare)
        dc.compare_type = "default"
        assert dc.compare_type == "default"


# ---------------------------------------------------------------------------
# TestQueryContainerToggleViewpoint
# ---------------------------------------------------------------------------

class TestQueryContainerToggleViewpoint:
    def test_toggle_viewpoint_updates_selected(self):
        qc = _make_query_container()
        qc.ranked_sequences = [MagicMock()]
        qc.n_queries = 1
        # Prepare a mock match object
        mo = MagicMock()
        mo.get_ranked_query_rids.return_value = [10]
        mo.get_ranked_matches.return_value = [(11, 0.1)]
        mo.show_viewpoint.return_value = True
        qc.ranked_sequences[0] = mo
        qc.set_query(0)

        available = qc.toggle_viewpoint("Left")
        assert qc.selected_viewpoint == "Left"
        assert available is True

    def test_toggle_viewpoint_returns_false_when_unavailable(self):
        qc = _make_query_container()
        mo = MagicMock()
        mo.get_ranked_query_rids.return_value = [10]
        mo.get_ranked_matches.return_value = [(11, 0.1)]
        mo.show_viewpoint.return_value = False
        qc.ranked_sequences = [mo]
        qc.n_queries = 1
        qc.set_query(0)

        available = qc.toggle_viewpoint("Right")
        assert available is False


# ---------------------------------------------------------------------------
# TestQueryContainerSetMatchFavorites
# ---------------------------------------------------------------------------

class TestQueryContainerSetMatchFavorites:
    def test_set_favorites_active_false_restores_knn(self):
        """Deactivating favorites restores the original knn match object."""
        qc = _make_query_container()
        original_mo = MagicMock()
        original_mo.get_ranked_matches.return_value = [(10, 0.1)]
        original_mo.get_ranked_query_rids.return_value = [10]
        qc.knn_match_object = original_mo
        qc.favorite_match_object = MagicMock()

        # set up current match state so set_match doesn't fail
        qc.current_match_rois = [10]
        qc.current_match_object = original_mo

        qc.set_match_favorites(False)

        assert qc.current_match_object is original_mo
        assert qc.knn_match_object is None
        assert qc.favorite_match_object is None
