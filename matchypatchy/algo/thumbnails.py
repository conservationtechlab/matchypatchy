"""
QThread for saving thumbnails to temp dir for media table
"""
import cv2
import random
from pathlib import Path

from PyQt6.QtGui import QImage
from PyQt6.QtCore import Qt, QRect

from matchypatchy.config import resource_path


THUMBNAIL_NOTFOUND = "assets/thumbnail_notfound.png"
THUMBNAIL_SIZE = 150

def save_media_thumbnail(thumbnail_dir, filepath, ext):
    # load video
    frame = 0
    if ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv']:
        original = get_frame(filepath, frame=frame)
    # load image
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
        thumbnail_filepath = f"{str(newpath)}_{frame}_{rand}.jpg"

        # save the image
        scaled_image.save(thumbnail_filepath, format="JPG")
                
    else:
        thumbnail_filepath = resource_path(THUMBNAIL_NOTFOUND)

    return thumbnail_filepath


def save_roi_thumbnail(thumbnail_dir, filepath, ext, frame, bbox_x, bbox_y, bbox_w, bbox_h):
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


# get specific frame of video as QImage
def get_frame(video_path, frame=0):
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
    else:
        table = "media_thumbnails"
        fid_col = "fid"
        source_table = "media"

    missing = mpDB._command(f"""
        SELECT {source_table}.id FROM {source_table}
        LEFT JOIN {table} ON {source_table}.id = {table}.{fid_col}
        WHERE {table}.{fid_col} IS NULL;
    """)

    missing_ids = [row[0] for row in missing]
    return missing_ids