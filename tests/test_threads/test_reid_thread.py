"""Tests for matchypatchy.threads.reid_thread"""
import sys
import types
from types import SimpleNamespace

import numpy as np
import pandas as pd


if "animl" not in sys.modules:
    animl_stub = types.ModuleType("animl")
    animl_stub.load_classifier = lambda *args, **kwargs: (None, None)
    animl_stub.load_miew = lambda *args, **kwargs: None
    animl_stub.softmax = lambda x: x
    sys.modules["animl"] = animl_stub

from matchypatchy.threads import reid_thread  # noqa: E402


class SignalSpy:
    def __init__(self):
        self.calls = []

    def emit(self, *args):
        self.calls.append(args)


class FakeModel:
    """Stand-in ONNX model: the predicted class is the number stored in each image."""

    def get_inputs(self):
        return [SimpleNamespace(name="input")]

    def run(self, _output_names, feed):
        images = feed["input"]
        logits = np.zeros((len(images), 10))
        for i, image in enumerate(images):
            logits[i, int(image)] = 10.0
        return [logits]


class FakeDB:
    def __init__(self):
        self.edit_row_calls = []

    def edit_row(self, table, row_id, replace, **kwargs):
        self.edit_row_calls.append((table, row_id, replace))
        return True


class FakeManifestGenerator:
    """Mimics animl.ManifestGenerator: yields (images, filepaths, frames, hw) batches
    and, like animl, silently drops files it can't load"""
    unreadable = set()

    def __init__(self, manifest, **kwargs):
        self.manifest = manifest.reset_index(drop=True)
        self.batch_size = kwargs.get("batch_size", 16)

    def __iter__(self):
        readable = self.manifest[~self.manifest["filepath"].isin(self.unreadable)]
        for start in range(0, len(readable), self.batch_size):
            batch = readable.iloc[start:start + self.batch_size]
            # the "image" is the digit in the file name, so results show which file they came from
            images = [int(f.split("_")[1][0]) for f in batch["filepath"]]
            yield images, batch["filepath"].tolist(), None, None


def _make_thread(monkeypatch, n_rois, unreadable=()):
    db = FakeDB()
    monkeypatch.setattr(reid_thread, "get_path", lambda *_a, **_k: "/fake/model.onnx")
    monkeypatch.setattr(reid_thread.animl, "load_classifier", lambda *_a, **_k: (FakeModel(), None))
    monkeypatch.setattr(FakeManifestGenerator, "unreadable", set(unreadable))
    monkeypatch.setattr(reid_thread.animl, "ManifestGenerator", FakeManifestGenerator, raising=False)

    thread = reid_thread.ReIDThread.__new__(reid_thread.ReIDThread)
    thread.mpDB = db
    thread.device = "cpu"
    thread.batch_size = 1
    thread.viewpoint_filepath = "/fake/viewpoint.onnx"
    thread.reid_filepath = None
    thread.isInterruptionRequested = lambda: False
    thread.progress_update = SignalSpy()
    thread.failed = set()

    thread.rois = pd.DataFrame({
        "roi_id": list(range(n_rois)),
        "viewpoint": [None] * n_rois,
        "bbox_x": [0.1] * n_rois,
        "filepath": [f"/img_{i}.jpg" for i in range(n_rois)],
    })
    return thread, db


class TestGetViewpointBatching:
    def test_manifest_dataloader_attribute_no_longer_used(self):
        """animl.ManifestDataloader does not exist in the installed animl-lite
        package; the fix must reference ManifestGenerator instead."""
        assert not hasattr(reid_thread.animl, "ManifestDataloader")

    def test_each_roi_gets_its_own_viewpoint(self, monkeypatch):
        thread, db = _make_thread(monkeypatch, n_rois=7)

        thread.get_viewpoint()

        # the fake model's answer is the ROI's own image number
        assert [(call[1], call[2]["viewpoint"]) for call in db.edit_row_calls] == [(i, i) for i in range(7)]

    def test_unreadable_file_does_not_shift_later_viewpoints(self, monkeypatch):
        thread, db = _make_thread(monkeypatch, n_rois=4, unreadable={"/img_1.jpg"})

        thread.get_viewpoint()

        assert [(call[1], call[2]["viewpoint"]) for call in db.edit_row_calls] == [(0, 0), (2, 2), (3, 3)]
        assert thread.failed == {"/img_1.jpg"}

    def test_roi_without_box_is_skipped(self, monkeypatch):
        thread, db = _make_thread(monkeypatch, n_rois=3)
        thread.rois.loc[1, "bbox_x"] = -1

        thread.get_viewpoint()

        assert [call[1] for call in db.edit_row_calls] == [0, 2]

    def test_skips_when_no_viewpoint_model_selected(self, monkeypatch):
        thread, db = _make_thread(monkeypatch, n_rois=3)
        thread.viewpoint_filepath = None

        thread.get_viewpoint()

        assert db.edit_row_calls == []


class TestGetEmbeddings:
    def test_unreadable_file_is_skipped(self, monkeypatch):
        thread, db = _make_thread(monkeypatch, n_rois=3, unreadable={"/img_1.jpg"})
        thread.reid_filepath = "/fake/miew.onnx"
        thread.rois["emb"] = 0
        db.add_emb_calls = []
        db.add_emb = lambda roi_id, emb: db.add_emb_calls.append(roi_id)
        monkeypatch.setattr(reid_thread.animl, "load_miew", lambda *_a, **_k: None, raising=False)

        def _extract(_model, manifest):
            # like animl: stacking no results raises
            images = [batch[0] for batch in FakeManifestGenerator(manifest)]
            return np.vstack(images)

        monkeypatch.setattr(reid_thread.animl, "extract_miew_embeddings", _extract, raising=False)

        thread.get_embeddings()

        assert db.add_emb_calls == [0, 2]
        assert thread.failed == {"/img_1.jpg"}
