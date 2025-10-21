import cv2
from pathlib import Path
from PIL import Image, ImageEnhance

from PyQt6.QtWidgets import (QDialog, QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QStackedLayout, QPushButton, QSlider)
from PyQt6.QtGui import QPixmap, QPainter, QImage, QPen
from PyQt6.QtCore import Qt, QRect, QPointF, QRectF, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from matchypatchy.database.media import VIDEO_EXT, IMAGE_EXT

class MediaWidget(QWidget):
    """
    Container Widget for Displaying Image or Video
    """
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # Stacked layout to switch between image and video
        self.stacked = QStackedLayout()
        layout.addLayout(self.stacked)

        # Image widget
        self.image_widget = ImageWidget()
        self.stacked.addWidget(self.image_widget)

        # Video widget
        self.video_widget = VideoWidget()
        self.stacked.addWidget(self.video_widget)

        # Media player
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        # Playback controls
        self.playbackbar = VideoPlayerBar(self.player, self.audio_output)
        self.playbackbar.setVisible(False)
        layout.addWidget(self.playbackbar)

        self.setLayout(layout)

    def load(self, filepath, bbox=None, frame=None, crop=False):
        # IMAGE
        if Path(filepath).suffix.lower() in IMAGE_EXT:
            self.playbackbar.setVisible(False)
            self.image_widget.load(filepath, bbox=bbox, frame=frame, crop=crop)
            self.stacked.setCurrentWidget(self.image_widget)
        # VIDEO
        elif Path(filepath).suffix.lower() in VIDEO_EXT:
            if bbox is not None:
                # display frame instead of video
                self.playbackbar.setVisible(False)
                self.image_widget.load(filepath, bbox=bbox, frame=frame, crop=crop)
                self.stacked.setCurrentWidget(self.image_widget)
            else:
                self.playbackbar.setVisible(True)
                self.player.setSource(QUrl.fromLocalFile(filepath))
                self.stacked.setCurrentWidget(self.video_widget)
                self.player.play()
        else:
            raise ValueError("Unsupported file format")
        
    def reset(self):
        self.player.stop()
        if self.stacked.currentWidget() == self.video_widget:
            pass
        elif self.stacked.currentWidget() == self.image_widget:
            self.image_widget.reset()


# ==============================================================================
# IMAGE
# ==============================================================================
class ImageWidget(QLabel):
    """
    Custom Widget for Displaying an Image
    """
    def __init__(self, image_path=None, width=600, height=400):
        super().__init__()
        self.default_width = width
        self.default_height = height
        self.image_path = image_path
        self.rel_bbox = None
        self.bbox = None
        self.crop_to_bbox = False
        self.pil_image = None
        self.qimage = None
        # Image Adjustments
        self.zoom_factor = 1.0
        self.image_offset = QPointF(0, 0)  # Image translation offset

        # Create a QLabel to hold the image
        self.setMinimumSize(self.default_width, self.default_height)
        self.setScaledContents(True)

        self.pixmap = QPixmap(self.size())
        self.setPixmap(self.pixmap)

    def load(self, image_path, bbox=None, frame=None, crop=False):
        """
        Load image path with pillow
        """
        if self.image_path is None or image_path != self.image_path:
            self.image_path = image_path

        if frame is not None:
            self.pil_image = self.load_from_video(frame)
        else:
            self.pil_image = Image.open(self.image_path)

        self.rel_bbox = bbox
        self.crop_to_bbox = crop
        self.adjust()

    def load_from_array(self, img_array):
        self.image_path = None
        self.pil_image = Image.fromarray(img_array)
        self.adjust()

    def load_from_video(self, frame):
        cap = cv2.VideoCapture(self.image_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ret, frame = cap.read()
        cap.release()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return Image.fromarray(frame)
        else:
            raise ValueError("Could not read frame from video.")

    def adjust(self, brightness=1.0, contrast=1.0, sharpness=1.0):
        """
        Adjust image values, convert to qimage, crop, display
        """
        enhancer = ImageEnhance.Brightness(self.pil_image)
        self.pil_image = enhancer.enhance(brightness)
        enhancer = ImageEnhance.Contrast(self.pil_image)
        self.pil_image = enhancer.enhance(contrast)
        enhancer = ImageEnhance.Sharpness(self.pil_image)
        self.pil_image = enhancer.enhance(sharpness)

        # Convert to QImage
        self.qimage = self.to_qimage()
        # Get BBOX
        self.bbox = self.get_bbox()
        # crop image
        if self.bbox is not None and self.crop_to_bbox:
            self.qimage = self.qimage.copy(self.bbox)

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

    def get_bbox(self):
        """
        Crop to bbox before painting
        """
        if self.rel_bbox is not None:
            left = self.qimage.width() * self.rel_bbox.iloc[0]['bbox_x']
            top = self.qimage.height() * self.rel_bbox.iloc[0]['bbox_y']
            right = self.qimage.width() * self.rel_bbox.iloc[0]['bbox_w']
            bottom = self.qimage.height() * self.rel_bbox.iloc[0]['bbox_h']
            return QRect(int(left), int(top), int(right), int(bottom))
        else:
            return None

    # IMAGE ADJUSTMENTS ========================================================
    def reset(self):
        self.scale_factor = 1.0
        self.zoom_factor = 1.0
        self.image_offset = QPointF(0, 0)
        # reload image
        self.load(image_path=self.image_path, bbox=self.rel_bbox, crop=self.crop_to_bbox)

    # EVENTS ===================================================================
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
            # not cropped but draw bbox
            if self.bbox is not None and not self.crop_to_bbox:
                scaled_bbox = QRectF(self.bbox)
                scale_factor_x = target_rect.width() / self.qimage.width()
                scale_factor_y = target_rect.height() / self.qimage.height()
                scaled_bbox.setRect(
                    target_rect.left() + scaled_bbox.left() * scale_factor_x,
                    target_rect.top() + scaled_bbox.top() * scale_factor_y,
                    scaled_bbox.width() * scale_factor_x,
                    scaled_bbox.height() * scale_factor_y)

                painter.setPen(QPen(Qt.GlobalColor.green, 3))
                painter.drawRect(scaled_bbox)

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


# ==============================================================================
# VIDEO
# ==============================================================================
class VideoWidget(QVideoWidget):
    """
    Custom Widget for Displaying a Video
    """
    def __init__(self, file_path=None, width=600, height=400):
        super().__init__()
        self.default_width = width
        self.default_height = height
        self.file_path = file_path


class VideoPlayerBar(QWidget):
    def __init__(self, player, audio_output):
        super().__init__()
        self.player = player
        self.audio_output = audio_output

        self.playback_layout = QHBoxLayout()

        self.button_play = QPushButton("⏵︎")
        self.button_pause = QPushButton("⏸︎")
        self.button_play.clicked.connect(self.player.play)
        self.button_pause.clicked.connect(self.player.pause)
        self.button_play.setFixedWidth(60)
        self.button_pause.setFixedWidth(60)

        # Seek slider
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderMoved.connect(self.seek_position)
        self.seek_slider.sliderPressed.connect(self.pause_for_seek)
        self.seek_slider.sliderReleased.connect(self.resume_after_seek)
        self.seeking = False

        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)


        # Volume slider
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)

        self.volume_slider.valueChanged.connect(self.set_volume)

        playback_layout = QHBoxLayout()
        playback_layout.addWidget(self.button_play, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        playback_layout.addWidget(self.button_pause, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        playback_layout.addSpacing(10)
        playback_layout.addWidget(QLabel("Seek:"))
        playback_layout.addWidget(self.seek_slider)
        playback_layout.addSpacing(10)
        playback_layout.addWidget(QLabel("Volume:"))
        playback_layout.addWidget(self.volume_slider)

        playback_layout.addStretch()
        self.setLayout(playback_layout)


    def update_position(self, position):
        if not self.seeking:
            self.seek_slider.setValue(position)

    def update_duration(self, duration):
        self.seek_slider.setRange(0, duration)

    def seek_position(self, position):
        self.player.setPosition(position)

    def pause_for_seek(self):
        self.seeking = True
        self.was_playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self.player.pause()

    def resume_after_seek(self):
        self.seeking = False
        if self.was_playing:
            self.player.play()

    def set_volume(self, value):
        self.audio_output.setVolume(value / 100)

    def get_frame(self):
        cap = cv2.VideoCapture('/path/to/video.mp4')
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        return int(self.player.position() / 1000 * fps)
    

class VideoViewer(QDialog):
    """
    Popup window to view video
    """
    def __init__(self, parent, filepath):
        super().__init__(parent)
        self.setWindowTitle("Video Viewer")
        self.setGeometry(100, 100, 800, 600)

        self.layout = QVBoxLayout(self)

        self.mediawidget = MediaWidget()
        self.layout.addWidget(self.mediawidget)

        self.mediawidget.load(filepath)

        self.setLayout(self.layout)
        self.show()