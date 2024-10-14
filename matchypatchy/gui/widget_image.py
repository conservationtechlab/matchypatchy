from PIL import Image
from PIL.ImageQt import ImageQt

from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap, QPainter, QImage
from PyQt6.QtCore import Qt, QRect


class ImageWidget(QLabel):
    def __init__(self, image_path=None, width=600, height=400):
        super().__init__()
        self.default_width = width
        self.default_height = height
        self.image_path = image_path
        
        # Create a QLabel to hold the image
        self.setMinimumSize(self.default_width,self.default_height)
        self.setScaledContents(True)
        
        self.pixmap = QPixmap(self.size())
        self.pixmap.fill(Qt.GlobalColor.black)
        self.setPixmap(self.pixmap)
        
        
    def display_image(self, image_path, bbox=None):
        if image_path != self.image_path:
            self.image_path = image_path
        self.clear()
        self.pixmap = QPixmap(self.width(), self.height())
        self.pixmap.fill(Qt.GlobalColor.black)

        self.original = QImage(image_path)

        if bbox is not None:
            left = self.original.width() * bbox['bbox_x']
            top = self.original.height() * bbox['bbox_y']
            right = self.original.width() * bbox['bbox_w']
            bottom = self.original.height() * bbox['bbox_h']
            crop_rect = QRect(int(left), int(top), int(right), int(bottom))
            self.image = self.original.copy(crop_rect)
        
        else:
            self.image = self.original.copy()

        scaled_image = self.image.scaled(self.size(), 
                                         Qt.AspectRatioMode.KeepAspectRatio, 
                                         Qt.TransformationMode.SmoothTransformation)
        
        painter = QPainter(self.pixmap)
        x_offset = (self.width() - scaled_image.width()) // 2
        y_offset = (self.height() - scaled_image.height()) // 2
        painter.drawImage(x_offset, y_offset, scaled_image)
        painter.end()

        self.setPixmap(self.pixmap)


    
    def resizeEvent(self, event):
        super().resizeEvent(event)