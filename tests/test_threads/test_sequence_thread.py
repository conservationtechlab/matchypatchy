"""Tests for SequenceThread in sequence_thread.py."""
from types import SimpleNamespace

import pandas as pd

from matchypatchy.threads import sequence_thread
from matchypatchy.threads.sequence_thread import SequenceThread


class FakeDB:
    def __init__(self):
        self.next_sequence = 0
        self.sequence_of = {}

    def add_sequence(self):
        self.next_sequence += 1
        return self.next_sequence

    def edit_row(self, table, row_id, changes):
        self.sequence_of[row_id] = changes["sequence_id"]


def _thread(monkeypatch, rows, flag=True):
    media = pd.DataFrame(rows, columns=["id", "station_id", "camera_id", "timestamp", "sequence_id"])
    monkeypatch.setattr(sequence_thread, "fetch_media", lambda _db: media.copy())
    cfg = SimpleNamespace(SEQUENCE_DURATION=60, SEQUENCE_N=10)
    return SequenceThread(FakeDB(), cfg, flag)


def test_images_without_a_camera_share_a_sequence(monkeypatch):
    # null camera_id comes back from the database as NaN in a float column
    thread = _thread(monkeypatch, [
        (1, 1, float("nan"), "2024-01-01 00:00:00", None),
        (2, 1, float("nan"), "2024-01-01 00:00:10", None),
        (3, 1, float("nan"), "2024-01-01 00:00:20", None),
        (4, 2, 7.0, "2024-01-01 00:00:00", None),
    ])
    thread.run()

    sequence_of = thread.mpDB.sequence_of
    assert sequence_of[1] == sequence_of[2] == sequence_of[3]
    assert sequence_of[4] != sequence_of[1]
