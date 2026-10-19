"""
Unit tests for matchypatchy.gui.manual_query.ManualQueryContainer distances
"""
import math
from unittest.mock import MagicMock, patch

import pandas as pd


def _make_mqc(similarities=None):
    """ManualQueryContainer with a mocked parent; similarities maps (id1, id2) -> similarity"""
    from matchypatchy.gui.manual_query import ManualQueryContainer

    parent = MagicMock()
    similarities = similarities or {}
    parent.mpDB.calculate_similarity.side_effect = lambda a, b: similarities.get((a, b))
    with patch("matchypatchy.gui.manual_query.load_model", return_value={}):
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
