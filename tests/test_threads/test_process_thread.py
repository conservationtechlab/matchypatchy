"""
ProcessThread: one pass per media file, against a real database with fake models

The fake viewpoint model answers 1 for bright crops and 0 for dark ones, and the
fake re-id model's embedding starts with the crop's mean brightness, so every
result can be traced back to the image it was computed from.
"""
import logging
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from matchypatchy.database.mpdb import MatchyPatchyDB
from matchypatchy.threads import process_thread
from matchypatchy.threads.process_thread import ProcessThread


class SignalSpy:
    def __init__(self):
        self.calls = []

    def emit(self, *args):
        self.calls.append(args)


class FakeSession:
    def __init__(self, fn, model_type=None):
        self.fn = fn
        self.model_type = model_type
        self.calls = 0

    def get_inputs(self):
        return [SimpleNamespace(name="input")]

    def run(self, _names, feed):
        self.calls += 1
        return [self.fn(feed["input"])]


def fake_detector():
    # one animal in the middle of the letterboxed 960x960 input
    box = np.array([[[200, 300, 700, 800, 0.9, 0]]], dtype=np.float32)
    return FakeSession(lambda x: np.repeat(box, x.shape[0], axis=0), model_type="megadetector")


def fake_viewpoint():
    return FakeSession(lambda x: np.array([[0.0, 10.0]] if x.mean() > 0.5 else [[10.0, 0.0]]))


def fake_miew():
    return FakeSession(lambda x: np.array([[float(x.mean()), 1.0, 0.0, 0.0]], dtype=np.float32))


@pytest.fixture
def project(tmp_path, monkeypatch):
    """Real database, fake models, images on disk; returns a helper namespace"""
    db = MatchyPatchyDB(str(tmp_path), logging.getLogger("test"))
    station = db.add_station("S", None, None, 1)
    upload = db.add_upload(str(tmp_path))
    models = SimpleNamespace(detector=fake_detector(), viewpoint=fake_viewpoint(), miew=fake_miew())
    monkeypatch.setattr(process_thread, "get_path", lambda _dir, key: Path(f"/models/{key}") if key else None)
    monkeypatch.setattr(process_thread.animl, "load_detector", lambda *_a, **_k: models.detector)
    monkeypatch.setattr(process_thread.animl, "load_classifier", lambda *_a, **_k: (models.viewpoint, None))
    monkeypatch.setattr(process_thread.animl, "load_miew", lambda *_a, **_k: models.miew)
    monkeypatch.setattr(process_thread, "save_roi_thumbnail_from_image", lambda *_a, **_k: "thumb.jpg")

    def add_image(name, value=None):
        """Image of one brightness (0-255); value None leaves the file missing"""
        if value is not None:
            Image.new("RGB", (640, 480), (value,) * 3).save(tmp_path / name)
        return db.add_media(upload, name, f"sha-{name}", Path(name).suffix, "2024-01-01 10:00:00", station)

    def thread(detector=True, viewpoint=True, reid=True, n_frames=2):
        cfg = SimpleNamespace(THUMBNAIL_DIR=str(tmp_path), DEVICE="cpu", ML_DIR=str(tmp_path),
                              SMART_FRAMES=True, VIDEO_FPS=1, N_FRAMES=n_frames)
        options = {"DETECTOR_KEY": "md" if detector else None, "VIEWPOINT_KEY": "vp" if viewpoint else None,
                   "REID_KEY": "miew" if reid else None}
        t = ProcessThread(db, cfg, options)
        t.prompt_update, t.progress_update, t.done = SignalSpy(), SignalSpy(), SignalSpy()
        t.isInterruptionRequested = lambda: False
        return t

    def rois():
        return db.select("roi", "media_id, frame, bbox_x, bbox_y, bbox_w, bbox_h, viewpoint, emb")

    yield SimpleNamespace(db=db, add_image=add_image, thread=thread, rois=rois, models=models, tmp=tmp_path)
    db.close()


def _embedding(db, roi_id):
    return db.collection.get(ids=[str(roi_id)], include=["embeddings"])["embeddings"][0]


class TestDetectAndEmbed:
    def test_new_images_get_rois_with_viewpoint_and_embedding(self, project):
        white = project.add_image("white.jpg", 255)
        black = project.add_image("black.jpg", 0)
        t = project.thread()
        t.run()
        rois = {row[0]: row for row in project.rois()}
        assert set(rois) == {white, black}
        assert rois[white][6] == 1 and rois[black][6] == 0       # viewpoint from the right image
        assert rois[white][7] == 1 and rois[black][7] == 1       # embedded
        assert project.db.count("roi_thumbnails") == 2
        roi_ids = dict(project.db.select("roi", "media_id, id"))
        assert _embedding(project.db, roi_ids[white])[0] > 0.9
        assert _embedding(project.db, roi_ids[black])[0] < 0.1
        assert t.done.calls == [()]

    def test_each_model_runs_once_per_image_or_roi(self, project):
        project.add_image("a.jpg", 200)
        project.add_image("b.jpg", 50)
        project.thread().run()
        assert project.models.detector.calls == 2
        assert project.models.viewpoint.calls == 2
        assert project.models.miew.calls == 2

    def test_unreadable_file_doesnt_shift_results(self, project):
        """Viewpoints went to the wrong roi when a file before them couldn't be loaded"""
        white = project.add_image("1_white.jpg", 255)
        project.add_image("2_missing.jpg")
        black = project.add_image("3_black.jpg", 0)
        t = project.thread()
        t.run()
        viewpoints = {row[0]: row[6] for row in project.rois()}
        assert viewpoints == {white: 1, black: 0}
        assert [Path(f).name for f in t.failed] == ["2_missing.jpg"]
        # the progress popup stays open with the result instead of closing
        assert t.done.calls == []
        assert "1 file(s) could not be processed" in t.prompt_update.calls[-1][0]


class TestExistingRois:
    def test_only_missing_results_are_computed(self, project):
        mid = project.add_image("a.jpg", 255)
        project.db.add_roi(mid, 0, 0.1, 0.1, 0.5, 0.5, viewpoint=0, emb=0)   # has a viewpoint, no embedding
        project.thread().run()
        assert project.models.detector.calls == 0
        assert project.models.viewpoint.calls == 0
        assert project.models.miew.calls == 1
        assert project.rois()[0][6:] == (0, 1)

    def test_imported_roi_without_bbox_gets_detection(self, project):
        mid = project.add_image("a.jpg", 255)
        project.db.add_roi(mid, 0, -1, -1, -1, -1)
        project.thread().run()
        (row,) = project.rois()
        assert row[2] >= 0 and row[4] > 0          # box found
        assert row[6] == 1 and row[7] == 1         # then viewpoint and embedding

    def test_roi_without_bbox_untouched_without_detector(self, project):
        mid = project.add_image("a.jpg", 255)
        project.db.add_roi(mid, 0, -1, -1, -1, -1)
        project.thread(detector=False).run()
        (row,) = project.rois()
        assert row[2] == -1
        assert project.models.miew.calls == 0       # nothing to crop


class TestNoDetector:
    def test_full_frame_roi_for_images(self, project):
        project.add_image("a.jpg", 255)
        project.thread(detector=False).run()
        (row,) = project.rois()
        assert row[1:6] == (0, 0.0, 0.0, 1.0, 1.0)

    def test_full_frame_roi_for_videos(self, project, monkeypatch):
        """detect(None, ...) used to crash on videos"""
        project.add_image("clip.mp4")
        frame = Image.new("RGB", (64, 48), (255,) * 3)
        monkeypatch.setattr(process_thread.ip, "load_frames", lambda _fp, frames: {0: frame} if 0 in frames else {})
        project.thread(detector=False).run()
        (row,) = project.rois()
        assert row[1:6] == (0, 0.0, 0.0, 1.0, 1.0)


class TestVideos:
    def test_best_frames_kept(self, project, monkeypatch):
        project.add_image("clip.mp4")
        frames = {f: Image.new("RGB", (64, 48), (255,) * 3) for f in (0, 5, 10)}
        monkeypatch.setattr(ProcessThread, "_candidate_frames", lambda self, fp: [0, 5, 10])
        monkeypatch.setattr(process_thread.ip, "load_frames", lambda _fp, wanted: {f: frames[f] for f in wanted})
        scores = {0: 0.2, 5: 0.9, 10: 0.6}
        monkeypatch.setattr(process_thread.ip, "detect_animals",
                            lambda *_a, frame=0, **_k: [dict(bbox_x=0.1, bbox_y=0.1, bbox_w=0.5, bbox_h=0.5,
                                                             conf=0.9, score=scores[frame])])
        project.thread(n_frames=2).run()
        assert sorted(row[1] for row in project.rois()) == [5, 10]


class TestRunControl:
    def test_model_not_downloaded(self, project, monkeypatch):
        project.add_image("a.jpg", 255)
        monkeypatch.setattr(process_thread, "get_path", lambda _dir, key: None)
        t = project.thread()
        t.run()
        assert "not downloaded" in t.prompt_update.calls[-1][0]
        assert project.rois() == []

    def test_cancel_stops_before_next_file(self, project):
        project.add_image("a.jpg", 255)
        project.add_image("b.jpg", 255)
        t = project.thread()
        calls = iter([False, True])
        t.isInterruptionRequested = lambda: next(calls, True)
        t.run()
        assert len({row[0] for row in project.rois()}) == 1
        assert t.done.calls == []

    def test_nothing_to_do(self, project):
        t = project.thread()
        t.run()
        assert t.done.calls == [()]
