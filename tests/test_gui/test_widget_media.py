"""
Unit tests for matchypatchy.gui.widgets.widget_media

Methods are called on a MagicMock standing in for the widget, so no Qt
display is needed. PyQt6 is stubbed out in conftest.py.
"""
from types import MethodType
from unittest.mock import MagicMock, patch

from PIL import Image


class TestVideoPlayerBarGetFrame:
    def _bar(self, fps, position=2000):
        bar = MagicMock()
        bar.player.metaData.return_value.value.return_value = fps
        bar.player.position.return_value = position
        return bar

    def test_frame_from_frame_rate(self):
        from matchypatchy.gui.widgets.widget_media import VideoPlayerBar
        assert VideoPlayerBar.get_frame(self._bar(25.0)) == 50

    def test_missing_frame_rate_falls_back_to_30(self):
        """No frame rate metadata (or not loaded yet): value() is None"""
        from matchypatchy.gui.widgets.widget_media import VideoPlayerBar
        assert VideoPlayerBar.get_frame(self._bar(None)) == 60


def _image_widget_class():
    """
    ImageWidget with its real methods

    With PyQt6 stubbed, QLabel is a MagicMock and so is any class built on it.
    Load a private copy of the module with QLabel as a plain class instead.
    """
    import importlib.util
    import sys
    from matchypatchy.gui.widgets import widget_media
    spec = importlib.util.spec_from_file_location("_widget_media_real_label", widget_media.__file__)
    module = importlib.util.module_from_spec(spec)
    with patch.object(sys.modules["PyQt6.QtWidgets"], "QLabel", type("QLabel", (), {})):
        spec.loader.exec_module(module)
    return module.ImageWidget


def _image_widget(path="a.jpg"):
    """MagicMock widget running ImageWidget's load/adjust/reset on a grey test image"""
    cls = _image_widget_class()
    widget = MagicMock()
    for name in ("load", "adjust", "reset"):
        setattr(widget, name, MethodType(getattr(cls, name), widget))
    widget.image_path = None
    widget.frame = None
    widget.original_image = None
    widget.rel_bbox = widget.loaded_bbox = widget.drawn_bbox = None
    widget.crop_to_bbox = False
    widget.zoom_factor = 1.0
    widget.image_offset = "centered"
    with patch("PIL.Image.open", return_value=Image.new("RGB", (4, 4), (100, 100, 100))):
        widget.load(path)
    return widget


class TestImageWidgetView:
    def test_next_image_opens_unzoomed(self):
        widget = _image_widget("a.jpg")
        widget.zoom_factor = 2.0
        widget.image_offset = "panned"
        with patch("PIL.Image.open", return_value=Image.new("RGB", (4, 4))):
            widget.load("b.jpg")
        assert widget.zoom_factor == 1.0
        assert widget.image_offset != "panned"

    def test_same_image_keeps_zoom(self):
        """Reloading the shown image (e.g. after saving a box) keeps the view"""
        widget = _image_widget("a.jpg")
        widget.zoom_factor = 2.0
        with patch("PIL.Image.open", return_value=Image.new("RGB", (4, 4))):
            widget.load("a.jpg")
        assert widget.zoom_factor == 2.0

    def test_reset_keeps_adjustments(self):
        """Double-click resets zoom and pan, the image keeps the slider values"""
        widget = _image_widget()
        widget.adjust(brightness=1.5, contrast=1.0, sharpness=1.0)
        widget.zoom_factor = 2.0
        widget.image_offset = "panned"
        with patch("PIL.Image.open", return_value=Image.new("RGB", (4, 4), (100, 100, 100))):
            widget.reset()
        assert widget.zoom_factor == 1.0
        assert widget.image_offset != "panned"
        assert widget.pil_image.getpixel((0, 0))[0] == 150
