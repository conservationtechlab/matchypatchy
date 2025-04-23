"""
QThread for saving thumbnails to temp dir for media table
"""
import os
from pathlib import Path
import tempfile

from PyQt6.QtGui import QImage
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QRect

THUMBNAIL_NOTFOUND = QImage(os.path.join(os.path.dirname(__file__), "assets/thumbnail_notfound.png"))
# TODO THUMBNAIL_NOTFOUND = QImage(os.path.normpath("assets/logo.png"))


class LoadThumbnailThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    loaded_image = pyqtSignal(int, str)
    done = pyqtSignal()

    def __init__(self, mpDB, data, data_type=1):
        super().__init__()
        self.mpDB = mpDB
        self.data = data
        self.data_type = data_type
        self.size = 99

    def run(self):
        for i, roi in self.data.iterrows():
            # CHECK IF THREAD WAS PAUSED
            if not self.isInterruptionRequested():
                # check if thumbnail exists
                id = str(roi['id'])
                if self.data_type == 1:
                    existing_filepath = self.mpDB.select("roi_thumbnails", "filepath", row_cond=f"fid={id}")
                else:
                    existing_filepath = self.mpDB.select("media_thumbnails", "filepath", row_cond=f"fid={id}")

                if existing_filepath and Path(existing_filepath[0][0]).is_file():
                    filepath = existing_filepath[0][0]  # unlist
                # new thumbnail
                else:
                    # load image
                    self.original = QImage(roi['filepath'])
                    # image not found, use placeholder
                    if self.original.isNull():
                        self.image = QImage(THUMBNAIL_NOTFOUND)
                    else:
                        # crop for rois
                        if self.data_type == 1:
                            left = self.original.width() * roi['bbox_x']
                            top = self.original.height() * roi['bbox_y']
                            right = self.original.width() * roi['bbox_w']
                            bottom = self.original.height() * roi['bbox_h']
                            crop_rect = QRect(int(left), int(top), int(right), int(bottom))
                            self.image = self.original.copy(crop_rect)
                        # no crop for media
                        else:
                            self.image = self.original.copy()
                    # scale it to 99x99
                    scaled_image = self.image.scaled(self.size, self.size,
                                                    Qt.AspectRatioMode.KeepAspectRatio,
                                                    Qt.TransformationMode.SmoothTransformation)

                    # create a temporary file to hold thumbnail
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                        filepath = temp_file.name
                    # save the image
                    scaled_image.save(filepath, format="JPG")

                    # save to table
                    if self.data_type == 1:
                        self.mpDB.add_thumbnail("roi", id, filepath)
                    else:
                        self.mpDB.add_thumbnail("media", id, filepath)

                # emit thumbnail_path and progress update
                self.loaded_image.emit(i, filepath)
                self.progress_update.emit(int((i + 1) / len(self.data) * 100))

        if not self.isInterruptionRequested():
            self.done.emit()