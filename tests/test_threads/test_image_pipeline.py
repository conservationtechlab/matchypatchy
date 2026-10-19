"""
image_pipeline: model inputs from images in memory must match animl's own

Processing reads each file once and builds every model input from it, so the
inputs have to be identical to what animl.ManifestGenerator / animl.detect
build when they read the file themselves.
"""
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from PIL import Image

import animl
from animl.generator import ManifestGenerator

from matchypatchy.threads import image_pipeline as ip

BBOX = {"bbox_x": 0.2345, "bbox_y": 0.1111, "bbox_w": 0.5, "bbox_h": 0.6789}


@pytest.fixture
def image_file(tmp_path):
    """A noisy 640x480 photo-like jpg (so resampling differences would show)"""
    rng = np.random.default_rng(0)
    arr = rng.integers(0, 255, size=(480, 640, 3), dtype=np.uint8)
    path = tmp_path / "photo.jpg"
    Image.fromarray(arr).save(path, quality=95)
    return str(path)


def _reference(path, **kwargs):
    """Input exactly as ManifestGenerator builds it when reading the file"""
    manifest = pd.DataFrame([dict(BBOX, filepath=path, frame=0)])
    gen = ManifestGenerator(manifest, batch_size=1, num_workers=0, **kwargs)
    return gen._load_item(0)


@pytest.mark.parametrize("make_prep,kwargs", [
    (ip.detector_preprocessor, dict(resize_width=960, resize_height=960, crop=False, normalize=True, letterbox=True)),
    (ip.viewpoint_preprocessor, dict(resize_width=480, resize_height=480, crop=True)),
    (ip.miewid_preprocessor, dict(resize_width=440, resize_height=440, crop=True, normalize=ip.MIEWID_NORMALIZE)),
])
def test_inputs_identical_to_manifest_generator(image_file, make_prep, kwargs):
    ref = _reference(image_file, **kwargs)
    arr, hw = make_prep()(ip.load_image(image_file), BBOX)
    assert arr.dtype == ref[0].dtype
    np.testing.assert_array_equal(arr, ref[0])
    np.testing.assert_array_equal(hw, ref[3])


def test_cropping_preprocessors_crop(image_file):
    """ManifestGenerator turns cropping off without bbox columns; ours must keep it on"""
    image = ip.load_image(image_file)
    cropped, _ = ip.viewpoint_preprocessor()(image, BBOX)
    whole, _ = ip.viewpoint_preprocessor()(image, {"bbox_x": 0, "bbox_y": 0, "bbox_w": 1, "bbox_h": 1})
    assert not np.array_equal(cropped, whole)


class FakeDetector:
    """ONNX-like detector: one animal box in letterboxed input pixels, plus one low-confidence vehicle"""
    model_type = "megadetector"

    def get_inputs(self):
        return [SimpleNamespace(name="images")]

    def run(self, _names, feed):
        n = feed["images"].shape[0]
        boxes = np.array([[100, 300, 500, 700, 0.9, 0],    # animal (class 0 -> 1)
                          [10, 20, 30, 40, 0.05, 2]],      # vehicle below threshold
                         dtype=np.float32)
        return [np.repeat(boxes[np.newaxis], n, axis=0)]


def test_detect_animals_matches_animl_detect(image_file):
    detector = FakeDetector()
    manifest = pd.DataFrame([{"filepath": image_file, "frame": 0}])
    ref = animl.get_animals(animl.parse_detections(
        animl.detect(detector, manifest.copy(), 960, 960, batch_size=1, use_progress_bar=False), manifest=manifest))
    ours = ip.detect_animals(detector, ip.detector_preprocessor(), ip.load_image(image_file), image_file)
    assert len(ours) == len(ref) == 1
    for key in ("bbox_x", "bbox_y", "bbox_w", "bbox_h", "conf"):
        assert ours[0][key] == pytest.approx(float(ref.iloc[0][key]))


def test_detect_animals_scores_frames_for_videos(image_file, monkeypatch):
    # cv2 (used for clarity) is stubbed in the test suite
    from animl import detection
    monkeypatch.setattr(detection, "_laplacian_variance", lambda _img: 250.0)
    ours = ip.detect_animals(FakeDetector(), ip.detector_preprocessor(), ip.load_image(image_file), image_file,
                             calculate_clarity=True)
    assert ours[0]["clarity"] == 0.5
    assert ours[0]["score"] == pytest.approx(0.4 * ours[0]["conf"] + 0.3 * ours[0]["bbox_w"] * ours[0]["bbox_h"] + 0.15)


class TestLoading:
    def test_unreadable_image(self, tmp_path):
        assert ip.load_image(tmp_path / "missing.jpg") is None
        assert ip.load_frames(tmp_path / "missing.jpg", {0}) == {}

    def test_video_opened_once_for_all_frames(self, tmp_path, monkeypatch):
        """cv2 is stubbed in the test suite; a fake capture stands in for a 10-frame video"""
        opened = []

        class FakeCapture:
            def __init__(self, path):
                opened.append(path)
                self.pos = 0

            def isOpened(self):
                return True

            def set(self, _prop, value):
                self.pos = int(value)

            def read(self):
                if self.pos >= 10:
                    return False, None
                return True, np.full((48, 64, 3), self.pos * 25, dtype=np.uint8)

            def release(self):
                pass

        monkeypatch.setattr(ip.cv2, "VideoCapture", FakeCapture)
        monkeypatch.setattr(ip.cv2, "cvtColor", lambda img, _code: img[..., ::-1])
        frames = ip.load_frames(tmp_path / "clip.mp4", [7, 2, 2, 50])   # 50 is past the end
        assert len(opened) == 1
        assert sorted(frames) == [2, 7]
        assert frames[7].size == (64, 48)
        assert np.asarray(frames[7]).mean() == 175


class TestBoxes:
    def test_bbox_rounded_as_stored(self):
        """Detector boxes are float32 values; crops use the 4-decimal values add_roi stores"""
        det = {"bbox_x": 0.033900000154972076, "bbox_y": 0.5, "bbox_w": 0.9660999774932861, "bbox_h": 0.25}
        assert ip.bbox_of(det) == {"bbox_x": 0.0339, "bbox_y": 0.5, "bbox_w": 0.9661, "bbox_h": 0.25}

    @pytest.mark.parametrize("value,expected", [(0.1, True), (0, True), (-1, False), (None, False), (np.nan, False)])
    def test_has_bbox(self, value, expected):
        assert ip.has_bbox({"bbox_x": value}) is expected
