"""
QThread for saving thumbnails to temp dir for media table
"""
import cv2
import random
import pandas as pd
from pathlib import Path

from PyQt6.QtGui import QImage
from PyQt6.QtCore import Qt, QRect

from matchypatchy.config import resource_path


THUMBNAIL_NOTFOUND = "assets/graphics/thumbnail_notfound.png"
THUMBNAIL_SIZE = 150


def save_media_thumbnail(thumbnail_dir, filepath, ext):
    """Save thumbnail for full media file"""
    if ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv']:
        # use first frame for video
        original = get_frame(filepath, frame=0)
    else:
        original = QImage(filepath)

    if not original.isNull():
        # crop for rois
        image = original.copy()
        # scale it to 150x150
        scaled_image = image.scaled(THUMBNAIL_SIZE, THUMBNAIL_SIZE,
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)

        # create a temporary file to hold thumbnail
        rand = random.randint(1000, 9999)
        newpath = Path(thumbnail_dir) / Path(filepath).stem
        thumbnail_filepath = f"{str(newpath)}_{rand}.jpg"
        # save the image
        scaled_image.save(thumbnail_filepath, format="JPG")
    else:
        thumbnail_filepath = resource_path(THUMBNAIL_NOTFOUND)

    return thumbnail_filepath


def save_roi_thumbnail(thumbnail_dir, filepath, ext, frame, bbox_x, bbox_y, bbox_w, bbox_h):
    """Save thumbnail for ROI given bbox coordinates"""
    original = QImage(filepath)
    if ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv']:
        original = get_frame(filepath, frame=frame)
    else:
        original = QImage(filepath)

    if not original.isNull():
        # crop for rois
        left = original.width() * bbox_x
        top = original.height() * bbox_y
        right = original.width() * bbox_w
        bottom = original.height() * bbox_h
        crop_rect = QRect(int(left), int(top), int(right), int(bottom))
        image = original.copy(crop_rect)

        # scale it to 150x150
        scaled_image = image.scaled(THUMBNAIL_SIZE, THUMBNAIL_SIZE,
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)

        # create a temporary file to hold thumbnail
        rand = random.randint(1000, 9999)
        newpath = Path(thumbnail_dir) / Path(filepath).stem
        thumbnail_filepath = f"{str(newpath)}_{frame}_{rand}.jpg"

        # save the image
        scaled_image.save(thumbnail_filepath, format="JPG")
    else:
        thumbnail_filepath = resource_path(THUMBNAIL_NOTFOUND)

    return thumbnail_filepath


def get_frame(video_path, frame=0):
    """Extract a given frame from video as QImage"""
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
    ret, still = cap.read()  # Read the first frame
    cap.release()

    if ret:
        rgb_frame = cv2.cvtColor(still, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    return qimg


def check_missing_thumbnails(mpDB, data_type):
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
    for t, row in thumbnails.iterrows():
        if not Path(row['thumbnail_path']).is_file():
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
