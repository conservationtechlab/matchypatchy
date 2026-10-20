"""Tests for MatchEmbeddingThread in match_thread.py."""
import pandas as pd

from matchypatchy.threads.match_thread import MatchEmbeddingThread


class FakeDB:
    """batch_knn stand-in returning fixed neighbors: {roi_id: [(neighbor_id, distance), ...]}"""
    def __init__(self, neighbors):
        self.neighbors = neighbors

    def batch_knn(self, query_ids, k=3):
        return {q: ([n for n, _ in self.neighbors[q]], [d for _, d in self.neighbors[q]])
                for q in query_ids if q in self.neighbors}


def _rois(rows):
    """roi_media frame with the columns MatchEmbeddingThread drops and reads"""
    df = pd.DataFrame(rows, columns=["id", "sequence_id", "individual_id", "viewpoint"])
    for col in ["frame", "bbox_x", "bbox_y", "bbox_w", "bbox_h", "comment", "name", "sex"]:
        df[col] = None
    df["favorite"] = 0
    return df.set_index("id", drop=False).rename_axis(None)


def _run(rois, sequences, neighbors):
    thread = MatchEmbeddingThread(FakeDB(neighbors), rois, sequences)
    results = []
    thread.ranked_queries_return.connect(results.append)
    thread.run()
    return results[0]


def test_neighbors_without_a_roi_are_dropped():
    # roi 99 has an embedding but its roi was deleted with its station
    rois = _rois([(1, 10, None, None), (2, 20, None, None)])
    sequences = {10: [1], 20: [2]}
    neighbors = {1: [(1, 0.0), (99, 0.05), (2, 0.1)],
                 2: [(2, 0.0), (99, 0.05), (1, 0.1)]}

    pairs = _run(rois, sequences, neighbors)

    matched = {roi for pair in pairs for roi, _ in pair.neighbors}
    assert 99 not in matched
    assert matched == {1, 2}
