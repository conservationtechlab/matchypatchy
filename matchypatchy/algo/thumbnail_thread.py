"""
QThread for saving thumbnails to temp dir for media table
"""
import cv2
import random
from pathlib import Path

from PyQt6.QtGui import QImage
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QRect

from matchypatchy import config
from concurrent.futures import ThreadPoolExecutor, as_completed


THUMBNAIL_NOTFOUND = config.resource_path("assets/thumbnail_notfound.png")


class LoadThumbnailThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    loaded_images = pyqtSignal(list)
    done = pyqtSignal()

    def __init__(self, mpDB, data, data_type=1, size=150):
        super().__init__()
        self.mpDB = mpDB
        self.data = data
        self.data_type = data_type
        self.size = size
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

    # create a new thumbnail
    def save_image(self, roi):
        frame = roi['frame'] if 'frame' in roi.index else 0
        # load video
        if roi['ext'].lower() in ['.mp4', '.avi', '.mov', '.mkv', '.wmv']:
            if self.data_type == 1:
                self.original = self.get_frame(roi['filepath'], frame=frame)
            else:
                # rois/frames not yet processed, use first frame
                self.original = self.get_frame(roi['filepath'], frame=frame)
        # load image
        else:
            self.original = QImage(roi['filepath'])
            # image not found, use placeholder

        if not self.original.isNull():
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
            rand = random.randint(1000, 9999)
            newpath = Path(self.thumbnail_dir) / Path(roi['filepath']).stem
            filepath = f"{str(newpath)}_{frame}_{rand}.jpg"

            # save the image
            scaled_image.save(filepath, format="JPG")

            # save to table
            if self.data_type == 1:
                self.mpDB.add_thumbnail("roi", roi['id'], filepath)
            else:
                self.mpDB.add_thumbnail("media", roi['id'], filepath)
                    
        else:
            filepath = THUMBNAIL_NOTFOUND

        return filepath
    
    # get specific frame of video as QImage
    def get_frame(self, video_path, frame=0):
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