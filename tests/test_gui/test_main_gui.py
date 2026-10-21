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
