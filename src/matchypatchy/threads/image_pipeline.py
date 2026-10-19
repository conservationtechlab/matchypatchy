"""
Load media once and prepare model inputs from the image in memory

animl's generators read the file from disk for every model (detector, viewpoint,
re-id) and every roi. Processing decodes each image / video frame once and
builds every model input from it. Preprocessing reuses animl's own
ManifestGenerator steps so inputs are identical to animl's.
"""
import logging
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image

from animl import detection as animl_detection
from animl.generator import ManifestGenerator

from matchypatchy.database.media import VIDEO_EXT

logger = logging.getLogger(__name__)

MEGADETECTORv1000_SIZE = 960
VIEWPOINT_SIZE = 480
MIEWID_SIZE = 440
MIEWID_NORMALIZE = {"mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]}


# LOADING ======================================================================
def is_video(filepath):
    """Whether the file is a video, by extension"""
    return Path(str(filepath)).suffix.lower() in VIDEO_EXT


def load_image(filepath):
    """Image file as RGB PIL image, None if it can't be read"""
    try:
        with Image.open(filepath) as img:
            return img.convert("RGB")
    except OSError as e:
        logger.error(f"Cannot open image {filepath}: {e}")
        return None


def read_video_frames(filepath, frames):
    """
    {frame: RGB PIL image} for the requested frames, opening the video once.
    Frames that can't be read are left out.
    """
    out = {}
    cap = cv2.VideoCapture(str(filepath))
    try:
        if not cap.isOpened():
            logger.error(f"Cannot open video {filepath}")
            return out
        for frame in sorted({int(f) for f in frames}):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, img = cap.read()
            if not ok:
                logger.error(f"Cannot read frame {frame} from {filepath}")
                continue
            out[frame] = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    finally:
        cap.release()
    return out


def load_frames(filepath, frames):
    """{frame: RGB PIL image}: frame 0 of an image file, or the requested video frames"""
    if is_video(filepath):
        return read_video_frames(filepath, frames)
    image = load_image(filepath)
    return {} if image is None else {0: image}


# PREPROCESSING ================================================================
class Preprocessor:
    """
    Model input from an image already in memory, matching animl.ManifestGenerator

    Uses the generator's own crop / resize / normalize steps in the order of
    ManifestGenerator._load_item (animl-lite is pinned in pyproject.toml).
    """

    def __init__(self, width, height, crop=False, normalize=True, letterbox=False):
        # used for its preprocessing steps only, never iterated; the bbox columns must be
        # present or ManifestGenerator turns cropping off
        template = pd.DataFrame(columns=["filepath", "frame", "bbox_x", "bbox_y", "bbox_w", "bbox_h"])
        self._gen = ManifestGenerator(template,
                                      resize_width=width, resize_height=height,
                                      crop=crop, normalize=normalize, letterbox=letterbox,
                                      batch_size=1, num_workers=0)

    def __call__(self, image, bbox=None):
        """
        (CHW float32 array, (height, width) of the full image)

        bbox: {'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h'} relative coordinates, used when cropping
        """
        gen = self._gen
        width, height = image.size
        if gen.crop:
            image = gen._apply_crop(image, bbox or {}, width, height)
        if gen.letterbox:
            image = gen._letterbox_resize(image)
        else:
            image = image.resize((gen.resize_width, gen.resize_height), Image.BILINEAR)
        arr = gen._pil_to_numpy(image)
        if isinstance(gen.normalize, dict):
            arr = gen._normalize(arr,
                                 mean=gen.normalize.get("mean", [0.485, 0.456, 0.406]),
                                 std=gen.normalize.get("std", [0.229, 0.224, 0.225]))
        elif gen.normalize is False:
            arr = arr * 255.0
        return arr, np.array((height, width), dtype=np.int32)


def detector_preprocessor():
    """Detector input as animl.detect builds it (letterboxed, [0, 1], not cropped)"""
    return Preprocessor(MEGADETECTORv1000_SIZE, MEGADETECTORv1000_SIZE, crop=False, normalize=True, letterbox=True)


def viewpoint_preprocessor():
    """Viewpoint classifier input as ReIDThread built it (roi crop, [0, 1])"""
    return Preprocessor(VIEWPOINT_SIZE, VIEWPOINT_SIZE, crop=True)


def miewid_preprocessor():
    """MiewID input as animl.extract_miew_embeddings builds it (roi crop, ImageNet normalized)"""
    return Preprocessor(MIEWID_SIZE, MIEWID_SIZE, crop=True, normalize=MIEWID_NORMALIZE)


# MODELS =======================================================================
def run_model(model, arr):
    """Run an ONNX session on a single preprocessed image, return its first output"""
    return model.run(None, {model.get_inputs()[0].name: arr[np.newaxis].astype(np.float32)})[0]


def detect_animals(detector, preprocess, image, filepath, frame=0,
                   confidence_threshold=0.1, calculate_clarity=False):
    """
    Animal detections in an image in memory, as animl.detect + parse_detections + get_animals give them

    Returns a list of dicts with bbox_x/y/w/h (relative, clipped to 0-1), conf and,
    with calculate_clarity, clarity and score.
    """
    arr, hw = preprocess(image)
    batch = (arr[np.newaxis].astype(np.float32), [str(filepath)],
             np.array([int(frame)], dtype=np.int32), hw[np.newaxis])
    outputs = detector.run(None, {detector.get_inputs()[0].name: batch[0]})[0]
    results = animl_detection._convert_detections(outputs, batch, True,
                                                  confidence_threshold=confidence_threshold,
                                                  model_type=detector.model_type,
                                                  calculate_clarity=calculate_clarity)
    animals = []
    for det in results[0]["detections"]:
        # parse_detections keeps conf > 0 and clips boxes; get_animals keeps animals
        if det["category_label"] != "animal" or not det["conf"] > 0:
            continue
        det = dict(det)
        for key in ("bbox_x", "bbox_y", "bbox_w", "bbox_h"):
            det[key] = float(np.clip(det[key], 0, 1))
        animals.append(det)
    return animals


def bbox_of(row):
    """
    Relative bbox dict from a roi row or detection, rounded to 4 decimals as add_roi stores it

    Detector boxes come from float32 math (0.0339 is 0.033900000154972076); cropping with the
    stored values keeps thumbnails, viewpoints and embeddings consistent with later re-runs
    """
    return {key: float(round(float(row[key]), 4)) for key in ("bbox_x", "bbox_y", "bbox_w", "bbox_h")}


def has_bbox(row):
    """Imported rois without a box have bbox_x == -1"""
    return row["bbox_x"] is not None and not pd.isna(row["bbox_x"]) and float(row["bbox_x"]) >= 0
