"""
Unit tests for matchypatchy.gui.query.QueryContainer

QueryContainer holds query/match navigation state and exposes pure-Python
helper methods that can be exercised without a real Qt display server.
PyQt6 is stubbed out in conftest.py.
"""
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers to build lightweight QueryContainer instances
# ---------------------------------------------------------------------------

def _make_parent(db=None):
    """Build a minimal parent mock that QueryContainer expects."""
    parent = MagicMock()
    parent.mpDB = db or MagicMock()
    parent.logger = MagicMock()
    parent.cfg = MagicMock()
    parent.distance_metric = "cosine"
    parent.k = 3
    parent.threshold = 50
    return parent


def _make_qc(db=None):
    """Instantiate QueryContainer with a mocked parent."""
    from matchypatchy.gui.query import QueryContainer
    parent = _make_parent(db)
    with patch("matchypatchy.gui.query.load_model", return_value={"0": "Left", "1": "Any", "2": "Right"}):
        with patch("matchypatchy.gui.query.MatchEmbeddingThread"):
            qc = QueryContainer(parent)
    return qc


def _sample_roi_df():
    """Return a small DataFrame that mimics the roi-media joined table.

    individual_id uses object dtype so Python ``None`` is preserved
    (needed for ``is None`` checks in the source code).
    """
    df = pd.DataFrame(
        {
            "id":            [10, 11, 12, 13],
            "station_id":    [1,   1,  2,  2],
            "individual_id": pd.array([100, 100, pd.NA, 200], dtype="Int64"),
            "emb":           [1,   1,   0,   1],
            "sequence_id":   [1,   1,   2,   3],
            "favorite":      [0,   1,   0,   0],
        },
        index=[10, 11, 12, 13],
    )
    # Convert individual_id to object so None comparisons work correctly
    df["individual_id"] = df["individual_id"].astype(object).where(df["individual_id"].notna(), None)
    return df


# ---------------------------------------------------------------------------
# TestQueryContainerInit
# ---------------------------------------------------------------------------

class TestQueryContainerInit:
    def test_initial_data_empty(self):
        qc = _make_qc()
        assert qc.data_raw.empty
        assert qc.data.empty

    def test_initial_counters_zero(self):
        qc = _make_qc()
        assert qc.current_query == 0
        assert qc.current_match == 0
        assert qc.n_queries == 0

    def test_initial_threshold(self):
        qc = _make_qc()
        assert qc.threshold == 50

    def test_set_threshold(self):
        qc = _make_qc()
        qc.set_threshold(75)
        assert qc.threshold == 75


# ---------------------------------------------------------------------------
# TestQueryContainerFilter
# ---------------------------------------------------------------------------

class TestQueryContainerFilter:
    def setup_method(self):
        self.qc = _make_qc()
        self.qc.data_raw = _sample_roi_df()

    def test_filter_no_args_copies_all(self):
        """filter(None, None) should keep all rows."""
        self.qc.filter()
        assert len(self.qc.data) == 4

    def test_filter_by_station(self):
        """Single-station filter keeps only matching rows."""
        filter_dict = {
            "active_region":  (0,),
            "active_survey":  (0,),
            "active_station": (1,),
        }
        valid_stations = {1: "Station A"}
        self.qc.filter(filter_dict, valid_stations)
        assert all(self.qc.data["station_id"] == 1)

    def test_filter_by_survey_restricts_to_valid_stations(self):
        """Survey filter restricts to rows whose station is in valid_stations."""
        filter_dict = {
            "active_region":  (0,),
            "active_survey":  (1,),
            "active_station": (0,),
        }
        valid_stations = {2: "Station B"}
        self.qc.filter(filter_dict, valid_stations)
        assert all(self.qc.data["station_id"] == 2)

    def test_filter_empty_valid_stations(self):
        """Empty valid_stations dict → no station-based filter is applied,
        and the show_progress helper is called for the no-stations case."""
        filter_dict = {
            "active_region":  (0,),
            "active_survey":  (0,),
            "active_station": (0,),
        }
        valid_stations = {}
        self.qc.filter(filter_dict, valid_stations)
        # When no valid stations, the else-branch notifies the parent
        self.qc.parent.show_progress.assert_called()

    def test_filter_preserves_data_raw(self):
        """data_raw should not be mutated by filter()."""
        original_len = len(self.qc.data_raw)
        self.qc.filter(
            {"active_region": (0,), "active_survey": (1,), "active_station": (1,)},
            {1: "Station A"},
        )
        assert len(self.qc.data_raw) == original_len


# ---------------------------------------------------------------------------
# TestQueryNavigation
# ---------------------------------------------------------------------------

class TestQueryNavigation:
    def setup_method(self):
        self.qc = _make_qc()
        # Build mock MatchObjects
        mo0 = MagicMock()
        mo0.get_ranked_query_rids.return_value = [10, 11]
        mo0.get_ranked_matches.return_value = [(12, 0.1), (13, 0.3)]
        mo0.sequence_id = 1

        mo1 = MagicMock()
        mo1.get_ranked_query_rids.return_value = [12]
        mo1.get_ranked_matches.return_value = [(10, 0.2)]
        mo1.sequence_id = 2

        self.qc.ranked_sequences = [mo0, mo1]
        self.qc.n_queries = 2

    def test_set_query_first(self):
        self.qc.set_query(0)
        assert self.qc.current_query == 0
        assert self.qc.current_query_rid == 10

    def test_set_query_second(self):
        self.qc.set_query(1)
        assert self.qc.current_query == 1
        assert self.qc.current_query_rid == 12

    def test_set_query_wraps_negative(self):
        """Negative index wraps to last query."""
        self.qc.set_query(-1)
        assert self.qc.current_query == 1

    def test_set_query_wraps_overflow(self):
        """Index beyond end wraps to first query."""
        self.qc.set_query(99)
        assert self.qc.current_query == 0

    def test_set_match_sets_rid(self):
        self.qc.set_query(0)
        self.qc.set_match(0)
        assert self.qc.current_match_rid == 12

    def test_set_match_second(self):
        self.qc.set_query(0)
        self.qc.set_match(1)
        assert self.qc.current_match_rid == 13

    def test_set_match_wraps_negative(self):
        self.qc.set_query(0)
        self.qc.set_match(-1)
        assert self.qc.current_match == 1

    def test_capture_ranked_sequences(self):
        new_seqs = [MagicMock()]
        self.qc.capture_ranked_sequences(new_seqs)
        assert self.qc.n_queries == 1

    def test_set_within_query_sequence_wraps(self):
        self.qc.set_query(0)  # query_rois = [10, 11]
        self.qc.set_within_query_sequence(-1)
        assert self.qc.current_query_sn == 1

    def test_set_within_query_sequence_overflow(self):
        self.qc.set_query(0)
        self.qc.set_within_query_sequence(99)
        assert self.qc.current_query_sn == 0


# ---------------------------------------------------------------------------
# TestQueryStateHelpers
# ---------------------------------------------------------------------------

class TestQueryStateHelpers:
    def setup_method(self):
        self.qc = _make_qc()
        self.qc.data = _sample_roi_df()
        # both rois 10 & 11 share individual_id=100
        self.qc.current_query_rid = 10
        self.qc.current_match_rid = 11

    def test_is_existing_match_true(self):
        """Same individual_id → existing match."""
        assert self.qc.is_existing_match() is True

    def test_is_existing_match_false_different_individual(self):
        """Different individual_ids → not a match."""
        self.qc.current_match_rid = 13  # individual_id=200
        assert not self.qc.is_existing_match()

    def test_is_existing_match_false_none_individual(self):
        """None individual_id → not a match."""
        self.qc.current_match_rid = 12  # individual_id=None
        assert not self.qc.is_existing_match()

    def test_both_unnamed_true(self):
        """Two unnamed ROIs."""
        self.qc.current_query_rid = 12
        self.qc.current_match_rid = 12
        # Force both to None
        self.qc.data.loc[12, "individual_id"] = None
        assert self.qc.both_unnamed() is True

    def test_both_unnamed_false_when_one_named(self):
        """One named ROI → not both unnamed."""
        assert self.qc.both_unnamed() is False

    def test_current_distance(self):
        """current_distance returns the distance for the active match."""
        mo = MagicMock()
        mo.get_ranked_matches.return_value = [(11, 0.42), (13, 0.9)]
        self.qc.current_match_object = mo
        self.qc.current_match = 0
        assert abs(self.qc.current_distance() - 0.42) < 1e-9

    def test_get_info_column(self):
        """get_info() returns specific column value."""
        val = self.qc.get_info(10, "station_id")
        assert val == 1

    def test_get_info_full_row(self):
        """get_info() with no column returns full row."""
        row = self.qc.get_info(10)
        assert row["station_id"] == 1


# ---------------------------------------------------------------------------
# TestFinishCalculating
# ---------------------------------------------------------------------------

class TestFinishCalculating:
    def test_emits_true_when_sequences_present(self):
        qc = _make_qc()
        qc.ranked_sequences = [MagicMock()]
        emitted = []
        qc.thread_signal.connect(emitted.append)
        qc.finish_calculating()
        assert emitted == [True]

    def test_emits_false_when_no_sequences(self):
        qc = _make_qc()
        qc.ranked_sequences = []
        emitted = []
        qc.thread_signal.connect(emitted.append)
        qc.finish_calculating()
        assert emitted == [False]
