"""
Unit tests for matchypatchy.gui.query_manual.ManualQueryContainer distances
"""
import math
from unittest.mock import MagicMock, patch

import pandas as pd


def _make_mqc(similarities=None):
    """ManualQueryContainer with a mocked parent; similarities maps (id1, id2) -> similarity"""
    from matchypatchy.algorithm.query_manual import ManualQueryContainer

    parent = MagicMock()
    similarities = similarities or {}
    parent.project.db.calculate_similarity.side_effect = lambda a, b: similarities.get((a, b))
    with patch("matchypatchy.algorithm.query_manual.load_model", return_value={}):
        mqc = ManualQueryContainer(parent, selected_ids=[])
    return mqc


class TestCalculateNeighbors:
    def test_distances_from_similarity(self):
        mqc = _make_mqc({(1, 2): 0.75})
        mqc.data = pd.DataFrame(index=[1, 2])
        mqc.calculate_neighbors()
        assert mqc.pair_table["distance"].tolist() == [0.25]

    def test_missing_embedding_has_no_distance(self):
        mqc = _make_mqc({(1, 2): None})
        mqc.data = pd.DataFrame(index=[1, 2])
        mqc.calculate_neighbors()  # should not raise on 1 - None
        assert mqc.pair_table["distance"].tolist() == [None]


class TestCurrentDistance:
    def test_stored_pair(self):
        mqc = _make_mqc()
        mqc.pair_table = pd.DataFrame([{"id1": 1, "id2": 2, "distance": 0.25}])
        mqc.current_query_rid, mqc.current_match_rid = 2, 1
        assert mqc.current_distance() == 0.25

    def test_unknown_pair_is_none(self):
        """No stored pair must not read as distance 0 (a perfect match)"""
        mqc = _make_mqc()
        mqc.pair_table = pd.DataFrame([{"id1": 1, "id2": 2, "distance": 0.25}])
        mqc.current_query_rid, mqc.current_match_rid = 1, 3
        assert mqc.current_distance() is None

    def test_missing_embedding_pair_is_not_finite(self):
        mqc = _make_mqc()
        mqc.pair_table = pd.DataFrame([{"id1": 1, "id2": 2, "distance": None},
                                       {"id1": 1, "id2": 3, "distance": 0.5}])
        mqc.current_query_rid, mqc.current_match_rid = 1, 2
        distance = mqc.current_distance()
        assert distance is None or not math.isfinite(distance)


class TestSingleRoi:
    def test_single_roi_pair_table_is_safe(self):
        mqc = _make_mqc()
        mqc.data = pd.DataFrame(index=[1])
        mqc.calculate_neighbors()
        assert list(mqc.pair_table.columns) == ["id1", "id2", "distance"]
        mqc.current_query_rid, mqc.current_match_rid = 1, 1
        assert mqc.current_distance() is None

    def test_filter_needs_two_rois(self):
        """One roi would be both query and match, so there is nothing to compare"""
        mqc = _make_mqc()
        mqc.data_raw = pd.DataFrame({"station_id": [1, 2]}, index=[1, 2])
        stations = {1: "A", 2: "B"}
        one = {"active_region": (0,), "active_survey": (0,), "active_station": (1,)}
        both = {"active_region": (0,), "active_survey": (0,), "active_station": (0,)}
        assert mqc.filter(one, stations) is False
        assert mqc.filter(both, stations) is True
