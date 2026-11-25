"""Tests for SequenceThread in sequence_thread.py."""
from types import SimpleNamespace

import pandas as pd

from matchypatchy.threads import sequence_thread
from matchypatchy.threads.sequence_thread import SequenceThread


class FakeDB:
    def __init__(self):
        self.next_sequence = 0
        self.sequence_of = {}
        self.on_edit = None

    def add_sequence(self):
        self.next_sequence += 1
        return self.next_sequence

    def edit_row(self, table, row_id, changes):
        self.sequence_of[row_id] = changes["sequence_id"]
        if self.on_edit:
            self.on_edit()


def _thread(monkeypatch, rows, flag=True):
    media = pd.DataFrame(rows, columns=["id", "station_id", "camera_id", "timestamp", "sequence_id"])
    monkeypatch.setattr(sequence_thread, "fetch_media", lambda _db: media.copy())
    cfg = SimpleNamespace(SEQUENCE_DURATION=60)
    return SequenceThread(FakeDB(), cfg, flag)


def test_cameras_at_a_station_share_sequences_by_time(monkeypatch):
    # camera is not part of the sequence calculation, including a missing camera
    # (null camera_id comes back from the database as NaN in a float column)
    thread = _thread(monkeypatch, [
        (1, 1, 7.0, "2024-01-01 00:00:00", None),
        (2, 1, 8.0, "2024-01-01 00:00:10", None),
        (3, 1, float("nan"), "2024-01-01 00:00:20", None),
        (4, 2, 7.0, "2024-01-01 00:00:05", None),
    ])
    thread.run()

    sequence_of = thread.mpDB.sequence_of
    assert sequence_of[1] == sequence_of[2] == sequence_of[3]
    assert sequence_of[4] != sequence_of[1]   # other station


def test_one_cameras_later_images_do_not_absorb_anothers_earlier_ones(monkeypatch):
    # camera 7 at 0s and 1000s, camera 8 at 10s: 8's image belongs with 7's first,
    # which needs media in time order across cameras, not camera by camera
    thread = _thread(monkeypatch, [
        (1, 1, 7.0, "2024-01-01 00:00:00", None),
        (2, 1, 7.0, "2024-01-01 00:16:40", None),
        (3, 1, 8.0, "2024-01-01 00:00:10", None),
    ])
    thread.run()

    sequence_of = thread.mpDB.sequence_of
    assert sequence_of[1] == sequence_of[3]
    assert sequence_of[2] != sequence_of[1]


def test_cancel_stops_writing_sequences(monkeypatch):
    # two sequences, an hour apart
    thread = _thread(monkeypatch, [
        (1, 1, 1, "2024-01-01 00:00:00", 5),
        (2, 1, 1, "2024-01-01 01:00:00", 5),
    ])
    done = []
    thread.done.connect(lambda: done.append(True))
    # cancel while the first sequence is being written
    thread.mpDB.on_edit = thread.requestInterruption
    thread.run()

    assert list(thread.mpDB.sequence_of) == [1]
    assert done == []


def test_media_is_loaded_in_run_not_on_the_gui_thread(monkeypatch):
    fetches = []
    monkeypatch.setattr(sequence_thread, "fetch_media", lambda _db: fetches.append(1))
    cfg = SimpleNamespace(SEQUENCE_DURATION=60)

    SequenceThread(FakeDB(), cfg, True)

    assert fetches == []
