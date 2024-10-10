from PIL import Image
from PIL.ImageQt import ImageQt

from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap, QPainter, QImage
from PyQt6.QtCore import Qt


class ImageWidget(QLabel):
    def __init__(self, image_path=None, width=600, height=400):
        super().__init__()
        self.default_width = width
        self.default_height = height
        self.image_path = image_path
        
        # Create a QLabel to hold the image
        self.image_label = QLabel(self)
        self.image_label.setMinimumSize(self.default_width, self.default_height)
        self.image_label.setScaledContents(True)
        
        self.pixmap = QPixmap(self.default_width,self.default_height)
        self.pixmap.fill(Qt.GlobalColor.black)
        self.image_label.setPixmap(self.pixmap)

        # Allow the QLabel to scale its content (the pixmap) with the widget's size
        
        
    def display_image(self, image_path, bbox=None):
        if image_path != self.image_path:
            self.image_path = image_path
        self.image_label.clear()

        # crop first
        if bbox is not None:
            image = QImage(image_path)
            img_width = image.width()
            img_height = image.height()
            
            left = img_width * bbox['bbox_x']
            top = img_height * bbox['bbox_y']
            right = img_width * (bbox['bbox_x'] + bbox['bbox_w'])
            bottom = img_height * (bbox['bbox_y'] + bbox['bbox_h'])
            crop_rect = (int(left), int(top), int(right), int(bottom))

            print(crop_rect)
            cropped_image = image.copy(*crop_rect)

            self.pixmap = QPixmap.fromImage(cropped_image)
            self.image_label.setPixmap(self.pixmap)
        
        # default load
        else:
            self.pixmap = QPixmap(self.image_path)  # Update the path to your image file
            self.image_label.setPixmap(self.pixmap)

        
    def display_image_padded(self, image_path, bbox=None):
        if image_path != self.image_path:
            self.image_path = image_path
        self.image_label.clear()
        self.pixmap = QPixmap(self.width(), self.height())
        self.pixmap.fill(Qt.GlobalColor.black)
        self.image_label.setPixmap(self.pixmap)
        # crop
        if bbox is not None:
            image = QImage(image_path)
            img_width = image.width()
            img_height = image.height()
            
            left = img_width * bbox['bbox_x']
            top = img_height * bbox['bbox_y']
            right = img_width * (bbox['bbox_x'] + bbox['bbox_w'])
            bottom = img_height * (bbox['bbox_y'] + bbox['bbox_h'])
            crop_rect = (int(left), int(top), int(right), int(bottom))

            print(crop_rect)
            cropped_image = image.copy(*crop_rect)

            self.pixmap = QPixmap.fromImage(cropped_image)
        
        # default load
        else:
            self.pixmap = QPixmap(self.image_path)

        
        self.image_label.setPixmap(self.pixmap)


    def resizeEvent(self, event):
        # Get the current size of the widget
        # Scale the pixmap to the size of the widget, keeping the aspect ratio
        self.image_label.clear()
        self.setPixmap(self.pixmap.scaled(self.width(), self.height(),
                                          Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation))

        # Call the parent class's resizeEvent
        super().resizeEvent(event)
