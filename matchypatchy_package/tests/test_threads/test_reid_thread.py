"""Tests for matchypatchy.threads.reid_thread — viewpoint batching regression."""
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
    """Stand-in ONNX model: returns one row of "logits" per image in the batch."""

    def get_inputs(self):
        return [SimpleNamespace(name="input")]

    def run(self, _output_names, feed):
        images = feed["input"]
        n = len(images)
        # class index == position in the batch, so we can tell results apart
        logits = np.zeros((n, n if n > 0 else 1))
        for i in range(n):
            logits[i, i % logits.shape[1]] = 10.0
        return [logits]


class FakeDB:
    def __init__(self):
        self.edit_row_calls = []

    def edit_row(self, table, row_id, replace, **kwargs):
        self.edit_row_calls.append((table, row_id, replace))
        return True


class FakeManifestGenerator:
    """Mimics animl.ManifestGenerator: yields (images, filepaths, frames, hw) batches."""

    def __init__(self, manifest, **kwargs):
        self.manifest = manifest.reset_index(drop=True)
        self.batch_size = kwargs.get("batch_size", 16)

    def __iter__(self):
        n = len(self.manifest)
        for start in range(0, n, self.batch_size):
            end = min(start + self.batch_size, n)
            batch = self.manifest.iloc[start:end]
            images = list(range(len(batch)))  # placeholder "images"
            filepaths = batch["filepath"].tolist()
            yield images, filepaths, None, None


def _make_thread(monkeypatch, n_rois, batch_size):
    db = FakeDB()
    monkeypatch.setattr(reid_thread, "get_path", lambda *_a, **_k: "/fake/model.onnx")
    monkeypatch.setattr(reid_thread.animl, "load_classifier", lambda *_a, **_k: (FakeModel(), None))
    monkeypatch.setattr(reid_thread.animl, "ManifestGenerator", FakeManifestGenerator, raising=False)

    thread = reid_thread.ReIDThread.__new__(reid_thread.ReIDThread)
    thread.mpDB = db
    thread.device = "cpu"
    thread.batch_size = batch_size
    thread.viewpoint_filepath = "/fake/viewpoint.onnx"
    thread.reid_filepath = None
    thread.isInterruptionRequested = lambda: False
    thread.progress_update = SignalSpy()

    thread.rois = pd.DataFrame({
        "roi_id": list(range(n_rois)),
        "viewpoint": [None] * n_rois,
        "filepath": [f"/img_{i}.jpg" for i in range(n_rois)],
    })
    return thread, db


class TestGetViewpointBatching:
    def test_manifest_dataloader_attribute_no_longer_used(self):
        """animl.ManifestDataloader does not exist in the installed animl-lite
        package; the fix must reference ManifestGenerator instead."""
        assert not hasattr(reid_thread.animl, "ManifestDataloader")

    def test_processes_every_roi_across_multiple_batches(self, monkeypatch):
        # 7 ROIs needing a viewpoint, batch_size=4 -> batches of 4 and 3.
        # Every ROI must get exactly one edit_row call, attached to the
        # correct roi_id (not just the first item of each batch).
        thread, db = _make_thread(monkeypatch, n_rois=7, batch_size=4)

        thread.get_viewpoint()

        processed_roi_ids = [call[1] for call in db.edit_row_calls]
        assert processed_roi_ids == list(range(7))
        assert len(db.edit_row_calls) == 7

    def test_single_item_batch_still_works(self, monkeypatch):
        thread, db = _make_thread(monkeypatch, n_rois=3, batch_size=1)

        thread.get_viewpoint()

        processed_roi_ids = [call[1] for call in db.edit_row_calls]
        assert processed_roi_ids == [0, 1, 2]

    def test_skips_when_no_viewpoint_model_selected(self, monkeypatch):
        thread, db = _make_thread(monkeypatch, n_rois=3, batch_size=4)
        thread.viewpoint_filepath = None

        thread.get_viewpoint()

        assert db.edit_row_calls == []
