"""
Unit tests for MainWindow view switching

MainWindow methods are called on a MagicMock standing in for the window,
so no Qt display is needed. PyQt6 is stubbed out in conftest.py.
"""
from unittest.mock import MagicMock, patch

MG = "matchypatchy.gui.main_gui"


class TestSetManualView:
    def test_filters_reset_before_manual_compare(self):
        """Manual compare must not run with the previous session's filters"""
        from matchypatchy.gui.main_gui import MainWindow
        mw = MagicMock()
        mw._load_manual_view = lambda ids: MainWindow._load_manual_view(mw, ids)
        calls = []
        mw.Compare.refresh_filters.side_effect = lambda: calls.append("refresh_filters")
        mw.Compare.compare_manual.side_effect = lambda **kw: calls.append("compare_manual")
        scheduled = []
        with patch(f"{MG}.QTimer") as timer:
            timer.singleShot.side_effect = lambda ms, fn: scheduled.append(fn)
            MainWindow._set_manual_view(mw, selected_ids=[1, 2])
        # timers fire after the method returns, in the order they were scheduled
        for fn in scheduled:
            fn()
        assert calls == ["refresh_filters", "compare_manual"]
        mw.Compare.compare_manual.assert_called_once_with(selected_ids=[1, 2])


class TestFontSize:
    def test_system_size_when_never_set_or_unreadable(self):
        from matchypatchy.gui.main_gui import MainWindow
        window = MagicMock(system_font_size=9)
        window.settings.value.side_effect = lambda _key, default: default
        assert MainWindow.font_size(window) == 9
        window.settings.value.side_effect = None
        window.settings.value.return_value = "big"
        assert MainWindow.font_size(window) == 9

    def test_saved_size_is_read_back(self):
        """QSettings can hand the size back as a string"""
        from matchypatchy.gui.main_gui import MainWindow
        window = MagicMock(system_font_size=9)
        window.settings.value.return_value = "15"
        assert MainWindow.font_size(window) == 15

    def test_save_applies_and_keeps_size(self):
        from matchypatchy.gui.main_gui import MainWindow
        window = MagicMock(system_font_size=9)
        MainWindow.save_font_size(window, 15)
        window.settings.setValue.assert_called_once_with("font_size", 15)
        window.apply_font_size.assert_called_once_with(15)

    def test_saving_system_size_follows_the_system(self):
        from matchypatchy.gui.main_gui import MainWindow
        window = MagicMock(system_font_size=9)
        MainWindow.save_font_size(window, 9)
        window.settings.remove.assert_called_once_with("font_size")
        window.settings.setValue.assert_not_called()
        window.apply_font_size.assert_called_once_with(9)

    def test_apply_sets_app_font_size(self):
        from matchypatchy.gui.main_gui import MainWindow
        with patch(f"{MG}.QApplication") as app_class:
            font = app_class.instance.return_value.font.return_value
            MainWindow.apply_font_size(MagicMock(), 15)
        font.setPointSize.assert_called_once_with(15)
        app_class.instance.return_value.setFont.assert_called_once_with(font)
