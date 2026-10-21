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


def _detect_reads(unreadable=()):
    """Stand-in for animl.detect: one result per readable file, unreadable ones left out"""
    def _detect(_detector, manifest, *_args, **_kwargs):
        return [{"filepath": f, "frame": 0, "detections": []}
                for f in manifest["filepath"].unique() if f not in unreadable]
    return _detect


def _empty_roi_media():
    return pd.DataFrame(columns=["id", "media_id", "bbox_x", "bbox_y", "bbox_w", "bbox_h", "filepath", "ext"])


class FakeDB:
    def __init__(self):
        self.add_roi_calls = []
        self.add_thumbnail_calls = []
        self.edit_row_calls = []
        self.marked_done = []
        # media ids with detection_done = 0, None for every media
        self.pending_media = None
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

    def select(self, table, columns="*", row_cond=None, quiet=True):
        assert (table, columns, row_cond) == ("media", "id", "detection_done = 0")
        pending = self.pending_media if self.pending_media is not None else range(1000)
        return [(media_id,) for media_id in pending]

    def mark_detection_done(self, media_ids):
        self.marked_done.extend(int(media_id) for media_id in media_ids)
        return True


def _cfg(tmp_path, smart_frames=True, n_frames=2):
    return SimpleNamespace(
        ML_DIR=str(tmp_path / "ml"),
        SMART_FRAMES=smart_frames,
        VIDEO_FPS=4,
        N_FRAMES=n_frames,
        THUMBNAIL_DIR=str(tmp_path / "thumbs"),
        DEVICE="cpu",
        BATCH_SIZE=1,
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
    @staticmethod
    def _write(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return animl_thread.get_sha256(path)

    @staticmethod
    def _run(db, updates, monkeypatch):
        # list files like build_file_manifest without depending on animl being installed
        monkeypatch.setattr(
            animl_thread.animl,
            "build_file_manifest",
            lambda directory, **_kwargs: pd.DataFrame(
                {"filepath": sorted(str(f) for f in Path(directory).rglob("*.jpg"))}),
        )
        parent = SimpleNamespace(mpDB=db, base_dirs=[], updates=updates)
        thread = animl_thread.VerifyNewBaseDirsThread(parent)
        thread.not_in_db = SignalSpy()
        thread.not_in_new_directory = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False
        thread.run()
        return thread

    def test_compares_hashes_and_emits_missing_lists(self, tmp_db, tmp_path, monkeypatch):
        db, _ = tmp_db
        new = tmp_path / "new"
        hash_a = self._write(new / "a.jpg", b"a")
        self._write(new / "c.jpg", b"c")
        station_id = db.add_station("S", 1.0, 2.0, 1)
        base_id = db.add_upload("/old")
        db.add_media(base_id, "a.jpg", hash_a, ".jpg", "2024-01-01 00:00:00", station_id)
        db.add_media(base_id, "b.jpg", "hash-b", ".jpg", "2024-01-01 00:00:01", station_id)

        thread = self._run(db, [(base_id, str(new))], monkeypatch)

        assert thread.not_in_db.calls == [([[str(new / "c.jpg")]],)]
        assert thread.not_in_new_directory.calls == [([["b.jpg"]],)]
        assert len(thread.finished.calls) == 1

    def test_files_must_be_at_their_relative_path(self, tmp_db, tmp_path, monkeypatch):
        """A folder holding the files one level deeper would break every path on save"""
        db, _ = tmp_db
        backup = tmp_path / "backup"
        sha = self._write(backup / "2023" / "Site01" / "IMG.JPG", b"img")
        station_id = db.add_station("S", 1.0, 2.0, 1)
        base_id = db.add_upload("/old/2023")
        db.add_media(base_id, "Site01/IMG.JPG", sha, ".jpg", "2024-01-01 00:00:00", station_id)

        thread = self._run(db, [(base_id, str(backup))], monkeypatch)
        assert thread.not_in_new_directory.calls == [([["Site01/IMG.JPG"]],)]

        thread = self._run(db, [(base_id, str(backup / "2023"))], monkeypatch)
        assert thread.not_in_new_directory.calls == [([[]],)]

    def test_changed_file_at_relative_path_is_missing(self, tmp_db, tmp_path, monkeypatch):
        db, _ = tmp_db
        new = tmp_path / "new"
        self._write(new / "a.jpg", b"different")
        station_id = db.add_station("S", 1.0, 2.0, 1)
        base_id = db.add_upload("/old")
        db.add_media(base_id, "a.jpg", "hash-a", ".jpg", "2024-01-01 00:00:00", station_id)

        thread = self._run(db, [(base_id, str(new))], monkeypatch)
        assert thread.not_in_new_directory.calls == [([["a.jpg"]],)]

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
        thread.detector = "det"
        thread.images = pd.DataFrame([{"id": 3, "filepath": "/base/new.jpg", "ext": ".jpg"}])
        thread.rois = pd.DataFrame([{"id": 20, "media_id": 4, "filepath": "/base/old.jpg", "ext": ".jpg"}])
        thread.to_process = 2
        thread.progress_count = 0
        thread.progress_update = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        monkeypatch.setattr(animl_thread.animl, "detect", _detect_reads())
        monkeypatch.setattr(animl_thread.animl, "parse_detections", lambda detections, **_kwargs: detections)
        
        # Track which batch is being processed
        call_count = [0]
        def mock_get_animals(_detections):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: new images batch
                return pd.DataFrame([
                    {
                        "id": 3,  # media_id for new images
                        "frame": 2,
                        "bbox_x": 0.1,
                        "bbox_y": 0.2,
                        "bbox_w": 0.3,
                        "bbox_h": 0.4,
                        "filepath": "/base/new.jpg",
                        "ext": ".jpg"
                    }
                ])
            else:
                # Second call: existing rois batch
                return pd.DataFrame([
                    {
                        "id": 20,  # roi id for existing rois
                        "frame": 0,
                        "conf": 0.9,
                        "bbox_x": 0.5,
                        "bbox_y": 0.6,
                        "bbox_w": 0.7,
                        "bbox_h": 0.8,
                        "filepath": "/base/old.jpg",
                        "ext": ".jpg"
                    }
                ])
        
        monkeypatch.setattr(animl_thread.animl, "get_animals", mock_get_animals)

        thread.detect_images()

        assert len(db.add_roi_calls) == 1
        assert db.add_roi_calls[0][0][0] == 3
        assert len(db.add_thumbnail_calls) == 1
        assert len(db.edit_row_calls) == 1
        assert db.edit_row_calls[0][0][1] == 20
        assert thread.progress_update.calls == [(50,), (100,)]

    def test_detect_images_uses_full_image_when_detector_none(self, tmp_path, monkeypatch):
        db = FakeDB()
        monkeypatch.setattr(animl_thread, "get_path", lambda *_a, **_k: None)
        monkeypatch.setattr(animl_thread, "fetch_roi_media", lambda *_a, **_k: _empty_roi_media())
        monkeypatch.setattr(animl_thread, "save_roi_thumbnail", lambda *_a, **_k: "thumb.jpg")

        thread = animl_thread.AnimlThread(db, _cfg(tmp_path), DETECTOR_KEY=None)
        thread.images = pd.DataFrame([{"id": 3, "filepath": "/base/new.jpg", "ext": ".jpg"}])
        thread.rois = pd.DataFrame()
        thread.prompt_update = SignalSpy()
        thread.to_process = 1

        thread.detect_images()

        # one full-frame ROI per image, no detector run
        assert db.add_roi_calls == [
            ((3, 0, 0, 0, 1, 1), {"viewpoint": None, "individual_id": None, "emb": 0})
        ]
        assert db.edit_row_calls == []

    def test_detect_videos_adds_top_frame_rois(self, tmp_path, monkeypatch):
        db = FakeDB()
        monkeypatch.setattr(animl_thread, "get_path", lambda *_args, **_kwargs: Path("/fake.pt"))
        monkeypatch.setattr(animl_thread.animl, "load_detector", lambda *_args, **_kwargs: "det")
        monkeypatch.setattr(animl_thread, "fetch_roi_media", lambda *_args, **_kwargs: _empty_roi_media())
        monkeypatch.setattr(animl_thread, "save_roi_thumbnail", lambda *_args, **_kwargs: "roi-thumb.jpg")

        thread = animl_thread.AnimlThread(db, _cfg(tmp_path, n_frames=1), DETECTOR_KEY="md")
        thread.detector = "det"
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

        monkeypatch.setattr(animl_thread.animl, "detect", _detect_reads())
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

    def _thread_with_detector(self, tmp_path, monkeypatch, unreadable):
        db = FakeDB()
        monkeypatch.setattr(animl_thread, "get_path", lambda *_a, **_k: Path("/fake.pt"))
        monkeypatch.setattr(animl_thread.animl, "load_detector", lambda *_a, **_k: "det")
        monkeypatch.setattr(animl_thread, "fetch_roi_media", lambda *_a, **_k: _empty_roi_media())
        monkeypatch.setattr(animl_thread, "save_roi_thumbnail", lambda *_a, **_k: "thumb.jpg")
        monkeypatch.setattr(animl_thread.animl, "detect", _detect_reads(unreadable))

        def _parse_detections(detections, manifest=None, **_kwargs):
            if len(detections) == 0:
                raise AssertionError("'detections' contains no detections")
            return manifest.assign(bbox_x=0.1, bbox_y=0.2, bbox_w=0.3, bbox_h=0.4, score=1.0)

        monkeypatch.setattr(animl_thread.animl, "parse_detections", _parse_detections)
        monkeypatch.setattr(animl_thread.animl, "get_animals", lambda detections: detections)

        thread = animl_thread.AnimlThread(db, _cfg(tmp_path, n_frames=1), DETECTOR_KEY="md")
        thread.detector = "det"
        thread.rois = pd.DataFrame()
        thread.progress_count = 0
        thread.progress_update = SignalSpy()
        thread.isInterruptionRequested = lambda: False
        return thread, db

    def test_unreadable_image_is_skipped(self, tmp_path, monkeypatch):
        thread, db = self._thread_with_detector(tmp_path, monkeypatch, unreadable={"/base/bad.jpg"})
        thread.images = pd.DataFrame([{"id": i, "filepath": f"/base/{name}.jpg", "ext": ".jpg"}
                                      for i, name in enumerate(["a", "bad", "c"])])
        thread.to_process = 3

        thread.detect_images()

        assert [call[0][0] for call in db.add_roi_calls] == [0, 2]
        assert thread.failed == {"/base/bad.jpg"}
        assert thread.progress_update.calls[-1] == (100,)

    def test_unreadable_video_is_skipped(self, tmp_path, monkeypatch):
        thread, db = self._thread_with_detector(tmp_path, monkeypatch, unreadable={"/base/bad.mp4"})
        thread.videos = pd.DataFrame([{"id": i, "filepath": f"/base/{name}.mp4", "ext": ".mp4", "frame": 0}
                                      for i, name in enumerate(["bad", "b"])])
        thread.to_process = 2

        thread.detect_videos()

        assert [call[0][0] for call in db.add_roi_calls] == [1]
        assert thread.failed == {"/base/bad.mp4"}

    def test_video_frames_are_detected_one_at_a_time(self, tmp_path, monkeypatch):
        thread, db = self._thread_with_detector(tmp_path, monkeypatch, unreadable=())
        batch_sizes = []
        detect = animl_thread.animl.detect

        def _detect(*args, **kwargs):
            batch_sizes.append(kwargs.get("batch_size", 8))  # animl's default
            return detect(*args, **kwargs)

        monkeypatch.setattr(animl_thread.animl, "detect", _detect)
        thread.videos = pd.DataFrame([{"id": 1, "filepath": "/base/v.mp4", "ext": ".mp4", "frame": f}
                                      for f in range(3)])
        thread.to_process = 1

        thread.detect_videos()

        assert batch_sizes == [1]

    def test_detect_videos_uses_full_first_frame_when_detector_none(self, tmp_path, monkeypatch):
        db = FakeDB()
        monkeypatch.setattr(animl_thread, "get_path", lambda *_a, **_k: None)
        monkeypatch.setattr(animl_thread, "fetch_roi_media", lambda *_a, **_k: _empty_roi_media())
        monkeypatch.setattr(animl_thread, "save_roi_thumbnail", lambda *_a, **_k: "thumb.jpg")

        def _detect(detector, *_args, **_kwargs):
            raise AssertionError("detect called without a detector")

        monkeypatch.setattr(animl_thread.animl, "detect", _detect)
        thread = animl_thread.AnimlThread(db, _cfg(tmp_path), DETECTOR_KEY=None)
        thread.videos = pd.DataFrame([{"id": 5, "filepath": "/base/v.mp4", "ext": ".mp4", "frame": f}
                                      for f in (3, 7)])
        thread.to_process = 1
        thread.progress_update = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        thread.detect_videos()

        assert db.add_roi_calls == [
            ((5, 3, 0, 0, 1, 1), {"viewpoint": None, "individual_id": None, "emb": 0})
        ]

    def test_rois_without_box_are_left_when_detector_none(self, tmp_path, monkeypatch):
        db = FakeDB()
        monkeypatch.setattr(animl_thread, "get_path", lambda *_a, **_k: None)
        monkeypatch.setattr(
            animl_thread, "fetch_roi_media",
            lambda *_a, **_k: pd.DataFrame([{"id": 10, "media_id": 1, "frame": 0, "bbox_x": -1, "bbox_y": -1,
                                             "bbox_w": -1, "bbox_h": -1, "filepath": "/base/a.jpg", "ext": ".jpg"}]))

        def _detect(detector, *_args, **_kwargs):
            raise AssertionError("detect called without a detector")

        monkeypatch.setattr(animl_thread.animl, "detect", _detect)
        monkeypatch.setattr(animl_thread.animl, "get_images", lambda media: media)
        monkeypatch.setattr(animl_thread.animl, "get_videos", lambda media: media)
        monkeypatch.setattr(animl_thread.animl, "extract_frames", lambda videos, **_k: videos)
        thread = animl_thread.AnimlThread(db, _cfg(tmp_path), DETECTOR_KEY=None)
        thread.prompt_update = SignalSpy()
        thread.progress_update = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        thread.run()

        assert db.edit_row_calls == []

    def test_roi_without_box_takes_most_confident_detection(self, tmp_path, monkeypatch):
        thread, db = self._thread_with_detector(tmp_path, monkeypatch, unreadable=())
        thread.images = pd.DataFrame(columns=["id", "filepath", "ext"])
        thread.rois = pd.DataFrame([{"id": 20, "media_id": 4, "frame": 0, "filepath": "/base/old.jpg", "ext": ".jpg"}])
        thread.to_process = 1
        # detections come sorted most confident first
        monkeypatch.setattr(
            animl_thread.animl, "parse_detections",
            lambda _detections, manifest=None, **_k: pd.DataFrame([
                {"id": 20, "frame": 0, "conf": conf, "bbox_x": x, "bbox_y": 0.1, "bbox_w": 0.2, "bbox_h": 0.2}
                for conf, x in ((0.9, 0.5), (0.4, 0.1), (0.2, 0.3))]))

        thread.detect_images()

        assert len(db.edit_row_calls) == 1
        assert db.edit_row_calls[0][0][2]["bbox_x"] == 0.5

    def test_detector_is_loaded_in_run_not_on_the_gui_thread(self, tmp_path, monkeypatch):
        db = FakeDB()
        loads = []
        monkeypatch.setattr(animl_thread, "get_path", lambda *_a, **_k: Path("/fake.pt"))
        monkeypatch.setattr(animl_thread.animl, "load_detector", lambda *_a, **_k: loads.append(1) or "det")
        monkeypatch.setattr(animl_thread, "fetch_roi_media", lambda *_a, **_k: _empty_roi_media())
        monkeypatch.setattr(animl_thread.animl, "get_images", lambda media: media)
        monkeypatch.setattr(animl_thread.animl, "get_videos", lambda media: media)
        monkeypatch.setattr(animl_thread.animl, "extract_frames", lambda videos, **_k: videos)

        thread = animl_thread.AnimlThread(db, _cfg(tmp_path), DETECTOR_KEY="md")
        assert loads == []
        thread.prompt_update = SignalSpy()
        thread.run()

        assert loads == [1]
        assert thread.detector == "det"


class TestDetectionDone:
    """Files are marked once they've been through detection, and only unmarked files are run"""

    def test_media_selection_skips_files_already_detected(self, tmp_db, tmp_path, monkeypatch):
        db, _ = tmp_db
        monkeypatch.setattr(animl_thread, "get_path", lambda *_a, **_k: None)
        station_id = db.add_station("Site01", None, None, 1)
        upload_id = db.add_upload("D:/2023")
        done, pending = (db.add_media(upload_id, f"{n}.jpg", f"hash{n}", ".jpg", "2023-01-01", station_id)
                         for n in ("done", "pending"))
        # the detector found nothing in it last time, so it has no rois
        db.mark_detection_done([done])

        thread = animl_thread.AnimlThread(db, _cfg(tmp_path), DETECTOR_KEY=None)

        assert thread.media["id"].tolist() == [pending]

    def test_rois_without_box_on_detected_media_are_skipped(self, tmp_path, monkeypatch):
        db = FakeDB()
        db.pending_media = {1}
        monkeypatch.setattr(animl_thread, "get_path", lambda *_a, **_k: None)
        monkeypatch.setattr(
            animl_thread, "fetch_roi_media",
            lambda *_a, **_k: pd.DataFrame([{"id": 10 + m, "media_id": m, "bbox_x": -1, "bbox_y": -1, "bbox_w": -1,
                                             "bbox_h": -1, "filepath": f"/base/{m}.jpg", "ext": ".jpg"}
                                            for m in (1, 2)]))

        thread = animl_thread.AnimlThread(db, _cfg(tmp_path), DETECTOR_KEY=None)

        assert thread.rois["media_id"].tolist() == [1]

    def test_detected_images_are_marked_except_unreadable(self, tmp_path, monkeypatch):
        thread, db = TestAnimlThread._thread_with_detector(None, tmp_path, monkeypatch, unreadable={"/base/bad.jpg"})
        thread.images = pd.DataFrame([{"id": i, "filepath": f"/base/{name}.jpg", "ext": ".jpg"}
                                      for i, name in enumerate(["a", "bad", "c"])])
        thread.to_process = 3

        thread.detect_images()

        assert db.marked_done == [0, 2]

    def test_images_with_nothing_detected_are_marked(self, tmp_path, monkeypatch):
        thread, db = TestAnimlThread._thread_with_detector(None, tmp_path, monkeypatch, unreadable=())
        monkeypatch.setattr(animl_thread.animl, "get_animals", lambda detections: detections.iloc[0:0])
        thread.images = pd.DataFrame([{"id": 7, "filepath": "/base/empty.jpg", "ext": ".jpg"}])
        thread.to_process = 1

        thread.detect_images()

        assert db.add_roi_calls == []
        assert db.marked_done == [7]

    def test_full_image_rois_mark_media(self, tmp_path, monkeypatch):
        db = FakeDB()
        monkeypatch.setattr(animl_thread, "get_path", lambda *_a, **_k: None)
        monkeypatch.setattr(animl_thread, "fetch_roi_media", lambda *_a, **_k: _empty_roi_media())
        monkeypatch.setattr(animl_thread, "save_roi_thumbnail", lambda *_a, **_k: "thumb.jpg")
        thread = animl_thread.AnimlThread(db, _cfg(tmp_path), DETECTOR_KEY=None)
        thread.images = pd.DataFrame([{"id": 3, "filepath": "/base/new.jpg", "ext": ".jpg"}])
        thread.rois = pd.DataFrame()
        thread.to_process = 1

        thread.detect_images()

        assert db.marked_done == [3]

    def test_rois_without_box_mark_their_media_even_without_a_detection(self, tmp_path, monkeypatch):
        thread, db = TestAnimlThread._thread_with_detector(None, tmp_path, monkeypatch, unreadable=())
        monkeypatch.setattr(animl_thread.animl, "get_animals", lambda detections: detections.assign(conf=1.0).iloc[0:0])
        thread.images = pd.DataFrame(columns=["id", "filepath", "ext"])
        thread.rois = pd.DataFrame([{"id": 20, "media_id": 4, "frame": 0, "filepath": "/base/old.jpg", "ext": ".jpg"}])
        thread.to_process = 1

        thread.detect_images()

        assert db.edit_row_calls == []
        assert db.marked_done == [4]

    def test_rois_without_box_are_not_marked_without_a_detector(self, tmp_path, monkeypatch):
        db = FakeDB()
        monkeypatch.setattr(animl_thread, "get_path", lambda *_a, **_k: None)
        monkeypatch.setattr(
            animl_thread, "fetch_roi_media",
            lambda *_a, **_k: pd.DataFrame([{"id": 10, "media_id": 1, "frame": 0, "bbox_x": -1, "bbox_y": -1,
                                             "bbox_w": -1, "bbox_h": -1, "filepath": "/base/a.jpg", "ext": ".jpg"}]))
        monkeypatch.setattr(animl_thread.animl, "get_images", lambda media: media)
        monkeypatch.setattr(animl_thread.animl, "get_videos", lambda media: media)
        monkeypatch.setattr(animl_thread.animl, "extract_frames", lambda videos, **_k: videos)
        thread = animl_thread.AnimlThread(db, _cfg(tmp_path), DETECTOR_KEY=None)
        thread.prompt_update = SignalSpy()
        thread.progress_update = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        thread.run()

        # left for a later run with a detector
        assert db.marked_done == []

    def test_detected_videos_are_marked_except_unreadable(self, tmp_path, monkeypatch):
        thread, db = TestAnimlThread._thread_with_detector(None, tmp_path, monkeypatch, unreadable={"/base/bad.mp4"})
        thread.videos = pd.DataFrame([{"id": i, "filepath": f"/base/{name}.mp4", "ext": ".mp4", "frame": 0}
                                      for i, name in enumerate(["bad", "b"])])
        thread.to_process = 2

        thread.detect_videos()

        assert db.marked_done == [1]
