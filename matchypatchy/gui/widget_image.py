"""
Custom Widget for Displaying an Image
"""
from PIL import Image, ImageEnhance

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
        self.pil_image = None
        self.qimage = None
        # Image Adjustments
        self.zoom_factor = 1.0
        self.image_offset = QPointF(0, 0)  # Image translation offset
        self.brightness_factor = 1.0
        self.contrast_factor = 1.0
        self.sharpness_factor = 1.0

        # Create a QLabel to hold the image
        self.setMinimumSize(self.default_width, self.default_height)
        self.setScaledContents(True)

        self.pixmap = QPixmap(self.size())
        self.setPixmap(self.pixmap)

    def load(self, image_path, bbox=None):
        """
        Load image path with pillow
        """
        if self.image_path is None or image_path != self.image_path:
            self.image_path = image_path
        
        if bbox is not None:
            self.bbox = bbox
        
        self.pil_image = Image.open(self.image_path)
        self.adjust()


    def adjust(self):
        """
        Adjust image values, convert to qimage, crop, display
        """
        # Adjust brightness
        enhancer = ImageEnhance.Brightness(self.pil_image)
        self.pil_image = enhancer.enhance(self.brightness_factor)

        enhancer = ImageEnhance.Contrast(self.pil_image)
        self.pil_image = enhancer.enhance(self.contrast_factor)

        enhancer = ImageEnhance.Sharpness(self.pil_image)
        self.pil_image = enhancer.enhance(self.sharpness_factor)

        # Convert to QImage
        self.qimage = self.to_qimage()

        # Crop
        self.qimage = self.crop(self.bbox)

        # Display
        self.update()

    def to_qimage(self):
        """
        Convert a PIL image to QImage.
        """
        # convert to raw
        self.pil_image = self.pil_image.convert('RGBA')
        image_data = self.pil_image.tobytes("raw", 'RGBA')
        width, height = self.pil_image.size
        
        # Create a QImage from the image data
        return QImage(image_data, width, height, QImage.Format.Format_RGBA8888)
    
    def crop(self, bbox=None):
        """
        Crop to bbox before painting
        """
        if bbox is not None:
            self.bbox = bbox
            left = self.qimage.width() * self.bbox['bbox_x']
            top = self.qimage.height() * self.bbox['bbox_y']
            right = self.qimage.width() * self.bbox['bbox_w']
            bottom = self.qimage.height() * self.bbox['bbox_h']
            crop_rect = QRect(int(left), int(top), int(right), int(bottom))
            qimage = self.qimage.copy(crop_rect)
        else:
            self.bbox=None
            qimage = self.qimage.copy()

        return qimage
    
    def draw_bbox(self, bbox):
        # TODO
        pass

    # ---- IMAGE ADJUSTMENTS ----

    def adjust_brightness(self, value):
        """
        QImage needs to be reconverted each time
        """
        self.brightness_factor = value / 50
        self.adjust()

    def adjust_contrast(self, value):
        """
        QImage needs to be reconverted each time
        """
        self.contrast_factor = value / 50
        self.adjust()

    def adjust_sharpness(self, value):
        """
        QImage needs to be reconverted each time
        """
        print(value/50)
        self.sharpness_factor = value / 50
        self.adjust()

    def reset(self):
        self.scale_factor = 1.0
        self.brightness_factor = 1.0
        self.contrast_factor = 1.0
        self.sharpness_factor = 1.0
        self.zoom_factor = 1.0
        self.image_offset = QPointF(0, 0)  
        # reload image
        self.load(image_path=self.image_path, bbox=self.bbox)

    # ---- EVENTS ----

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if self.qimage:
            scaled_image = self.qimage.scaled(self.size() * self.zoom_factor,
                                              Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
            # set black background
            painter.fillRect(self.rect(), Qt.GlobalColor.black)
            # draw image
            pixmap = QPixmap.fromImage(scaled_image)
            target_rect = pixmap.rect()
            target_rect.moveCenter(self.rect().center() + self.image_offset.toPoint())
            painter.drawPixmap(target_rect.topLeft(), pixmap)


    def wheelEvent(self, event):
        """
        Zoom in or out based on the scroll wheel movement.
        """
        # Calculate the zoom delta
        zoom_delta = 0.1 if event.angleDelta().y() > 0 else -0.1
        new_zoom_factor = self.zoom_factor + zoom_delta
        if new_zoom_factor < 0.5:  # Prevent zooming too far out
            return

        # Calculate the image position relative to the center
        mouse_pos = event.position()
        widget_center = QPointF(self.width() / 2, self.height() / 2)
        mouse_relative_pos = mouse_pos - widget_center

        # Adjust offset based on zoom
        scale_change = new_zoom_factor / self.zoom_factor
        self.image_offset += mouse_relative_pos * (1 - scale_change)

        # Update zoom factor
        self.zoom_factor = new_zoom_factor
        self.update()


    def mousePressEvent(self, event):
        """
        Start dragging the image.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.position()

    def mouseMoveEvent(self, event):
        """
        Handle dragging to move the image.
        """
        if hasattr(self, "drag_start_position"):
            drag_delta = event.position() - self.drag_start_position
            self.image_offset += drag_delta
            self.drag_start_position = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        """
        End dragging the image.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            del self.drag_start_position

    def mouseDoubleClickEvent(self, event):
        """
        Handle double-click events.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.reset()
        super().mouseDoubleClickEvent(event)
