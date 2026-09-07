"""
Unit tests for matchypatchy.gui.display_media.DisplayMedia

Tests focus on the pure-Python helper/logic methods that do not require a
real Qt display server.  Qt widgets are stubbed out by conftest.py.
"""
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_display_media():
    """Return a minimally-configured DisplayMedia instance (no real Qt)."""
    from matchypatchy.gui.display_media import DisplayMedia

    parent = MagicMock()
    parent.mpDB = MagicMock()
    parent.logger = MagicMock()
    parent.cfg = MagicMock()
    parent.mpDB.count.return_value = 5  # media and roi present

    dm = DisplayMedia.__new__(DisplayMedia)
    dm.parent = parent
    dm.logger = parent.logger
    dm.cfg = parent.cfg
    dm.mpDB = parent.mpDB
    dm.data_type = 1  # ROI mode
    dm.valid_stations = {1: "S1", 2: "S2"}
    dm.selected_rows = []

    # Stub child widgets
    dm.media_table = MagicMock()
    dm.media_table.edit_stack = []
    dm.media_table.data_filtered = pd.DataFrame()
    dm.filterbar = MagicMock()
    dm.show_type = MagicMock()
    dm.button_save = MagicMock()
    dm.button_undo = MagicMock()
    dm.button_edit = MagicMock()
    dm.button_duplicate = MagicMock()
    dm.button_delete = MagicMock()
    dm.button_select = MagicMock()
    dm.count_label = MagicMock()

    dm.filters = {
        "active_region": (0,), "active_survey": (0,), "active_station": (0,),
        "active_viewpoint": (0,), "active_individual": (0,),
        "unidentified_only": False, "favorites_only": False, "no_roi_mids": False,
    }

    dm.SAVE_STYLE = "QPushButton { background-color: #2a3e5e; }"

    from tests.conftest import _SignalStub
    dm.edit_stack_signal = _SignalStub()

    return dm


# ---------------------------------------------------------------------------
# TestUpdateCountLabel
# ---------------------------------------------------------------------------

class TestUpdateCountLabel:
    def test_count_label_reflects_filtered_rows(self):
        dm = _make_display_media()
        dm.media_table.data_filtered = pd.DataFrame({"id": [1, 2, 3]})
        dm.update_count_label()
        dm.count_label.setText.assert_called_once_with("Total Media: 3")

    def test_count_label_zero_when_empty(self):
        dm = _make_display_media()
        dm.media_table.data_filtered = pd.DataFrame()
        dm.update_count_label()
        dm.count_label.setText.assert_called_once_with("Total Media: 0")

    def test_count_label_selected(self):
        dm = _make_display_media()
        dm.media_table.selectedRows.return_value = [0, 2]
        dm.media_table.data_filtered = pd.DataFrame({"id": [1, 2, 3]})
        dm.update_count_label_selected()
        dm.count_label.setText.assert_called_once_with("Selected: 2 / 3")


# ---------------------------------------------------------------------------
# TestCheckUndoButton
# ---------------------------------------------------------------------------

class TestCheckUndoButton:
    def test_undo_enabled_when_edit_stack_nonempty(self):
        dm = _make_display_media()
        dm.media_table.edit_stack = [MagicMock()]
        dm.check_undo_button()
        dm.button_undo.setEnabled.assert_called_with(True)
        dm.button_save.setStyleSheet.assert_called_with(dm.SAVE_STYLE)

    def test_undo_disabled_when_edit_stack_empty(self):
        dm = _make_display_media()
        dm.media_table.edit_stack = []
        dm.check_undo_button()
        dm.button_undo.setEnabled.assert_called_with(False)
        dm.button_save.setStyleSheet.assert_called_with("")


# ---------------------------------------------------------------------------
# TestToggleFilterbarDatatype
# ---------------------------------------------------------------------------

class TestToggleFilterbarDatatype:
    def test_roi_mode_shows_roi_filters(self):
        dm = _make_display_media()
        dm.data_type = 1
        dm.toggle_filterbar_datatype()
        dm.filterbar.individual_visible.assert_called_with(True)
        dm.filterbar.unidentified_visible.assert_called_with(True)
        dm.filterbar.favorites_visible.assert_called_with(True)
        dm.filterbar.viewpoint_visible.assert_called_with(True)
        dm.filterbar.no_roi_visible.assert_called_with(False)

    def test_media_mode_hides_roi_filters(self):
        dm = _make_display_media()
        dm.data_type = 0
        dm.toggle_filterbar_datatype()
        dm.filterbar.individual_visible.assert_called_with(False)
        dm.filterbar.unidentified_visible.assert_called_with(False)
        dm.filterbar.favorites_visible.assert_called_with(False)
        dm.filterbar.viewpoint_visible.assert_called_with(False)
        dm.filterbar.no_roi_visible.assert_called_with(True)


# ---------------------------------------------------------------------------
# TestHandleTableChange
# ---------------------------------------------------------------------------

class TestHandleTableChange:
    def test_checkbox_change_triggers_check_selected_rows(self):
        dm = _make_display_media()
        dm.check_selected_rows = MagicMock()
        dm.check_undo_button = MagicMock()
        # item stub in column 0 (checkbox)
        dm.media_table.table.item.return_value = MagicMock()
        dm.handle_table_change([0, 0])
        dm.check_selected_rows.assert_called_once()

    def test_non_checkbox_change_does_not_trigger_check_selected_rows(self):
        dm = _make_display_media()
        dm.check_selected_rows = MagicMock()
        dm.check_undo_button = MagicMock()
        dm.handle_table_change([0, 5])  # column 5, not checkbox
        dm.check_selected_rows.assert_not_called()
        dm.check_undo_button.assert_called_once()


# ---------------------------------------------------------------------------
# TestHandleLoadedData
# ---------------------------------------------------------------------------

class TestHandleLoadedData:
    def test_handle_loaded_data_calls_update_count_label(self):
        dm = _make_display_media()
        dm.update_count_label = MagicMock()
        dm.handle_loaded_data()
        dm.update_count_label.assert_called_once()


# ---------------------------------------------------------------------------
# TestSaveAndUndo
# ---------------------------------------------------------------------------

class TestSaveAndUndo:
    def test_save_calls_media_table_save_changes(self):
        dm = _make_display_media()
        dm.check_undo_button = MagicMock()
        dm.save()
        dm.media_table.save_changes.assert_called_once()
        dm.check_undo_button.assert_called_once()

    def test_undo_calls_media_table_undo(self):
        dm = _make_display_media()
        dm.check_undo_button = MagicMock()
        dm.undo()
        dm.media_table.undo.assert_called_once()
        dm.check_undo_button.assert_called_once()


# ---------------------------------------------------------------------------
# TestCheckSelectedRows
# ---------------------------------------------------------------------------

class TestCheckSelectedRows:
    def test_no_selection_disables_row_action_buttons(self):
        dm = _make_display_media()
        dm.media_table.selectedRows.return_value = []
        dm.check_selected_rows()
        dm.button_edit.setEnabled.assert_called_with(False)
        dm.button_delete.setEnabled.assert_called_with(False)
        dm.button_duplicate.setEnabled.assert_called_with(False)

    def test_with_selection_enables_edit_and_delete_buttons(self):
        dm = _make_display_media()
        dm.media_table.selectedRows.return_value = [0, 1]
        dm.media_table.data_filtered = MagicMock()
        dm.check_selected_rows()
        dm.button_edit.setEnabled.assert_called_with(True)
        dm.button_delete.setEnabled.assert_called_with(True)


# ---------------------------------------------------------------------------
# TestUpdateButtons
# ---------------------------------------------------------------------------

class TestUpdateButtons:
    def test_with_selection_enables_edit_and_delete(self):
        dm = _make_display_media()
        dm.media_table.selectedRows.return_value = [0]
        dm.update_buttons()
        dm.button_edit.setEnabled.assert_called_with(True)
        dm.button_delete.setEnabled.assert_called_with(True)

    def test_without_selection_disables_buttons(self):
        dm = _make_display_media()
        dm.media_table.selectedRows.return_value = []
        dm.update_buttons()
        dm.button_edit.setEnabled.assert_called_with(False)


# ---------------------------------------------------------------------------
# TestLoadTable
# ---------------------------------------------------------------------------

class TestLoadTable:
    def test_no_media_returns_false(self):
        dm = _make_display_media()
        dm.mpDB.count.side_effect = lambda tbl: 0  # both media and roi = 0
        with patch("matchypatchy.gui.display_media.AlertPopup") as mock_popup:
            mock_popup.return_value.exec.return_value = True
            result = dm.load_table()
        assert result is False

    def test_has_media_returns_true(self):
        dm = _make_display_media()
        dm.mpDB.count.side_effect = lambda tbl: (5 if tbl == "media" else 3)
        result = dm.load_table()
        assert result is True
        dm.media_table.clear_and_load_contents.assert_called()

    def test_no_rois_defaults_to_media_mode(self):
        dm = _make_display_media()
        dm.data_type = 1
        dm.mpDB.count.side_effect = lambda tbl: (5 if tbl == "media" else 0)
        with patch("matchypatchy.gui.display_media.AlertPopup") as mock_popup:
            mock_popup.return_value.exec.return_value = True
            result = dm.load_table()
        assert result is True
        assert dm.data_type == 0
