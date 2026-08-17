"""
Custom Widgets for Displaying Media (Image/Video)
"""

import cv2
import pandas as pd
from pathlib import Path
from PIL import Image, ImageEnhance

from PyQt6.QtWidgets import (QDialog, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                             QStackedLayout, QPushButton, QSlider)
from PyQt6.QtGui import QPixmap, QPainter, QImage, QPen
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPointF, QRectF, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData
from PyQt6.QtMultimediaWidgets import QVideoWidget

from matchypatchy.database.media import VIDEO_EXT, IMAGE_EXT


class MediaWidget(QWidget):
    """
    Container Widget for Displaying Image or Video
    """
    new_bbox = pyqtSignal(dict)

    def __init__(self, adjust_mode='zoom'):
        super().__init__()
        self.adjust_mode = adjust_mode
        self.drawing = False
        self.filepath = None
        layout = QVBoxLayout(self)

        # Stacked layout to switch between image and video
        self.stacked = QStackedLayout()
        layout.addLayout(self.stacked)

        # Image widget
        self.image_widget = ImageWidget(adjust_mode=self.adjust_mode)
        self.image_widget.box_drawn.connect(self.capture_bbox)
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
        """
        Load media file (image or video) into the appropriate widget

        Args:
            filepath (str): Path to the media file
            bbox (DataFrame, optional): Bounding box data for cropping/display
            frame (int, optional): Frame number to load from video
            crop (bool, optional): Whether to crop to bbox
        """
        self.filepath = filepath

        # IMAGE
        if Path(self.filepath).suffix.lower() in IMAGE_EXT:
            self.playbackbar.setVisible(False)
            self.image_widget.load(self.filepath, bbox=bbox, frame=frame, crop=crop)
            self.stacked.setCurrentWidget(self.image_widget)

        # VIDEO
        elif Path(self.filepath).suffix.lower() in VIDEO_EXT:
            if frame is not None:
                print(f"Loading video frame {frame} for {self.filepath}")
                # display frame instead of video
                self.playbackbar.setVisible(False)
                self.image_widget.load(self.filepath, bbox=bbox, frame=frame, crop=crop)
                self.stacked.setCurrentWidget(self.image_widget)
            else:
                self.playbackbar.setVisible(True)
                self.player.setSource(QUrl.fromLocalFile(self.filepath))
                self.stacked.setCurrentWidget(self.video_widget)
                self.player.play()
        else:
            raise ValueError("Unsupported file format")

    def reset(self):
        """Reset the media widget to its initial state"""
        self.player.stop()
        if self.stacked.currentWidget() == self.video_widget:
            # no reset yet for video widget
            pass
        elif self.stacked.currentWidget() == self.image_widget:
            self.image_widget.reset()

    def enable_drawing_mode(self, enable=True):
        """Enable or disable drawing mode"""
        self.drawing = enable
        self.adjust_mode = 'bbox' if enable else 'zoom'
        if self.stacked.currentWidget() == self.video_widget:
            frame = self.playbackbar.get_frame()
            # default_bbox = pd.DataFrame(index=[0], data={'bbox_x':0, 'bbox_y':0, 'bbox_w':0, 'bbox_h':0})
            self.load(self.filepath, bbox=None, frame=frame)
            self.stacked.setCurrentWidget(self.image_widget)

        self.image_widget.enable_drawing_mode(enable)

    def capture_bbox(self, bbox):
        """Capture the bounding box from the image widget"""
        if self.stacked.currentWidget() == self.image_widget:
            self.new_bbox.emit(bbox)


# ==============================================================================
# IMAGE
# ==============================================================================

class ImageWidget(QLabel):
    """
    Custom Widget for Displaying an Image
    """
    box_drawn = pyqtSignal(dict)

    def __init__(self, image_path=None, width=600, height=400, adjust_mode='zoom'):
        super().__init__()
        self.default_width = width
        self.default_height = height
        self.image_path = image_path
        self.adjust_mode = adjust_mode
        self.drawing = False

        self.frame = None
        self.rel_bbox = None
        self.loaded_bbox = None  # The original bounding box loaded from the media file
        self.bbox = None
        self.drawn_bbox = None  # The bounding box drawn by the user
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

        # Mouse events for drawing bounding boxes
        self.start_pos = None
        self.end_pos = None

    def load(self, image_path, bbox=None, frame=None, crop=False):
        """
        Load image path with pillow

        Args:
            image_path (str): Path to the image file
            bbox (DataFrame, optional): Bounding box data for cropping/display
            frame (int, optional): Frame number to load from video
            crop (bool, optional): Whether to crop to bbox
        """
        # load new image if path is different
        if image_path is not None:
            self.image_path = image_path

        # no image path to load
        if self.image_path is None:
            return

        self.frame = frame

        if self.frame is not None:
            self.pil_image = self.load_from_video(self.frame)
        else:
            self.pil_image = Image.open(self.image_path)

        self.drawn_bbox = None
        self.rel_bbox = bbox
        self.loaded_bbox = bbox
        self.crop_to_bbox = crop
        self.adjust()

    def load_from_array(self, img_array):
        """
        Load image from numpy array
        Used for pairx

        Args:
            img_array (np.array): Image data as numpy array
        """

        self.image_path = None
        self.pil_image = Image.fromarray(img_array)
        self.adjust()

    def load_from_video(self, selected_frame):
        """
        Load a specific frame from a video file

        Args:
            frame (int): Frame number to load
        """
        cap = cv2.VideoCapture(self.image_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(selected_frame))
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

        Connected to sliders in imageadjustmentbar widget
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
        elif self.drawn_bbox is not None:
            return self.drawn_bbox
        else:
            return None

    def convert_bbox_for_signal(self):
        """
        Convert the drawn bounding box to relative coordinates.
        """
        if self.drawn_bbox is None:
            return None

        # Calculate the image position in widget space (from your paintEvent)
        pixmap = QPixmap.fromImage(self.scaled_image)
        target_rect = pixmap.rect()
        target_rect.moveCenter(self.rect().center() + self.image_offset.toPoint())

        # Convert widget coords to scaled image coords
        image_x = self.drawn_bbox.x() - target_rect.left()
        image_y = self.drawn_bbox.y() - target_rect.top()
        image_w = self.drawn_bbox.width()
        image_h = self.drawn_bbox.height()

        # Clamp to image bounds
        image_x = max(0, min(image_x, self.scaled_image.width()))
        image_y = max(0, min(image_y, self.scaled_image.height()))
        image_w = min(image_w, self.scaled_image.width() - image_x)
        image_h = min(image_h, self.scaled_image.height() - image_y)

        # Convert to relative coords (0-1)
        x = image_x / self.scaled_image.width()
        y = image_y / self.scaled_image.height()
        w = image_w / self.scaled_image.width()
        h = image_h / self.scaled_image.height()

        frame = self.frame if self.frame is not None else 0

        return {"bbox_x": x, "bbox_y": y, "bbox_w": w, "bbox_h": h, "frame": frame}

    # IMAGE ADJUSTMENTS ========================================================
    def reset(self):
        """Reset image adjustments and reload"""
        self.scale_factor = 1.0
        self.zoom_factor = 1.0
        self.image_offset = QPointF(0, 0)
        self.rel_bbox = self.loaded_bbox  # reset to original bbox
        # reload image
        self.load(image_path=self.image_path, bbox=self.rel_bbox, frame=self.frame, crop=self.crop_to_bbox)

    def enable_drawing_mode(self, enable):
        self.drawing = enable
        self.adjust_mode = 'bbox' if enable else 'zoom'

    # EVENTS ===================================================================
    def paintEvent(self, event):
        """
        Paint the image with current zoom and offset.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if self.qimage:
            self.scaled_image = self.qimage.scaled(self.size() * self.zoom_factor,
                                                   Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)
            # set black background
            painter.fillRect(self.rect(), Qt.GlobalColor.black)
            # draw image
            pixmap = QPixmap.fromImage(self.scaled_image)
            target_rect = pixmap.rect()
            target_rect.moveCenter(self.rect().center() + self.image_offset.toPoint())
            painter.drawPixmap(target_rect.topLeft(), pixmap)
            # set pen for drawing bounding boxes
            painter.setPen(QPen(Qt.GlobalColor.green, 3))

            # bbox drawing mode
            if self.adjust_mode == 'bbox':
                if self.drawing and self.start_pos and self.end_pos:
                    preview_rect = QRect(self.start_pos, self.end_pos).normalized()
                    # draw preview
                    painter.drawRect(preview_rect)
                else:
                    bbox = self.drawn_bbox
                    if bbox is not None:
                        painter.drawRect(bbox)

            # not cropped but draw bbox
            elif self.adjust_mode == 'zoom':
                if self.bbox is not None and not self.crop_to_bbox:
                    scaled_bbox = QRectF(self.bbox)
                    scale_factor_x = target_rect.width() / self.qimage.width()
                    scale_factor_y = target_rect.height() / self.qimage.height()
                    scaled_bbox.setRect(
                        target_rect.left() + scaled_bbox.left() * scale_factor_x,
                        target_rect.top() + scaled_bbox.top() * scale_factor_y,
                        scaled_bbox.width() * scale_factor_x,
                        scaled_bbox.height() * scale_factor_y)
                    painter.drawRect(scaled_bbox)
            else:
                pass

            painter.end()

    def wheelEvent(self, event):
        """
        Zoom in or out based on the scroll wheel movement.
        """
        if self.adjust_mode == 'zoom':
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
        # no wheel event for bbox mode
        else:
            event.ignore()  # Don't process the event
            return

    def mousePressEvent(self, event):
        """
        Start dragging the image.
        """
        if self.adjust_mode == 'zoom':
            if event.button() == Qt.MouseButton.LeftButton:
                self.drag_start_position = event.position()
        # Handle bounding box drawing mode
        elif self.adjust_mode == 'bbox':
            if self.drawing and event.button() == Qt.MouseButton.LeftButton:
                self.start_pos = event.pos()
                self.end_pos = event.pos()
        else:
            event.ignore()  # Don't process the event
            return

    def mouseMoveEvent(self, event):
        """
        Handle dragging to move the image.
        """
        # Handle zoom mode
        if self.adjust_mode == 'zoom':
            if hasattr(self, "drag_start_position"):
                drag_delta = event.position() - self.drag_start_position
                self.image_offset += drag_delta
                self.drag_start_position = event.position()
                self.update()
        # Handle bounding box drawing mode
        elif self.adjust_mode == 'bbox':
            if self.drawing:
                self.end_pos = event.pos()
                self.update()
        else:
            event.ignore()  # Don't process the event
            return

    def mouseReleaseEvent(self, event):
        """
        End dragging the image.
        """
        if self.adjust_mode == 'zoom':
            if event.button() == Qt.MouseButton.LeftButton:
                del self.drag_start_position
        # Handle bounding box drawing mode
        elif self.adjust_mode == 'bbox':
            if event.button() == Qt.MouseButton.LeftButton and self.drawing:
                # get the final position of the mouse
                self.end_pos = event.pos()
                # create rectangle
                rect = QRect(self.start_pos, self.end_pos).normalized()
                # Only save if box has area
                if rect.width() > 5 and rect.height() > 5:
                    self.rel_bbox = None
                    self.drawn_bbox = rect
                    converted_bbox = self.convert_bbox_for_signal()
                    self.box_drawn.emit(converted_bbox)
                # update the widget to show the drawn box
                self.update()
        else:
            event.ignore()  # Don't process the event
            return

    def mouseDoubleClickEvent(self, event):
        """
        Handle double-click events.
        """
        if self.adjust_mode == 'zoom':
            if event.button() == Qt.MouseButton.LeftButton:
                self.reset()
            super().mouseDoubleClickEvent(event)
        else:
            event.ignore()  # Don't process the event
            return


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
    """Video Playback Control Bar"""
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
        """Update seek slider position"""
        if not self.seeking:
            self.seek_slider.setValue(position)

    def update_duration(self, duration):
        """Update seek slider duration"""
        self.seek_slider.setRange(0, duration)

    def seek_position(self, position):
        """Seek to a new position in the video"""
        self.player.setPosition(position)

    def pause_for_seek(self):
        """Pause playback when seeking"""
        self.seeking = True
        self.was_playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self.player.pause()

    def resume_after_seek(self):
        """Resume playback after seeking"""
        self.seeking = False
        if self.was_playing:
            self.player.play()

    def set_volume(self, value):
        """Set audio volume"""
        self.audio_output.setVolume(value / 100)

    def get_frame(self):
        """Get current frame number based on position"""
        fps = round(self.player.metaData().value(QMediaMetaData.Key.VideoFrameRate))
        if fps <= 0:
            fps = 30
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
