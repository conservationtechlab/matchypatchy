"""Tests for matchypatchy thread workers in animl_thread.py."""
import sys
import types
from types import SimpleNamespace

import pandas as pd


if "animl" not in sys.modules:
    animl_stub = types.ModuleType("animl")
    animl_stub.build_file_manifest = lambda *args, **kwargs: pd.DataFrame()
    animl_stub.load_detector = lambda *args, **kwargs: None
    animl_stub.get_images = lambda *args, **kwargs: pd.DataFrame()
    animl_stub.get_videos = lambda *args, **kwargs: pd.DataFrame()
    animl_stub.extract_frames = lambda videos, **kwargs: videos
    animl_stub.detect = lambda *args, **kwargs: pd.DataFrame()
    animl_stub.parse_detections = lambda detections, **kwargs: detections
    animl_stub.get_animals = lambda detections: detections
    sys.modules["animl"] = animl_stub

from matchypatchy.threads import animl_thread


class SignalSpy:
    def __init__(self):
        self.calls = []

    def emit(self, *args):
        self.calls.append(args)


class TestBuildManifestThread:
    def test_calls_build_file_manifest_and_emits_manifest(self, monkeypatch):
        expected = pd.DataFrame([{"filepath": "/x.jpg"}])
        calls = []

        def _build_file_manifest(directory, exif, data_timezone):
            calls.append((directory, exif, data_timezone))
            return expected

        monkeypatch.setattr(animl_thread.animl, "build_file_manifest", _build_file_manifest)
        thread = animl_thread.BuildManifestThread("/data", "UTC")
        thread.manifest = SignalSpy()

        thread.run()

        assert calls == [("/data", True, "UTC")]
        assert len(thread.manifest.calls) == 1
        assert thread.manifest.calls[0][0].equals(expected)


class TestVerifyNewBaseDirsThread:
    def test_compares_hashes_and_emits_missing_lists(self, tmp_db, monkeypatch):
        db, _ = tmp_db
        station_id = db.add_station("S", 1.0, 2.0, 1)
        base_id = db.add_upload("/old")
        db.add_media(base_id, "a.jpg", "hash-a", ".jpg", "2024-01-01 00:00:00", station_id)
        db.add_media(base_id, "b.jpg", "hash-b", ".jpg", "2024-01-01 00:00:01", station_id)

        parent = SimpleNamespace(mpDB=db, base_dirs=[], updates=[(base_id, "/new")])

        monkeypatch.setattr(
            animl_thread.animl,
            "build_file_manifest",
            lambda *_args, **_kwargs: pd.DataFrame({"filepath": ["/new/a.jpg", "/new/c.jpg"]}),
        )
        monkeypatch.setattr(
            animl_thread,
            "get_sha256",
            lambda filepath: {
                "/new/a.jpg": "hash-a",
                "/new/c.jpg": "hash-c",
            }[filepath],
        )

        thread = animl_thread.VerifyNewBaseDirsThread(parent)
        thread.not_in_db = SignalSpy()
        thread.not_in_new_directory = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False
        thread.run()

        assert thread.not_in_db.calls == [([["/new/c.jpg"]],)]
        assert thread.not_in_new_directory.calls == [([["b.jpg"]],)]
        assert len(thread.finished.calls) == 1

    def test_interruption_emits_nothing(self, tmp_db):
        db, _ = tmp_db
        parent = SimpleNamespace(mpDB=db, base_dirs=[], updates=[(1, "/new")])
        thread = animl_thread.VerifyNewBaseDirsThread(parent)
        thread.not_in_db = SignalSpy()
        thread.not_in_new_directory = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: True

        thread.run()

        assert thread.not_in_db.calls == []
        assert thread.not_in_new_directory.calls == []
        assert thread.finished.calls == []
