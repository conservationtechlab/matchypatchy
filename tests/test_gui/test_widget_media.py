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
        from matchypatchy.gui.widgets.widget_media import VideoPlayerBar
        bar = MagicMock()
        bar.player.metaData.return_value.value.return_value = fps
        bar.player.position.return_value = position
        bar.get_fps = lambda: VideoPlayerBar.get_fps(bar)
        return bar

    def test_frame_from_frame_rate(self):
        from matchypatchy.gui.widgets.widget_media import VideoPlayerBar
        assert VideoPlayerBar.get_frame(self._bar(25.0)) == 50

    def test_missing_frame_rate_falls_back_to_30(self):
        """No frame rate metadata (or not loaded yet): value() is None"""
        from matchypatchy.gui.widgets.widget_media import VideoPlayerBar
        assert VideoPlayerBar.get_frame(self._bar(None)) == 60


class TestVideoPlayerBarStepFrame:
    def _bar(self, position, duration=2000, fps=25.0):
        from matchypatchy.gui.widgets.widget_media import VideoPlayerBar
        bar = MagicMock()
        bar.player.metaData.return_value.value.return_value = fps
        bar.player.position.return_value = position
        bar.player.duration.return_value = duration
        bar.get_fps = lambda: VideoPlayerBar.get_fps(bar)
        bar.get_frame = lambda: VideoPlayerBar.get_frame(bar)
        return bar

    def _step(self, bar, step):
        from matchypatchy.gui.widgets.widget_media import VideoPlayerBar
        VideoPlayerBar.step_frame(bar, step)
        bar.player.pause.assert_called_once()
        calls = bar.player.setPosition.call_args_list
        return calls[0][0][0] if calls else None

    def test_forward_seeks_to_middle_of_next_frame(self):
        # frame 10 at 25 fps, frame 11 spans 440-480 ms
        position = self._step(self._bar(400), 1)
        assert position == 460
        assert int(position / 1000 * 25) == 11

    def test_back_seeks_to_previous_frame(self):
        position = self._step(self._bar(400), -1)
        assert int(position / 1000 * 25) == 9

    def test_back_stops_at_first_frame(self):
        position = self._step(self._bar(0), -1)
        assert int(position / 1000 * 25) == 0

    def test_forward_stops_at_last_frame(self):
        # frame 49 is the last of a 2000 ms video at 25 fps
        assert self._step(self._bar(1980), 1) is None


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
