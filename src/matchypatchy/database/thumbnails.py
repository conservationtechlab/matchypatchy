"""
QThread for saving thumbnails to temp dir for media table
"""
import logging
from pathlib import Path
import random

import cv2
import pandas as pd

from PyQt6.QtGui import QImage
from PyQt6.QtCore import Qt, QRect

from matchypatchy.config import asset_path


THUMBNAIL_NOTFOUND = "graphics/thumbnail_notfound.png"
THUMBNAIL_NOBBOX = "graphics/thumbnail_nobbox.png"
THUMBNAIL_SIZE = 150
VIDEO_EXT = ['.mp4', '.avi', '.mov', '.mkv', '.wmv']

logger = logging.getLogger(__name__)


def load_image(filepath):
    """
    Load an image file as QImage, reading the bytes with Python rather than
    letting Qt open the path. Qt can fail to open files on Windows mapped or
    network drives that Python reads fine, which returned a silent null image.
    """
    try:
        with open(filepath, "rb") as f:
            data = f.read()
    except OSError as e:
        logger.error(f"Could not read {filepath} for thumbnail: {e}")
        return None
    image = QImage.fromData(data)
    if image.isNull():
        logger.error(f"Could not decode {filepath} for thumbnail")
        return None
    return image


def load_media(filepath, ext, frame=0):
    """Load the given frame of a video, or the image itself, as QImage"""
    if ext in VIDEO_EXT:
        image = get_frame(filepath, frame=frame)
        if image is None:
            logger.error(f"Could not read frame {frame} of {filepath} for thumbnail")
        return image
    return load_image(filepath)


def save_thumbnail(thumbnail_dir, filepath, image):
    """Scale image to thumbnail size and save it, returning the thumbnail filename"""
    scaled_image = image.scaled(THUMBNAIL_SIZE, THUMBNAIL_SIZE,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation)
    rand = random.randint(1000, 9999)
    thumbnail_filepath = f"{str(Path(filepath).stem)}_{rand}.jpg"
    if not scaled_image.save(str(Path(thumbnail_dir) / thumbnail_filepath), format="JPG"):
        logger.error(f"Could not save thumbnail for {filepath} to {thumbnail_dir}")
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
    original = load_media(filepath, ext, frame=frame)
    if original is None:
        return str(asset_path(THUMBNAIL_NOTFOUND))

    # crop for rois
    left = original.width() * bbox_x
    top = original.height() * bbox_y
    width = original.width() * bbox_w
    height = original.height() * bbox_h
    image = original.copy(QRect(int(left), int(top), int(width), int(height)))
    return save_thumbnail(thumbnail_dir, filepath, image)


def get_frame(video_path, frame=0):
    """Extract a given frame from video as QImage"""
    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
    ret, still = cap.read()  # Read the first frame
    cap.release()

    if ret:
        rgb_frame = cv2.cvtColor(still, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        # copy so the QImage owns its pixels instead of pointing at the numpy buffer
        qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        return qimg
    return None


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
    missing_ids = [row[0] for row in missing]

    # Also check for files that are listed but the file is missing
    for _, row in thumbnails.iterrows():
        if not (Path(thumbnail_dir) / Path(row['thumbnail_path'])).is_file():
            missing_ids.append(row['id'])
        if row['thumbnail_path'] == str(asset_path(THUMBNAIL_NOTFOUND)):
            missing_ids.append(row['id'])

    return missing_ids


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
