"""
QThread for saving thumbnails to temp dir for media table
"""
import logging
import os
from pathlib import Path
import uuid

import cv2
import numpy as np
import pandas as pd

from PyQt6.QtGui import QImage, QImageReader
from PyQt6.QtCore import QBuffer, QByteArray, QIODevice

from matchypatchy.config import asset_path


THUMBNAIL_NOTFOUND = "graphics/thumbnail_notfound.png"
THUMBNAIL_NOBBOX = "graphics/thumbnail_nobbox.png"
THUMBNAIL_SIZE = 200
VIDEO_EXT = ['.mp4', '.avi', '.mov', '.mkv', '.wmv']
JPEG_QUALITY = 75  # Qt's default, which thumbnails were saved with before
# OpenCV flags that decode straight to 1/scale of the full size
DECODE_FLAGS = {1: cv2.IMREAD_COLOR, 2: cv2.IMREAD_REDUCED_COLOR_2,
                4: cv2.IMREAD_REDUCED_COLOR_4, 8: cv2.IMREAD_REDUCED_COLOR_8}

logger = logging.getLogger(__name__)


def read_bytes(filepath):
    """
    Read a file's bytes with Python rather than letting Qt or OpenCV open the path.
    Both can fail to open files on Windows mapped or network drives that Python
    reads fine, and OpenCV cannot open non-ASCII paths on Windows.
    """
    try:
        with open(filepath, "rb") as f:
            return f.read()
    except OSError as e:
        logger.error(f"Could not read {filepath} for thumbnail: {e}")
        return None


def load_image(filepath, crop=(1.0, 1.0)):
    """
    Load an image file as a BGR array, decoded only as large as the thumbnail needs.

    crop is the (width, height) fraction of the image that will be cut out and shrunk
    to a thumbnail. JPEGs can be decoded straight to 1/2, 1/4 or 1/8 size, which is far
    cheaper than a full decode, so the smallest size that still leaves the crop at least
    THUMBNAIL_SIZE pixels is used. EXIF orientation is ignored, as it was with Qt, so
    stored bounding boxes still line up with the pixels.
    """
    data = read_bytes(filepath)
    if data is None:
        return None
    width, height = _image_size(data)
    scale = _decode_scale(width * crop[0], height * crop[1])
    image = cv2.imdecode(np.frombuffer(data, np.uint8), DECODE_FLAGS[scale] | cv2.IMREAD_IGNORE_ORIENTATION)
    if image is None:
        logger.error(f"Could not decode {filepath} for thumbnail")
    return image


def _image_size(data):
    """
    (width, height) of an encoded image, read from its header without decoding it.

    Called by load_image to pick a decode scale before decoding; (0, 0) if the header
    cannot be read, which makes _decode_scale fall back to a full decode. Kept separate
    so the Qt buffer plumbing stays out of load_image.
    """
    buffer = QBuffer()
    buffer.setData(QByteArray(data))
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    size = QImageReader(buffer).size()
    return max(size.width(), 0), max(size.height(), 0)


def _decode_scale(crop_width, crop_height):
    """
    Largest decode reduction that keeps a crop of this many full-size pixels at least THUMBNAIL_SIZE.

    Called by load_image; kept separate so the rule can be tested without decoding images.
    """
    longest = max(crop_width, crop_height)
    for scale in (8, 4, 2):
        if longest / scale >= THUMBNAIL_SIZE:
            return scale
    return 1


def load_media(filepath, ext, frame=0, crop=(1.0, 1.0)):
    """Load the given frame of a video, or the image itself, as a BGR array"""
    if ext in VIDEO_EXT:
        image = read_frame(filepath, frame=frame)
        if image is None:
            logger.error(f"Could not read frame {frame} of {filepath} for thumbnail")
        return image
    return load_image(filepath, crop=crop)


def save_thumbnail(thumbnail_dir, filepath, image):
    """Scale a BGR image to fit THUMBNAIL_SIZE and save it, returning the thumbnail filename"""
    height, width = image.shape[:2]
    if not width or not height:
        logger.error(f"Nothing to save as a thumbnail for {filepath}")
        return str(asset_path(THUMBNAIL_NOTFOUND))
    factor = THUMBNAIL_SIZE / max(width, height)
    size = (max(1, round(width * factor)), max(1, round(height * factor)))
    interpolation = cv2.INTER_AREA if factor < 1 else cv2.INTER_LINEAR
    scaled_image = cv2.resize(image, size, interpolation=interpolation)
    # unique suffix, camera trap filenames (e.g. IMG_0001) repeat across folders and
    # every roi of a media file shares its stem, so a short random number collides
    thumbnail_filepath = f"{str(Path(filepath).stem)}_{uuid.uuid4().hex}.jpg"
    encoded, buffer = cv2.imencode(".jpg", scaled_image, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    try:
        if not encoded:
            raise OSError("JPEG encoding failed")
        with open(Path(thumbnail_dir) / thumbnail_filepath, "wb") as f:
            f.write(buffer.tobytes())
    except OSError as e:
        logger.error(f"Could not save thumbnail for {filepath} to {thumbnail_dir}: {e}")
        return str(asset_path(THUMBNAIL_NOTFOUND))
    return thumbnail_filepath


def save_media_thumbnail(thumbnail_dir, filepath, ext):
    """Save thumbnail for full media file"""
    original = load_media(filepath, ext, frame=0)
    if original is None:
        return str(asset_path(THUMBNAIL_NOTFOUND))
    return save_thumbnail(thumbnail_dir, filepath, original)


def save_roi_thumbnail(thumbnail_dir, filepath, ext, frame, bbox_x, bbox_y, bbox_w, bbox_h):
    """Save thumbnail for ROI given bbox coordinates"""
    original = load_media(filepath, ext, frame=frame, crop=(bbox_w, bbox_h))
    if original is None:
        return str(asset_path(THUMBNAIL_NOTFOUND))

    # crop for rois, clipped to the image so a box running off the edge still crops
    height, width = original.shape[:2]
    left = min(max(int(width * bbox_x), 0), width)
    top = min(max(int(height * bbox_y), 0), height)
    right = min(left + int(width * bbox_w), width)
    bottom = min(top + int(height * bbox_h), height)
    image = original[top:bottom, left:right]
    return save_thumbnail(thumbnail_dir, filepath, image)


def read_frame(video_path, frame=0):
    """Extract a given frame from video as a BGR array"""
    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
    ret, still = cap.read()
    cap.release()
    return still if ret else None


def get_frame(video_path, frame=0):
    """Extract a given frame from video as QImage"""
    still = read_frame(video_path, frame=frame)
    if still is None:
        return None
    rgb_frame = cv2.cvtColor(still, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_frame.shape
    bytes_per_line = ch * w
    # copy so the QImage owns its pixels instead of pointing at the numpy buffer
    return QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()


def check_missing_thumbnails(mpDB, thumbnail_dir, data_type):
    """
    Check for missing thumbnails in roi or media table
    """
    if data_type == 1:
        table = "roi_thumbnails"
        fid_col = "fid"
        source_table = "roi"
        thumbnails = fetch_roi_thumbnails(mpDB)
    else:
        table = "media_thumbnails"
        fid_col = "fid"
        source_table = "media"
        thumbnails = fetch_media_thumbnails(mpDB)

    # Find ids in source_table that do not have entries in thumbnails table
    missing = mpDB._command(f"""SELECT {source_table}.id FROM {source_table}
                            LEFT JOIN {table} ON {source_table}.id = {table}.{fid_col}
                            WHERE {table}.{fid_col} IS NULL;""", quiet=True)
    # _command returns None if the query failed (already logged)
    missing_ids = [row[0] for row in missing] if missing else []

    # Also check for files that are listed but the file is missing, or that are the not-found placeholder
    # list the directory once instead of a stat per thumbnail, which is slow on network drives
    existing = _list_files(thumbnail_dir)
    placeholder = str(asset_path(THUMBNAIL_NOTFOUND))
    for fid, thumbnail_path in zip(thumbnails['id'], thumbnails['thumbnail_path']):
        if thumbnail_path == placeholder or not _thumbnail_exists(thumbnail_dir, thumbnail_path, existing):
            missing_ids.append(fid)

    return missing_ids


def _list_files(directory):
    """
    Names of the files directly in directory, empty if it cannot be read.

    Called by check_missing_thumbnails, so one directory listing answers whether
    each thumbnail exists; kept separate so the OSError handling stays out of that loop.
    """
    try:
        with os.scandir(directory) as entries:
            return {entry.name for entry in entries if entry.is_file()}
    except OSError as e:
        logger.error(f"Could not list thumbnails in {directory}: {e}")
        return set()


def _thumbnail_exists(thumbnail_dir, thumbnail_path, existing):
    """
    Whether a stored thumbnail path points at a file.

    Called by check_missing_thumbnails per thumbnail row. Plain filenames, which is
    what save_thumbnail stores, are looked up in the directory listing `existing`;
    anything else (absolute or nested paths, e.g. from older databases) falls back
    to a stat. Kept separate so that fallback rule lives in one place.
    """
    if not thumbnail_path:
        return False
    if os.path.basename(thumbnail_path) == thumbnail_path:
        return thumbnail_path in existing
    return (Path(thumbnail_dir) / Path(thumbnail_path)).is_file()


def fetch_roi_thumbnails(mpDB):
    """
    Get roi thumbnail paths
    """
    thumbnails = mpDB.select("roi_thumbnails", columns="fid, filepath")
    if thumbnails:
        thumbnails = pd.DataFrame(thumbnails, columns=["id", "thumbnail_path"])
    else:
        thumbnails = pd.DataFrame(columns=["id", "thumbnail_path"])
    thumbnails = thumbnails.replace({float('nan'): None})
    return thumbnails


def fetch_media_thumbnails(mpDB):
    """
    Get media thumbnail paths
    """
    thumbnails = mpDB.select("media_thumbnails", columns="fid, filepath")
    if thumbnails:
        thumbnails = pd.DataFrame(thumbnails, columns=["id", "thumbnail_path"])
    else:
        thumbnails = pd.DataFrame(columns=["id", "thumbnail_path"])
    thumbnails = thumbnails.replace({float('nan'): None})
    return thumbnails
