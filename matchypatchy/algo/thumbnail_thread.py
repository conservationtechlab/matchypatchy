from PyQt6.QtCore import QThread, pyqtSignal

import tempfile

from PyQt6.QtGui import QImage
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QRect

THUMBNAIL_NOTFOUND = '/home/kyra/matchypatchy/matchypatchy/gui/assets/thumbnail_notfound.png'

# TODO: SAVE THUMBNAIL TO TABLE

class LoadThumbnailThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    loaded_image = pyqtSignal(int, str)

    def __init__(self, data, crop=True):
        super().__init__()
        self.data = data
        self.crop = crop
        self.size = 99
    
    def run(self):
        for i, roi in self.data.iterrows():
            # load image
            self.original = QImage(roi['filepath'])
            # image not found, use placeholder
            if self.original.isNull():
                self.image = QImage(THUMBNAIL_NOTFOUND)
            else:
                # crop for rois
                if self.crop:
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
                temp_file_path = temp_file.name 
            # save the image
            scaled_image.save(temp_file_path, format="JPG")
            # emit thumbnail_path and progress update
            self.loaded_image.emit(i, temp_file_path)
            self.progress_update.emit(int((i + 1) / len(self.data) * 100))