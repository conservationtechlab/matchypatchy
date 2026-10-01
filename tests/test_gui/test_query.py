"""
Unit tests for matchypatchy.gui.query.QueryContainer

QueryContainer holds query/match navigation state, the KNN cache, and the
filter-after-cache pipeline:

    load_data -> set_filter -> (load_knn_cache | calculate_neighbors)
              -> finish_calculating -> finalize -> filter + _restrict_to_data

PyQt6 is stubbed out in conftest.py, so no display server is required.
"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

QUERY = "matchypatchy.gui.query"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_parent(db=None, cache_dir=None):
    """Build a minimal parent mock that QueryContainer expects."""
    parent = MagicMock()
    parent.mpDB = db or MagicMock()
    parent.logger = MagicMock()
    parent.cfg = MagicMock()
    parent.cfg.DB_DIR = str(cache_dir)
    parent.distance_metric = "cosine"
    parent.k = 3
    parent.threshold = 50
    return parent


def _make_qc(cache_dir, db=None):
    """Instantiate QueryContainer with a mocked parent and a temp cache dir."""
    from matchypatchy.gui.query import QueryContainer
    parent = _make_parent(db, cache_dir)
    with patch(f"{QUERY}.load_model", return_value={"0": "Left", "1": "Any", "2": "Right"}):
        qc = QueryContainer(parent)
    return qc


def _sample_roi_df():
    """Small DataFrame mimicking db_roi.fetch_roi_media().

    ROI ids live in the index (named 'id'), not in a column.
    individual_id is object dtype so Python None is preserved.

        id  station  individual  sequence
        10     1         100         1
        11     1         100         1
        12     2         None        2
        13     2         200         3
    """
    df = pd.DataFrame(
        {
            "station_id":  [1, 1, 2, 2],
            "emb":         [1, 1, 0, 1],
            "sequence_id": [1, 1, 2, 3],
            "favorite":    [0, 1, 0, 0],
        },
        index=pd.Index([10, 11, 12, 13], name="id"),
    )
    df["individual_id"] = pd.Series([100, 100, None, 200], index=df.index, dtype=object)
    return df


def _filter_dict(region=0, survey=0, station=0):
    return {
        "active_region":  (region,),
        "active_survey":  (survey,),
        "active_station": (station,),
    }


def _raw(seq_id, query_rids, neighbors, truncated=False):
    """One serialized (cache-format) sequence entry."""
    return {
        "sequence_id": seq_id,
        "neighbors": neighbors,
        "truncated": truncated,
        "og_ranked_query_rids": query_rids,
        "og_ranked_matches": neighbors,
    }


def _fake_match(seq_id, neighbors, query_rids):
    """Stand-in for a MatchObject as returned by MatchEmbeddingThread."""
    return SimpleNamespace(
        sequence_id=seq_id,
        neighbors=neighbors,
        og_ranked_query_rids=query_rids,
        og_ranked_matches=neighbors,
    )


def _collect(signal):
    emitted = []
    signal.connect(emitted.append)
    return emitted


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_db_roi():
    """Replace the db_roi module inside query.py for every test."""
    with patch(f"{QUERY}.db_roi") as m:
        m.sequence_roi_dict.return_value = {}
        yield m


@pytest.fixture
def qc(tmp_path):
    return _make_qc(tmp_path)


@pytest.fixture
def qc_raw(qc):
    """Container with data_raw loaded (no filtering applied yet)."""
    qc.data_raw = _sample_roi_df()
    return qc


@pytest.fixture
def fake_match_object():
    """MatchObject that just records its kwargs (real one needs viewpoint columns etc.)."""
    with patch(f"{QUERY}.MatchObject", side_effect=lambda **kw: SimpleNamespace(**kw)) as m:
        yield m


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

class TestQueryContainerInit:
    def test_initial_data_empty(self, qc):
        assert qc.data_raw.empty
        assert qc.data.empty

    def test_initial_counters_zero(self, qc):
        assert qc.current_query == 0
        assert qc.current_match == 0
        assert qc.n_queries == 0

    def test_initial_threshold(self, qc):
        assert qc.threshold == 50

    def test_set_threshold(self, qc):
        qc.set_threshold(75)
        assert qc.threshold == 75

    def test_k_cache_is_overfetched(self, qc):
        from matchypatchy.gui.query import KNN_OVERFETCH
        assert qc.k == 3
        assert qc.k_cache == qc.k * KNN_OVERFETCH

    def test_initial_pipeline_state(self, qc):
        assert qc._raw_ranked is None
        assert qc._from_cache is False
        assert qc._stop_requested is False
        assert qc.filter_matched is True
        assert qc.valid_stations is None

    def test_cache_path_in_db_dir(self, qc, tmp_path):
        assert qc.CACHE_PATH == tmp_path / "knn_cache.json"


# ---------------------------------------------------------------------------
# load_data / set_filter
# ---------------------------------------------------------------------------

class TestLoadData:
    def test_false_when_no_rows(self, qc, mock_db_roi):
        mock_db_roi.fetch_roi_media.return_value = pd.DataFrame()
        assert qc.load_data() is False

    def test_false_when_no_embeddings(self, qc, mock_db_roi):
        df = _sample_roi_df()
        df["emb"] = 0
        mock_db_roi.fetch_roi_media.return_value = df
        assert qc.load_data() is False

    def test_true_when_some_embeddings(self, qc, mock_db_roi):
        mock_db_roi.fetch_roi_media.return_value = _sample_roi_df()
        assert qc.load_data() is True
        assert len(qc.data_raw) == 4

    def test_emits_loaded_data(self, qc, mock_db_roi):
        mock_db_roi.fetch_roi_media.return_value = _sample_roi_df()
        emitted = _collect(qc.loaded_data)
        qc.load_data()
        assert len(emitted) == 1

    def test_does_not_filter(self, qc, mock_db_roi):
        """Filtering now happens in finalize(), not load_data()."""
        mock_db_roi.fetch_roi_media.return_value = _sample_roi_df()
        qc.load_data()
        assert qc.data.empty

    def test_resets_stop_flag(self, qc, mock_db_roi):
        mock_db_roi.fetch_roi_media.return_value = _sample_roi_df()
        qc._stop_requested = True
        qc.load_data()
        assert qc._stop_requested is False


class TestSetFilter:
    def test_stores_filter_state(self, qc):
        fd, vs = _filter_dict(station=1), {1: "A"}
        qc.set_filter(fd, vs)
        assert qc.filter_dict is fd
        assert qc.valid_stations is vs


# ---------------------------------------------------------------------------
# filter()
# ---------------------------------------------------------------------------

class TestQueryContainerFilter:
    def test_filter_no_args_copies_all(self, qc_raw):
        assert qc_raw.filter() is True
        assert len(qc_raw.data) == 4

    def test_filter_no_args_is_independent_copy(self, qc_raw):
        qc_raw.filter()
        qc_raw.data.loc[10, "station_id"] = 99
        assert qc_raw.data_raw.loc[10, "station_id"] == 1

    def test_filter_valid_stations_none_keeps_all(self, qc_raw):
        assert qc_raw.filter(_filter_dict(station=1), None) is True
        assert len(qc_raw.data) == 4

    def test_filter_by_station(self, qc_raw):
        assert qc_raw.filter(_filter_dict(station=1), {1: "Station A"}) is True
        assert set(qc_raw.data["station_id"]) == {1}
        assert len(qc_raw.data) == 2

    def test_filter_by_survey_restricts_to_valid_stations(self, qc_raw):
        assert qc_raw.filter(_filter_dict(survey=1), {2: "Station B"}) is True
        assert set(qc_raw.data["station_id"]) == {2}

    def test_filter_by_region_restricts_to_valid_stations(self, qc_raw):
        assert qc_raw.filter(_filter_dict(region=1), {1: "A", 2: "B"}) is True
        assert len(qc_raw.data) == 4

    def test_filter_empty_valid_stations(self, qc_raw):
        assert qc_raw.filter(_filter_dict(), {}) is False
        assert qc_raw.data.empty

    def test_filter_returns_false_when_nothing_left(self, qc_raw):
        """Stations that exist in the filter but not in the data -> empty -> False."""
        assert qc_raw.filter(_filter_dict(station=99), {99: "Ghost"}) is False
        assert qc_raw.data.empty

    def test_filter_preserves_data_raw(self, qc_raw):
        qc_raw.filter(_filter_dict(station=1), {1: "Station A"})
        assert len(qc_raw.data_raw) == 4

    def test_filter_builds_sequences_from_filtered_data(self, qc_raw, mock_db_roi):
        mock_db_roi.sequence_roi_dict.return_value = {"seq": [1]}
        qc_raw.filter(_filter_dict(station=1), {1: "A"})
        assert qc_raw.sequences == {"seq": [1]}
        assert mock_db_roi.sequence_roi_dict.call_args.args[0] is qc_raw.data

    def test_build_seq_indices(self, qc_raw):
        qc_raw._build_seq_indices()
        assert qc_raw._seq_index == {1: [10, 11], 2: [12], 3: [13]}


class TestValidStations:
    def test_empty_returns_none(self, qc):
        assert qc._get_valid_stations(_filter_dict(), {}) is None

    def test_single_station_has_priority(self, qc):
        ids = qc._get_valid_stations(_filter_dict(station=2, survey=1), {1: "A", 2: "B"})
        assert ids == {2}

    def test_survey_or_region_returns_all_valid(self, qc):
        assert qc._get_valid_stations(_filter_dict(survey=1), {1: "A", 2: "B"}) == {1, 2}
        assert qc._get_valid_stations(_filter_dict(region=1), {1: "A", 2: "B"}) == {1, 2}

    def test_no_active_filter_returns_all_valid(self, qc):
        assert qc._get_valid_stations(_filter_dict(), {1: "A"}) == {1}

    def test_remembers_valid_stations(self, qc):
        assert qc._get_valid_stations_from_current() is None
        qc._get_valid_stations(_filter_dict(), {1: "A"})
        assert qc._get_valid_stations_from_current() == {1: "A"}


# ---------------------------------------------------------------------------
# calculate_neighbors / thread control
# ---------------------------------------------------------------------------

class TestCalculateNeighbors:
    def _run(self, qc):
        with patch(f"{QUERY}.MatchEmbeddingThread") as thread_cls, \
             patch(f"{QUERY}.QTimer") as timer:
            qc.calculate_neighbors()
        return thread_cls, timer

    def test_uses_unfiltered_data_with_overfetch(self, qc_raw, mock_db_roi):
        qc_raw.data = qc_raw.data_raw.iloc[:1]          # pretend a filter is active
        mock_db_roi.sequence_roi_dict.return_value = {"raw": [1]}
        thread_cls, _ = self._run(qc_raw)

        args, kwargs = thread_cls.call_args
        assert args[0] is qc_raw.mpDB
        assert args[1] is qc_raw.data_raw                # NOT the filtered data
        assert args[2] == {"raw": [1]}
        assert kwargs["k"] == qc_raw.k_cache             # NOT qc.k
        assert kwargs["metric"] == "cosine"
        assert kwargs["threshold"] == 50
        assert mock_db_roi.sequence_roi_dict.call_args.args[0] is qc_raw.data_raw

    def test_connects_signals_and_defers_start(self, qc_raw):
        thread_cls, timer = self._run(qc_raw)
        thread = thread_cls.return_value
        thread.progress_update.connect.assert_called_once_with(qc_raw.update_progress)
        thread.ranked_queries_return.connect.assert_called_once_with(qc_raw.capture_ranked_sequences)
        thread.finished.connect.assert_called_once_with(qc_raw.finish_calculating)
        timer.singleShot.assert_called_once_with(100, qc_raw.start_thread)

    def test_marks_results_as_not_from_cache(self, qc_raw):
        qc_raw._from_cache = True
        self._run(qc_raw)
        assert qc_raw._from_cache is False

    def test_start_thread_starts(self, qc):
        qc.match_thread = MagicMock()
        qc.start_thread()
        qc.match_thread.start.assert_called_once()

    def test_start_thread_skipped_after_cancel(self, qc):
        qc.match_thread = MagicMock()
        qc._stop_requested = True
        qc.start_thread()
        qc.match_thread.start.assert_not_called()

    def test_start_thread_without_thread_is_safe(self, qc):
        qc.start_thread()

    def test_stop_calculation_sets_flag_and_interrupts(self, qc):
        qc.match_thread = MagicMock()
        qc.stop_calculation()
        assert qc._stop_requested is True
        qc.match_thread.requestInterruption.assert_called_once()

    def test_stop_calculation_without_thread_is_safe(self, qc):
        qc.stop_calculation()
        assert qc._stop_requested is True

    def test_update_progress_forwards(self, qc):
        emitted = _collect(qc.progress_update)
        qc.update_progress(42)
        assert emitted == [42]


# ---------------------------------------------------------------------------
# Query navigation
# ---------------------------------------------------------------------------

class TestQueryNavigation:
    @pytest.fixture(autouse=True)
    def _setup(self, qc):
        self.qc = qc
        mo0 = MagicMock()
        mo0.get_ranked_query_rids.return_value = [10, 11]
        mo0.get_ranked_matches.return_value = [(12, 0.1), (13, 0.3)]
        mo0.sequence_id = 1

        mo1 = MagicMock()
        mo1.get_ranked_query_rids.return_value = [12]
        mo1.get_ranked_matches.return_value = [(10, 0.2)]
        mo1.sequence_id = 2

        qc.ranked_sequences = [mo0, mo1]
        qc.n_queries = 2

    def test_set_query_first(self):
        self.qc.set_query(0)
        assert self.qc.current_query == 0
        assert self.qc.current_query_rid == 10

    def test_set_query_second(self):
        self.qc.set_query(1)
        assert self.qc.current_query == 1
        assert self.qc.current_query_rid == 12

    def test_set_query_wraps_negative(self):
        self.qc.set_query(-1)
        assert self.qc.current_query == 1

    def test_set_query_wraps_overflow(self):
        self.qc.set_query(99)
        assert self.qc.current_query == 1

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

    def test_capture_ranked_sequences_sets_count(self):
        self.qc.capture_ranked_sequences([MagicMock()])
        assert self.qc.n_queries == 1

    def test_set_within_query_sequence_wraps(self):
        self.qc.set_query(0)
        self.qc.set_within_query_sequence(-1)
        assert self.qc.current_query_sn == 1

    def test_set_within_query_sequence_overflow(self):
        self.qc.set_query(0)
        self.qc.set_within_query_sequence(99)   # 99 % 2 = 1
        assert self.qc.current_query_sn == 1
        assert self.qc.current_query_rid == 11

    def test_get_query_sequence_id(self):
        self.qc.set_query(1)
        assert self.qc.get_query_sequence_id() == 2

    def test_get_query_sequence_id_none_before_query(self, qc):
        assert qc.get_query_sequence_id() is None

    def test_get_match_sequence_id_uses_match_roi(self):
        self.qc.data = _sample_roi_df()
        self.qc.set_query(0)
        self.qc.set_match(1)            # rid 13 -> sequence 3
        assert self.qc.get_match_sequence_id() == 3

    def test_toggle_viewpoint_refreshes_rois(self):
        self.qc.set_query(0)
        mo = self.qc.current_match_object
        mo.show_viewpoint.return_value = True
        mo.get_ranked_query_rids.return_value = [11]
        assert self.qc.toggle_viewpoint(2) is True
        mo.show_viewpoint.assert_called_once_with(2)
        assert self.qc.selected_viewpoint == 2
        assert self.qc.current_query_rois == [11]
        assert self.qc.current_query_rid == 11


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

class TestQueryStateHelpers:
    @pytest.fixture(autouse=True)
    def _setup(self, qc):
        self.qc = qc
        qc.data = _sample_roi_df()
        # rois 10 & 11 share individual_id=100
        qc.current_query_rid = 10
        qc.current_match_rid = 11

    def test_clean_iid(self):
        clean = self.qc._clean_iid
        assert clean(None) is None
        assert clean(np.nan) is None
        assert clean(pd.NA) is None
        assert clean(7.0) == 7 and isinstance(clean(7.0), int)
        assert clean(np.int64(5)) == 5 and isinstance(clean(np.int64(5)), int)

    def test_is_existing_match_true(self):
        assert self.qc.is_existing_match() is True

    def test_is_existing_match_false_different_individual(self):
        self.qc.current_match_rid = 13  # individual_id=200
        assert not self.qc.is_existing_match()

    def test_is_existing_match_false_none_individual(self):
        self.qc.current_match_rid = 12  # individual_id=None
        assert not self.qc.is_existing_match()

    def test_both_unnamed_true_with_none(self):
        self.qc.current_query_rid = 12
        self.qc.current_match_rid = 12
        assert self.qc.both_unnamed() is True

    def test_both_unnamed_true_with_nan(self):
        """NaN (what pandas produces for missing ids) counts as unnamed."""
        self.qc.data.loc[12, "individual_id"] = np.nan
        self.qc.current_query_rid = 12
        self.qc.current_match_rid = 12
        assert self.qc.both_unnamed() is True
        assert not self.qc.is_existing_match()

    def test_both_unnamed_false_when_one_named(self):
        assert self.qc.both_unnamed() is False

    def test_current_distance(self):
        mo = MagicMock()
        mo.get_ranked_matches.return_value = [(11, 0.42), (13, 0.9)]
        self.qc.current_match_object = mo
        self.qc.current_match = 0
        assert abs(self.qc.current_distance() - 0.42) < 1e-9

    def test_current_distance_out_of_range_is_inf(self):
        mo = MagicMock()
        mo.get_ranked_matches.return_value = []
        self.qc.current_match_object = mo
        assert self.qc.current_distance() == float("inf")

    def test_get_info_column(self):
        assert self.qc.get_info(10, "station_id") == 1

    def test_get_info_full_row(self):
        assert self.qc.get_info(10)["station_id"] == 1

    def test_get_info_unknown_rid_is_none(self):
        assert self.qc.get_info(999, "station_id") is None

    def test_get_info_bbox(self, mock_db_roi):
        mock_db_roi.get_roi_bbox.return_value = "BBOX"
        assert self.qc.get_info(10, "bbox") == "BBOX"
        assert list(mock_db_roi.get_roi_bbox.call_args.args[0].index) == [10]

    def test_get_info_metadata_delegates(self):
        with patch.object(self.qc, "roi_metadata", return_value={"k": 1}) as meta:
            assert self.qc.get_info(10, "metadata") == {"k": 1}
        assert meta.call_args.args[0]["station_id"] == 1

    def test_get_roi_full_record(self):
        assert self.qc._get_roi_full_record(10)["sequence_id"] == 1
        assert self.qc._get_roi_full_record(999) is None


class TestRoiMetadata:
    @staticmethod
    def _roi(viewpoint=1):
        return pd.Series({
            "name": "Bob", "sex": "M", "age": 5, "filepath": "/x/a.jpg",
            "comment": "hi", "timestamp": "2024-01-01", "station_id": 1,
            "camera_id": 2, "sequence_id": 7, "external_id": "E1",
            "viewpoint": viewpoint,
        })

    @pytest.fixture(autouse=True)
    def _loc(self):
        loc = {"station_name": "Stn", "survey_name": "Srv",
               "region_name": "Reg", "camera_name": "Cam"}
        with patch(f"{QUERY}.fetch_station_names_from_id", return_value=loc):
            yield

    def test_location_fields_resolved(self, qc):
        info = qc.roi_metadata(self._roi())
        assert info["Name"] == "Bob"
        assert info["Station"] == "Stn"
        assert info["Survey"] == "Srv"
        assert info["Region"] == "Reg"
        assert info["Camera"] == "Cam"

    @pytest.mark.parametrize("value, expected", [
        (0, "Left"), (2, "Right"), (np.nan, "None"), (9, "Unknown"),
    ])
    def test_viewpoint_text(self, qc, value, expected):
        assert qc.roi_metadata(self._roi(value))["Viewpoint"] == expected


# ---------------------------------------------------------------------------
# finish_calculating
# ---------------------------------------------------------------------------

class TestFinishCalculating:
    def test_cancelled_does_nothing(self, qc):
        qc._stop_requested = True
        qc.ranked_sequences = [_fake_match(1, [(12, 0.1)], [10])]
        qc.save_knn_cache = MagicMock()
        qc.finalize = MagicMock()
        qc.finish_calculating()
        qc.save_knn_cache.assert_not_called()
        qc.finalize.assert_not_called()
        assert qc._raw_ranked is None

    def test_serializes_saves_and_finalizes(self, qc):
        qc.ranked_sequences = [_fake_match(1, [(12, 0.1)], [10])]
        qc.save_knn_cache = MagicMock()
        qc.finalize = MagicMock()
        qc.finish_calculating()
        assert qc._raw_ranked[0]["sequence_id"] == 1
        qc.save_knn_cache.assert_called_once_with(qc._raw_ranked)
        qc.finalize.assert_called_once()

    def test_no_results_skips_cache_but_still_finalizes(self, qc):
        qc.ranked_sequences = []
        qc.save_knn_cache = MagicMock()
        qc.finalize = MagicMock()
        qc.finish_calculating()
        assert qc._raw_ranked == []
        qc.save_knn_cache.assert_not_called()
        qc.finalize.assert_called_once()


# ---------------------------------------------------------------------------
# finalize (filter + narrow), after cache load OR compute
# ---------------------------------------------------------------------------

class TestFinalize:
    def test_cancelled_emits_nothing(self, qc_raw):
        qc_raw._stop_requested = True
        qc_raw._raw_ranked = [_raw(1, [10], [(11, 0.1)])]
        emitted = _collect(qc_raw.thread_signal)
        qc_raw.finalize()
        assert emitted == []

    def test_no_raw_results_emits_false(self, qc_raw):
        emitted = _collect(qc_raw.thread_signal)
        qc_raw.finalize()
        assert emitted == [False]
        assert qc_raw.n_queries == 0

    def test_emits_true_and_builds_sequences(self, qc_raw, fake_match_object):
        qc_raw.set_filter(None, None)
        qc_raw._raw_ranked = [_raw(1, [10, 11], [(12, 0.1), (13, 0.3)])]
        emitted = _collect(qc_raw.thread_signal)
        qc_raw.finalize()
        assert emitted == [True]
        assert qc_raw.n_queries == 1
        assert qc_raw.filter_matched is True
        assert qc_raw.ranked_sequences[0].sequence_id == 1
        assert len(qc_raw.data) == 4            # filter ran

    def test_filter_narrows_neighbors(self, qc_raw, fake_match_object):
        """Station 1 keeps ids 10/11 only; neighbor 12 is filtered away."""
        qc_raw.set_filter(_filter_dict(station=1), {1: "A"})
        qc_raw._raw_ranked = [_raw(1, [10], [(11, 0.1), (12, 0.2)])]
        emitted = _collect(qc_raw.thread_signal)
        qc_raw.finalize()
        assert emitted == [True]
        assert qc_raw.ranked_sequences[0].filtered_neighbors == [(11, 0.1)]

    def test_empty_valid_stations_emits_false(self, qc_raw, fake_match_object):
        qc_raw.set_filter(_filter_dict(), {})
        qc_raw._raw_ranked = [_raw(1, [10], [(11, 0.1)])]
        emitted = _collect(qc_raw.thread_signal)
        qc_raw.finalize()
        assert emitted == [False]
        assert qc_raw.filter_matched is False
        assert qc_raw.ranked_sequences == []

    def test_all_sequences_filtered_out_emits_false(self, qc_raw, fake_match_object):
        qc_raw.set_filter(_filter_dict(station=2), {2: "B"})
        qc_raw._raw_ranked = [_raw(1, [10, 11], [(12, 0.1)])]   # query is station 1
        emitted = _collect(qc_raw.thread_signal)
        qc_raw.finalize()
        assert emitted == [False]
        assert qc_raw.filter_matched is False
        assert qc_raw.n_queries == 0

    def test_cache_without_headroom_recomputes(self, qc_raw, fake_match_object):
        qc_raw.set_filter(_filter_dict(station=1), {1: "A"})
        qc_raw._from_cache = True
        qc_raw._raw_ranked = [_raw(1, [10], [(11, 0.1), (12, 0.2), (13, 0.3)], truncated=True)]
        qc_raw.calculate_neighbors = MagicMock()
        emitted = _collect(qc_raw.thread_signal)
        qc_raw.finalize()
        qc_raw.calculate_neighbors.assert_called_once()
        assert emitted == []

    def test_fresh_compute_never_recomputes(self, qc_raw, fake_match_object):
        """Same data as above but from a fresh compute: accept fewer than k, no loop."""
        qc_raw.set_filter(_filter_dict(station=1), {1: "A"})
        qc_raw._from_cache = False
        qc_raw._raw_ranked = [_raw(1, [10], [(11, 0.1), (12, 0.2), (13, 0.3)], truncated=True)]
        qc_raw.calculate_neighbors = MagicMock()
        emitted = _collect(qc_raw.thread_signal)
        qc_raw.finalize()
        qc_raw.calculate_neighbors.assert_not_called()
        assert emitted == [True]


# ---------------------------------------------------------------------------
# _restrict_to_data
# ---------------------------------------------------------------------------

class TestRestrictToData:
    @pytest.fixture(autouse=True)
    def _setup(self, qc, fake_match_object):
        self.qc = qc
        qc.data = _sample_roi_df()      # all four rows
        qc.k = 3

    def test_keeps_everything_when_unfiltered(self):
        out = self.qc._restrict_to_data([_raw(1, [10, 11], [(12, 0.1), (13, 0.3)])], strict=False)
        assert len(out) == 1
        mo = out[0]
        assert mo.sequence_id == 1
        assert mo.filtered_neighbors == [(12, 0.1), (13, 0.3)]
        assert mo.og_ranked_query_rids == [10, 11]
        assert mo.ranked_matches == [(12, 0.1), (13, 0.3)]

    def test_query_and_match_data_have_id_column(self):
        """MatchObject reads data['id'] as a column, so the index must be reset."""
        mo = self.qc._restrict_to_data([_raw(1, [10, 11], [(12, 0.1), (13, 0.3)])], strict=False)[0]
        assert "id" in mo.query_data.columns
        assert list(mo.query_data["id"]) == [10, 11]
        assert list(mo.match_data["id"]) == [12, 13]

    def test_drops_sequence_whose_queries_are_filtered_out(self):
        self.qc.data = self.qc.data.loc[[12, 13]]
        out = self.qc._restrict_to_data([_raw(1, [10, 11], [(12, 0.1)])], strict=False)
        assert out == []

    def test_removes_filtered_neighbors(self):
        self.qc.data = self.qc.data.loc[[10, 11, 12]]
        mo = self.qc._restrict_to_data([_raw(1, [10], [(12, 0.1), (13, 0.3)])], strict=False)[0]
        assert mo.filtered_neighbors == [(12, 0.1)]
        assert mo.ranked_matches == [(12, 0.1)]

    def test_removes_filtered_query_rois(self):
        self.qc.data = self.qc.data.loc[[10, 12]]
        mo = self.qc._restrict_to_data([_raw(1, [10, 11], [(12, 0.1)])], strict=False)[0]
        assert mo.og_ranked_query_rids == [10]
        assert list(mo.query_data["id"]) == [10]

    def test_truncates_to_k(self):
        self.qc.k = 2
        neighbors = [(11, 0.1), (12, 0.2), (13, 0.3)]
        mo = self.qc._restrict_to_data([_raw(1, [10], neighbors)], strict=False)[0]
        assert mo.filtered_neighbors == [(11, 0.1), (12, 0.2)]
        assert len(mo.ranked_matches) == 2

    def test_drops_sequence_with_no_neighbors_left(self):
        self.qc.data = self.qc.data.loc[[10, 11]]
        out = self.qc._restrict_to_data([_raw(1, [10], [(12, 0.1)])], strict=False)
        assert out == []

    def test_strict_truncated_cache_without_headroom_returns_none(self):
        self.qc.data = self.qc.data.loc[[10, 11]]
        raw = [_raw(1, [10], [(11, 0.1), (12, 0.2), (13, 0.3)], truncated=True)]
        assert self.qc._restrict_to_data(raw, strict=True) is None

    def test_strict_but_not_truncated_is_fine(self):
        self.qc.data = self.qc.data.loc[[10, 11]]
        raw = [_raw(1, [10], [(11, 0.1), (12, 0.2)], truncated=False)]
        out = self.qc._restrict_to_data(raw, strict=True)
        assert out is not None and len(out) == 1

    def test_non_strict_accepts_short_result(self):
        self.qc.data = self.qc.data.loc[[10, 11]]
        raw = [_raw(1, [10], [(11, 0.1), (12, 0.2), (13, 0.3)], truncated=True)]
        out = self.qc._restrict_to_data(raw, strict=False)
        assert out[0].filtered_neighbors == [(11, 0.1)]

    def test_json_lists_become_tuples(self):
        """Cache round-trips tuples as lists; output must be tuples again."""
        raw = [_raw(1, [10], [[11, 0.1]])]
        mo = self.qc._restrict_to_data(raw, strict=False)[0]
        assert mo.filtered_neighbors == [(11, 0.1)]
        assert mo.ranked_matches == [(11, 0.1)]
        assert all(isinstance(m, tuple) for m in mo.ranked_matches)


# ---------------------------------------------------------------------------
# KNN cache
# ---------------------------------------------------------------------------

class TestKnnCache:
    @staticmethod
    def _serialized():
        return [_raw(1, [10, 11], [(12, 0.1), (13, 0.3)])]

    def test_serialize_marks_truncated(self, qc):
        full = [(i, 0.1 * i) for i in range(qc.k_cache)]
        out = qc._serialize_ranked_sequences([
            _fake_match(1, full, [10]),
            _fake_match(2, full[:2], [11]),
        ])
        assert out[0]["truncated"] is True
        assert out[1]["truncated"] is False

    def test_serialize_keeps_ids_and_distances_only(self, qc):
        out = qc._serialize_ranked_sequences([_fake_match(1, [(12, 0.1)], [10])])[0]
        assert set(out) == {"sequence_id", "neighbors", "truncated",
                            "og_ranked_query_rids", "og_ranked_matches"}
        assert out["og_ranked_matches"] == [(12, 0.1)]

    def test_roundtrip(self, qc_raw):
        qc_raw.save_knn_cache(self._serialized())
        assert qc_raw.CACHE_PATH.exists()
        assert qc_raw.load_knn_cache() is True
        assert qc_raw._from_cache is True
        assert qc_raw._raw_ranked[0]["sequence_id"] == 1
        assert qc_raw._raw_ranked[0]["neighbors"] == [[12, 0.1], [13, 0.3]]

    def test_saved_payload_metadata(self, qc_raw):
        qc_raw.save_knn_cache(self._serialized())
        payload = json.loads(qc_raw.CACHE_PATH.read_text())
        assert payload["n_raw"] == 4
        assert payload["k_cache"] == qc_raw.k_cache
        assert payload["metric"] == "cosine"
        assert payload["threshold"] == 50
        assert "timestamp" in payload

    def test_save_leaves_no_tmp_file(self, qc_raw, tmp_path):
        qc_raw.save_knn_cache(self._serialized())
        assert list(tmp_path.glob("*.tmp")) == []

    def test_save_handles_numpy_values(self, qc_raw):
        serialized = [_raw(np.int64(1), [np.int64(10)], [(np.int64(12), np.float32(0.25))])]
        qc_raw.save_knn_cache(serialized)
        assert qc_raw.load_knn_cache() is True
        assert qc_raw._raw_ranked[0]["neighbors"] == [[12, 0.25]]

    def test_save_failure_is_logged_not_raised(self, qc_raw, tmp_path):
        qc_raw.CACHE_PATH = tmp_path / "missing_dir" / "knn_cache.json"
        qc_raw.save_knn_cache(self._serialized())
        qc_raw.logger.error.assert_called_once()
        assert list(tmp_path.rglob("*.tmp")) == []

    def test_load_without_file(self, qc_raw):
        assert qc_raw.load_knn_cache() is False

    @pytest.mark.parametrize("mutate", [
        lambda qc: setattr(qc, "cache_timeout", -1),
        lambda qc: setattr(qc, "metric", "euclidean"),
        lambda qc: setattr(qc, "threshold", 99),
        lambda qc: setattr(qc, "k", qc.k_cache + 1),
        lambda qc: setattr(qc, "data_raw", qc.data_raw.iloc[:2]),
    ], ids=["expired", "metric_changed", "threshold_changed",
            "k_exceeds_cached_k", "data_changed"])
    def test_load_rejects_stale_cache(self, qc_raw, mutate):
        qc_raw.save_knn_cache(self._serialized())
        mutate(qc_raw)
        assert qc_raw.load_knn_cache() is False
        assert qc_raw._raw_ranked is None

    def test_load_corrupt_file(self, qc_raw):
        qc_raw.CACHE_PATH.write_text("{not json")
        assert qc_raw.load_knn_cache() is False
        qc_raw.logger.error.assert_called_once()

    def test_cache_is_independent_of_filter(self, qc_raw):
        """The cache stores unfiltered results, so a changed filter must not invalidate it."""
        qc_raw.save_knn_cache(self._serialized())
        qc_raw.set_filter(_filter_dict(station=1), {1: "A"})
        assert qc_raw.load_knn_cache() is True

    def test_clear_removes_file(self, qc_raw):
        qc_raw.save_knn_cache(self._serialized())
        qc_raw.clear_knn_cache()
        assert not qc_raw.CACHE_PATH.exists()

    def test_clear_without_file_is_safe(self, qc_raw):
        qc_raw.clear_knn_cache()

    def test_json_default_rejects_unknown_types(self, qc):
        with pytest.raises(TypeError):
            qc._json_default(object())

    def test_json_default_numpy(self, qc):
        assert qc._json_default(np.int64(3)) == 3
        assert qc._json_default(np.float32(0.5)) == 0.5
        assert qc._json_default(np.array([1, 2])) == [1, 2]


# ---------------------------------------------------------------------------
# Local data updates
# ---------------------------------------------------------------------------

class TestUpdateRoiIndex:
    def test_updates_both_frames(self, qc):
        qc.data_raw = _sample_roi_df()
        qc.data = qc.data_raw.copy()
        qc._update_roi_index({10: {"individual_id": 555, "reviewed": 1}})
        assert qc.data.loc[10, "individual_id"] == 555
        assert qc.data_raw.loc[10, "individual_id"] == 555
        assert qc.data.loc[10, "reviewed"] == 1

    def test_skips_ids_missing_from_a_frame(self, qc):
        """Filtered-out ROIs must not be appended to self.data as NaN rows."""
        qc.data_raw = _sample_roi_df()
        qc.data = qc.data_raw.loc[[10, 11]].copy()
        qc._update_roi_index({13: {"individual_id": 555}})
        assert len(qc.data) == 2
        assert qc.data_raw.loc[13, "individual_id"] == 555


class TestUpdateSequencesInPlace:
    @staticmethod
    def _fresh(qc, seq):
        df = qc.data_raw[qc.data_raw["sequence_id"] == seq].copy()
        df["individual_id"] = 999
        return df

    def test_fallback_when_ids_missing(self, qc):
        qc.load_data = MagicMock()
        qc.filter = MagicMock()
        qc.update_sequences_in_place(None, 2)
        qc.load_data.assert_called_once()
        qc.filter.assert_called_once()

    def test_fallback_when_fetch_is_empty(self, qc, mock_db_roi):
        qc.data_raw = _sample_roi_df()
        qc.data = qc.data_raw.copy()
        mock_db_roi.fetch_roi_media.side_effect = [pd.DataFrame(), self._fresh(qc, 2)]
        qc.load_data = MagicMock()
        qc.filter = MagicMock()
        qc.update_sequences_in_place(1, 2)
        qc.load_data.assert_called_once()
        qc.filter.assert_called_once()

    def test_replaces_rows_in_data_and_data_raw(self, qc, mock_db_roi):
        qc.data_raw = _sample_roi_df()
        qc.data = qc.data_raw.copy()
        mock_db_roi.fetch_roi_media.side_effect = [self._fresh(qc, 1), self._fresh(qc, 2)]
        qc.update_sequences_in_place(1, 2)

        calls = mock_db_roi.fetch_roi_media.call_args_list
        assert calls[0].kwargs == {"sequence_ids": [1]}
        assert calls[1].kwargs == {"sequence_ids": [2]}
        for df in (qc.data, qc.data_raw):
            assert len(df) == 4
            assert all(df.loc[[10, 11, 12], "individual_id"] == 999)
            assert df.loc[13, "individual_id"] == 200
        assert set(qc._seq_index) == {1, 2, 3}

    def test_same_sequence_on_both_sides_has_no_duplicates(self, qc, mock_db_roi):
        qc.data_raw = _sample_roi_df()
        qc.data = qc.data_raw.copy()
        mock_db_roi.fetch_roi_media.side_effect = [self._fresh(qc, 1), self._fresh(qc, 1)]
        qc.update_sequences_in_place(1, 1)
        assert qc.data.index.is_unique
        assert qc.data_raw.index.is_unique
        assert len(qc.data) == 4


class TestUpdatePartialSequences:
    def test_empty_list_is_noop(self, qc, mock_db_roi):
        qc.data = _sample_roi_df()
        qc.update_partial_sequences([])
        mock_db_roi.fetch_roi_media.assert_not_called()
        assert len(qc.data) == 4

    def test_replaces_rows(self, qc, mock_db_roi):
        qc.data_raw = _sample_roi_df()
        qc.data = qc.data_raw.copy()
        fresh = qc.data_raw[qc.data_raw["sequence_id"] == 1].copy()
        fresh["individual_id"] = 999
        mock_db_roi.fetch_roi_media.return_value = fresh
        qc.update_partial_sequences([1])
        assert len(qc.data) == 4
        assert all(qc.data.loc[[10, 11], "individual_id"] == 999)


# ---------------------------------------------------------------------------
# Match actions (DB writes + local updates)
# ---------------------------------------------------------------------------

class TestMatchActions:
    @pytest.fixture(autouse=True)
    def _setup(self, qc):
        """ids 10,11 -> iid 100 (seq 1); 12 -> none (seq 2); 13,14 -> iid 200 (seq 3 / 4)."""
        base = _sample_roi_df()
        extra = base.loc[[13]].rename(index={13: 14})
        extra["sequence_id"] = 4
        df = pd.concat([base, extra])
        df.index.name = "id"

        self.qc = qc
        qc.data_raw = df
        qc.data = df.copy()
        qc._build_seq_indices()

    def test_new_iid(self):
        qc = self.qc
        qc.current_query_rois = [10, 11]
        qc.current_match_rid = 13
        qc.new_iid(500)

        table, updates = qc.mpDB.batch_edit.call_args.args
        assert table == "roi"
        assert set(updates) == {10, 11, 13}
        assert all(u == {"individual_id": 500, "reviewed": 1} for u in updates.values())
        assert qc.mpDB.batch_edit.call_args.kwargs == {"quiet": True}
        assert qc.data.loc[13, "individual_id"] == 500

    def test_merge_keeps_lowest_id_and_absorbs_other_individual(self):
        qc = self.qc
        qc.current_query_rid = 10       # iid 100, seq 1
        qc.current_match_rid = 13       # iid 200, seq 3
        qc.current_match_object = SimpleNamespace(sequence_id=1)
        qc.merge()

        table, updates = qc.mpDB.batch_edit.call_args.args
        assert table == "roi"
        # both sequences + every other ROI of the absorbed individual (14)
        assert set(updates) == {10, 11, 13, 14}
        assert all(type(k) is int for k in updates)
        assert all(u == {"individual_id": 100, "reviewed": 1} for u in updates.values())
        assert qc.mpDB.batch_edit.call_args.kwargs == {"quiet": True}
        assert qc.data.loc[14, "individual_id"] == 100
        assert qc.data_raw.loc[13, "individual_id"] == 100

    def test_merge_keeps_lowest_id_when_query_is_higher(self):
        qc = self.qc
        qc.current_query_rid = 13       # iid 200
        qc.current_match_rid = 10       # iid 100
        qc.current_match_object = SimpleNamespace(sequence_id=3)
        qc.merge()
        updates = qc.mpDB.batch_edit.call_args.args[1]
        assert all(u["individual_id"] == 100 for u in updates.values())
        assert set(updates) == {10, 11, 13, 14}

    def test_merge_named_match_into_unnamed_query(self):
        qc = self.qc
        qc.current_query_rid = 12       # unnamed, seq 2
        qc.current_match_rid = 10       # iid 100, seq 1
        qc.current_match_object = SimpleNamespace(sequence_id=2)
        qc.merge()
        updates = qc.mpDB.batch_edit.call_args.args[1]
        assert set(updates) == {12, 10, 11}
        assert all(u["individual_id"] == 100 for u in updates.values())

    def test_merge_treats_nan_as_unnamed(self):
        qc = self.qc
        qc.data.loc[12, "individual_id"] = np.nan
        qc.current_query_rid = 12
        qc.current_match_rid = 10
        qc.current_match_object = SimpleNamespace(sequence_id=2)
        qc.merge()
        updates = qc.mpDB.batch_edit.call_args.args[1]
        assert all(u["individual_id"] == 100 for u in updates.values())

    def test_merge_does_nothing_when_both_unnamed(self):
        qc = self.qc
        qc.current_query_rid = 12
        qc.current_match_rid = 12
        qc.current_match_object = SimpleNamespace(sequence_id=2)
        qc.merge()
        qc.mpDB.batch_edit.assert_not_called()

    def test_unmatch(self):
        qc = self.qc
        qc.current_query_rid = 10
        qc.unmatch()
        qc.mpDB.edit_row.assert_called_once_with(
            "roi", 10, {"individual_id": None, "reviewed": 0},
            allow_none=True, quiet=True)
        assert pd.isna(qc.data.loc[10, "individual_id"])
        assert qc.data.loc[10, "reviewed"] == 0


# ---------------------------------------------------------------------------
# Favorites
# ---------------------------------------------------------------------------

class TestFavorites:
    @pytest.fixture(autouse=True)
    def _setup(self, qc):
        self.qc = qc
        qc.data_raw = _sample_roi_df()          # only id 11 is a favorite
        self.knn = MagicMock()
        self.knn.sequence_id = 1
        self.knn.query_data = pd.DataFrame({"id": [10]})
        self.knn.get_ranked_matches.return_value = [(12, 0.1)]
        qc.current_match_object = self.knn

    def test_toggle_on_and_off(self):
        qc = self.qc
        qc.mpDB.batch_calculate_similarity.return_value = {11: 0.8}
        with patch(f"{QUERY}.FavoriteMatchObject") as fav_cls:
            fav = fav_cls.return_value
            fav.get_ranked_matches.return_value = [(11, 0.2)]

            qc.set_match_favorites(True)
            assert qc.current_match_object is fav
            assert qc.knn_match_object is self.knn
            assert qc.current_match_rois == [11]
            qc.mpDB.batch_calculate_similarity.assert_called_once_with(10, [11])
            assert fav_cls.call_args.args[0] == 1
            assert fav_cls.call_args.args[1] == [(11, pytest.approx(0.2))]

            qc.set_match_favorites(False)
            assert qc.current_match_object is self.knn
            assert qc.favorite_match_object is None
            assert qc.knn_match_object is None
            assert qc._similarities_cache == {}
            assert qc.current_match_rois == [12]

    def test_no_favorites_leaves_match_object_alone(self):
        qc = self.qc
        qc.data_raw["favorite"] = 0
        qc.set_match_favorites(True)
        assert qc.current_match_object is self.knn
        qc.mpDB.batch_calculate_similarity.assert_not_called()
