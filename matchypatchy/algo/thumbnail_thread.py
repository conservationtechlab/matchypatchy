"""
QThread for saving thumbnails to temp dir for media table
"""
import os
from pathlib import Path

from PyQt6.QtGui import QImage
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QRect

from matchypatchy import config
from concurrent.futures import ThreadPoolExecutor, as_completed

THUMBNAIL_NOTFOUND = QImage(os.path.join(os.path.dirname(__file__), "assets/thumbnail_notfound.png"))
# TODO THUMBNAIL_NOTFOUND = QImage(os.path.normpath("assets/logo.png"))


class LoadThumbnailThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    loaded_images = pyqtSignal(list)
    done = pyqtSignal()

    def __init__(self, mpDB, data, data_type=1):
        super().__init__()
        self.mpDB = mpDB
        self.data = data
        self.data_type = data_type
        self.size = 99
        if self.data_type == 1:
            self.existing_filepaths = dict(self.mpDB.select("roi_thumbnails", "fid, filepath"))
        else:
            self.existing_filepaths = dict(self.mpDB.select("media_thumbnails", "fid, filepath"))
        self.thumbnail_dir = config.load('THUMBNAIL_DIR')
        

    def run(self):
        filepaths = []

        #TODO: break into chunks so thread can be interupted 

        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self.process_image, roi): roi for _,roi in self.data.iterrows()}

            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                filepaths.append(result)
                self.progress_update.emit(int((i + 1) / len(self.data) * 100))

        self.loaded_images.emit(filepaths)
        self.done.emit()


    def process_image(self, roi):
        id = roi['id']
        try:
            filepath = self.existing_filepaths[id]
            if not Path(filepath).is_file():
                filepath = self.save_image(roi)

        except KeyError:
            filepath = self.save_image(roi)

        return id, filepath


    def save_image(self, roi):
        # create a new thumbnail
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
        filepath = Path(self.thumbnail_dir) / Path(self.original).name
        # save the image
        scaled_image.save(filepath, format="JPG")

        # save to table
        if self.data_type == 1:
            self.mpDB.add_thumbnail("roi", roi['id'], filepath)
        else:
            self.mpDB.add_thumbnail("media", roi['id'], filepath)

        return filepath