from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QSizePolicy)
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import Qt


class ImageWidget(QLabel):
    def __init__(self, image_path=None, width=600, height=600):
        super().__init__()
        self.default_width = width
        self.default_height = height
        self.image_path = image_path
        
        # Create a QLabel to hold the image
        self.image_label = QLabel(self)
        self.image_label.setMinimumSize(self.default_width, self.default_height)

        # Load the image
        self.pixmap = QPixmap(image_path)
        # Set the initial pixmap to the label

        # Set the initial pixmap to the label
        self.setPixmap(self.pixmap.scaled(self.default_width, self.default_height, Qt.AspectRatioMode.KeepAspectRatio))

        # Set alignment to center the image
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


        
    def display_image(self, image_path):
        self.image_path = image_path
        pixmap = QPixmap(self.image_path)  # Update the path to your image file
        scaled_pixmap = pixmap.scaled(self.default_width, self.default_height, 
                                      Qt.AspectRatioMode.KeepAspectRatio, 
                                      Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        
    def display_image_padded(self, image_path):
        self.image_path = image_path
        pixmap = QPixmap(self.image_path)  # Update the path to your image file
        scaled_pixmap = pixmap.scaled(self.default_width, self.default_height, 
                                      Qt.AspectRatioMode.KeepAspectRatio, 
                                      Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        
        padded_image = QPixmap(self.default_width, self.default_height)
        padded_image.fill(Qt.GlobalColor.black) 
        
        painter = QPainter(padded_image)
        # Calculate position to center the scaled image
        x = (self.default_width - scaled_pixmap.width()) // 2
        y = (self.default_height - scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()
        
        self.image_label.setPixmap(padded_image)


    def resizeEvent(self, event):
        """Override the resize event to adjust image size dynamically."""
        # Get the current size of the widget
        widget_width = self.width()
        widget_height = self.height()
        print(widget_height,widget_width)

        # Scale the pixmap to the size of the widget, keeping the aspect ratio
        #self.image_label.resize(widget_width, widget_height)
        scaled_pixmap = self.pixmap.scaled(widget_width, widget_height, Qt.AspectRatioMode.KeepAspectRatio)

        # Set the scaled pixmap on the label
        self.setPixmap(scaled_pixmap)

        # Call the parent class's resizeEvent
        super().resizeEvent(event)