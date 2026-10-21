"""
Unit tests for matchypatchy.gui.widgets.widget_media

Methods are called on a MagicMock standing in for the widget, so no Qt
display is needed. PyQt6 is stubbed out in conftest.py.
"""
from unittest.mock import MagicMock


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
