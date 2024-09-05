from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QSizePolicy)
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import Qt

import os


class ImageWidget(QWidget):
    def __init__(self, image_path=None, width=600, height=600):
        super().__init__()
        self.box_width = width
        self.box_height = height
        self.image_path = image_path
    
        self.setFixedSize(self.box_width, self.box_height)
        layout = QVBoxLayout()
        
        # Create a QLabel to hold the image
        self.image_label = QLabel(self)
        self.image_label.resize(self.box_width, self.box_height)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

        if self.image_path:
            self.display_image(self.image_path)

        # Add the QLabel to the layout
        layout.addWidget(self.image_label)

        # Set the layout for the widget
        self.setLayout(layout)
        
    def display_image(self, image_path):
        self.image_path = image_path
        pixmap = QPixmap(self.image_path)  # Update the path to your image file
        scaled_pixmap = pixmap.scaled(self.box_width, self.box_height, 
                                      Qt.AspectRatioMode.KeepAspectRatio, 
                                      Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        
    def display_image_padded(self, image_path):
        self.image_path = image_path
        pixmap = QPixmap(self.image_path)  # Update the path to your image file
        scaled_pixmap = pixmap.scaled(self.box_width, self.box_height, 
                                      Qt.AspectRatioMode.KeepAspectRatio, 
                                      Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        
        padded_image = QPixmap(self.box_width, self.box_height)
        padded_image.fill(Qt.GlobalColor.black) 
        
        painter = QPainter(padded_image)
        # Calculate position to center the scaled image
        x = (self.box_width - scaled_pixmap.width()) // 2
        y = (self.box_height - scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()
        
        self.image_label.setPixmap(padded_image)