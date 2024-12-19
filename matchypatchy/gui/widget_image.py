"""
Custom Widget for Displaying an Image
"""
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap, QPainter, QImage
from PyQt6.QtCore import Qt, QRect, QPointF


class ImageWidget(QLabel):
    def __init__(self, image_path=None, width=600, height=400):
        super().__init__()
        self.default_width = width
        self.default_height = height
        self.image_path = image_path
        self.bbox = None
        self.scale_factor = 1.0
        self.translation = QPointF(0, 0)  # Image translation offset
        self.last_cursor_position = QPointF(0, 0)  # Last cursor position on zoom
        self.brightness_factor = 0
        self.contrast_factor = 0

        # Create a QLabel to hold the image
        self.setMinimumSize(self.default_width, self.default_height)
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
            self.bbox = bbox
            left = self.original.width() * self.bbox['bbox_x']
            top = self.original.height() * self.bbox['bbox_y']
            right = self.original.width() * self.bbox['bbox_w']
            bottom = self.original.height() * self.bbox['bbox_h']
            crop_rect = QRect(int(left), int(top), int(right), int(bottom))
            self.image = self.original.copy(crop_rect)
        else:
            self.bbox=None
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
        self.translation = QPointF(0, 0)
        super().resizeEvent(event)  


    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.pixmap.isNull():
            # Calculate the scaled size
            scaled_pixmap = self.pixmap.scaled(
                self.pixmap.size() * self.scale_factor,
                Qt.AspectRatioMode.KeepAspectRatio
            )

            # Draw the translated and scaled pixmap
            x = (self.width() - scaled_pixmap.width()) / 2 + self.translation.x()
            y = (self.height() - scaled_pixmap.height()) / 2 + self.translation.y()
            painter.drawPixmap(x, y, scaled_pixmap)

    def wheelEvent(self, event):
        if self.pixmap.isNull():
            return

        # Determine cursor position in the widget
        cursor_position = event.position()

        # Calculate cursor position relative to the image
        widget_center = QPointF(self.width() / 2, self.height() / 2)
        cursor_relative_to_image = (cursor_position - widget_center - self.translation) / self.scale_factor

        # Adjust scale factor
        old_scale = self.scale_factor
        if event.angleDelta().y() > 0:
            self.scale_factor *= 1.1  # Zoom in
        else:
            self.scale_factor /= 1.1  # Zoom out

        self.scale_factor = max(0.1, min(self.scale_factor, 10.0))  # Limit zoom range

        # Adjust translation to zoom toward cursor
        new_cursor_position_on_image = cursor_relative_to_image * self.scale_factor
        adjustment = new_cursor_position_on_image - cursor_relative_to_image
        print(adjustment)
        self.translation -= adjustment

        self.update()  # Trigger a repaint

    # TODO:
    def zoom(self):
        pass

    def adjust_brightness(self, value):
        print(value)
        pass

    def adjust_contrast(self, value):
        print(value)
        pass

    def reset(self):
        self.scale_factor = 1.0
        self.translation = QPointF(0, 0)  # Image translation offset
        self.last_cursor_position = QPointF(0, 0)  # Last cursor position on zoom
        self.display_image(self.image_path, bbox=self.bbox)