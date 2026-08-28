"""Tests for matchypatchy thread workers in animl_thread.py."""
import sys
import types
from pathlib import Path
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


def _empty_roi_media():
    return pd.DataFrame(columns=["id", "media_id", "bbox_x", "bbox_y", "bbox_w", "bbox_h", "filepath", "ext"])


class FakeDB:
    def __init__(self):
        self.add_roi_calls = []
        self.add_thumbnail_calls = []
        self.edit_row_calls = []
        self.media_rows = []
        self.media_columns = [
            "id",
            "base_dir_id",
            "relative_path",
            "sha256",
            "ext",
            "timestamp",
            "station_id",
            "camera_id",
            "sequence_id",
            "external_id",
            "comment",
            "filepath",
        ]

    def get_media_with_filepath(self, row_cond=None):
        return self.media_rows, self.media_columns

    def add_roi(self, *args, **kwargs):
        self.add_roi_calls.append((args, kwargs))
        return len(self.add_roi_calls)

    def add_thumbnail(self, *args):
        self.add_thumbnail_calls.append(args)
        return len(self.add_thumbnail_calls)

    def edit_row(self, *args, **kwargs):
        self.edit_row_calls.append((args, kwargs))
        return True


def _cfg(tmp_path, smart_frames=True, n_frames=2):
    return SimpleNamespace(
        ML_DIR=str(tmp_path / "ml"),
        SMART_FRAMES=smart_frames,
        VIDEO_FPS=4,
        N_FRAMES=n_frames,
        THUMBNAIL_DIR=str(tmp_path / "thumbs"),
        DEVICE="cpu",
    )


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


class TestAnimlThread:
    def test_initializes_media_and_rois_and_none_detector(self, tmp_path, monkeypatch):
        db = FakeDB()
        db.media_rows = [
            (1, 1, "a.jpg", "hash-a", ".jpg", "2024-01-01", 1, None, None, None, None, "/base/a.jpg"),
            (2, 1, "b.mp4", "hash-b", ".mp4", "2024-01-02", 1, None, None, None, None, "/base/b.mp4"),
        ]

        monkeypatch.setattr(animl_thread, "get_path", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(
            animl_thread,
            "fetch_roi_media",
            lambda *_args, **_kwargs: pd.DataFrame(
                [
                    {"id": 10, "media_id": 1, "bbox_x": -1, "bbox_y": -1, "bbox_w": -1, "bbox_h": -1, "filepath": "/base/a.jpg", "ext": ".jpg"},
                    {"id": 11, "media_id": 2, "bbox_x": 0.1, "bbox_y": 0.2, "bbox_w": 0.3, "bbox_h": 0.4, "filepath": "/base/b.mp4", "ext": ".mp4"},
                ]
            ),
        )

        thread = animl_thread.AnimlThread(db, _cfg(tmp_path), DETECTOR_KEY=None)

        assert len(thread.media) == 2
        assert len(thread.rois) == 1
        assert "bbox_x" not in thread.rois.columns
        assert thread.detector is None

    def test_detect_images_adds_rois_updates_existing_and_emits_progress(self, tmp_path, monkeypatch):
        db = FakeDB()
        monkeypatch.setattr(animl_thread, "get_path", lambda *_args, **_kwargs: Path("/fake.pt"))
        monkeypatch.setattr(animl_thread.animl, "load_detector", lambda *_args, **_kwargs: "det")
        monkeypatch.setattr(animl_thread, "fetch_roi_media", lambda *_args, **_kwargs: _empty_roi_media())
        monkeypatch.setattr(animl_thread, "save_roi_thumbnail", lambda *_args, **_kwargs: "roi-thumb.jpg")

        thread = animl_thread.AnimlThread(db, _cfg(tmp_path), DETECTOR_KEY="md")
        thread.images = pd.DataFrame([{"id": 3, "filepath": "/base/new.jpg", "ext": ".jpg"}])
        thread.rois = pd.DataFrame([{"id": 20, "media_id": 4, "filepath": "/base/old.jpg", "ext": ".jpg"}])
        thread.to_process = 2
        thread.progress_count = 0
        thread.progress_update = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        monkeypatch.setattr(animl_thread.animl, "detect", lambda *_args, **_kwargs: pd.DataFrame())
        monkeypatch.setattr(animl_thread.animl, "parse_detections", lambda detections, **_kwargs: detections)
        monkeypatch.setattr(
            animl_thread.animl,
            "get_animals",
            lambda _detections: pd.DataFrame([{"frame": 2, "bbox_x": 0.1, "bbox_y": 0.2, "bbox_w": 0.3, "bbox_h": 0.4}]),
        )

        thread.detect_images()

        assert len(db.add_roi_calls) == 1
        assert db.add_roi_calls[0][0][0] == 3
        assert len(db.add_thumbnail_calls) == 1
        assert len(db.edit_row_calls) == 1
        assert db.edit_row_calls[0][0][1] == 20
        assert thread.progress_update.calls == [(50,), (100,)]

    def test_detect_images_skips_when_detector_none(self, tmp_path, monkeypatch):
        db = FakeDB()
        monkeypatch.setattr(animl_thread, "get_path", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(animl_thread, "fetch_roi_media", lambda *_args, **_kwargs: _empty_roi_media())

        thread = animl_thread.AnimlThread(db, _cfg(tmp_path), DETECTOR_KEY=None)
        thread.images = pd.DataFrame([{"id": 3, "filepath": "/base/new.jpg", "ext": ".jpg"}])
        thread.rois = pd.DataFrame()
        thread.prompt_update = SignalSpy()

        thread.detect_images()

        assert db.add_roi_calls == []
        assert db.edit_row_calls == []
        assert ("No detector selected, skipping detection...",) in thread.prompt_update.calls

    def test_detect_videos_adds_top_frame_rois(self, tmp_path, monkeypatch):
        db = FakeDB()
        monkeypatch.setattr(animl_thread, "get_path", lambda *_args, **_kwargs: Path("/fake.pt"))
        monkeypatch.setattr(animl_thread.animl, "load_detector", lambda *_args, **_kwargs: "det")
        monkeypatch.setattr(animl_thread, "fetch_roi_media", lambda *_args, **_kwargs: _empty_roi_media())
        monkeypatch.setattr(animl_thread, "save_roi_thumbnail", lambda *_args, **_kwargs: "roi-thumb.jpg")

        thread = animl_thread.AnimlThread(db, _cfg(tmp_path, n_frames=1), DETECTOR_KEY="md")
        thread.videos = pd.DataFrame(
            [
                {"id": 5, "filepath": "/base/v.mp4", "ext": ".mp4", "frame": 1},
                {"id": 5, "filepath": "/base/v.mp4", "ext": ".mp4", "frame": 2},
            ]
        )
        thread.to_process = 1
        thread.progress_count = 0
        thread.progress_update = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        monkeypatch.setattr(animl_thread.animl, "detect", lambda *_args, **_kwargs: pd.DataFrame())
        monkeypatch.setattr(animl_thread.animl, "parse_detections", lambda detections, **_kwargs: detections)
        monkeypatch.setattr(
            animl_thread.animl,
            "get_animals",
            lambda _detections: pd.DataFrame(
                [
                    {"frame": 1, "bbox_x": 0.1, "bbox_y": 0.2, "bbox_w": 0.3, "bbox_h": 0.4, "score": 0.5, "filepath": "/base/v.mp4", "ext": ".mp4"},
                    {"frame": 2, "bbox_x": 0.6, "bbox_y": 0.7, "bbox_w": 0.8, "bbox_h": 0.9, "score": 0.9, "filepath": "/base/v.mp4", "ext": ".mp4"},
                ]
            ),
        )

        thread.detect_videos()

        assert len(db.add_roi_calls) == 1
        assert db.add_roi_calls[0][0][1] == 2
        assert len(db.add_thumbnail_calls) == 1
        assert thread.progress_update.calls == [(100,)]
