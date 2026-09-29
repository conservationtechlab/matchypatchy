"""
Unit tests for matchypatchy.gui.display_media.DisplayMedia

Tests focus on pure-Python helper/logic methods that do not require a
real Qt display server. Qt widgets are stubbed out by conftest.py.
"""
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch


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
    parent._set_base_view = MagicMock()
    parent._set_compare_view = MagicMock()
    parent._set_manual_view = MagicMock()

    # Mock Qt components
    with patch("matchypatchy.gui.display_media.QVBoxLayout"), \
         patch("matchypatchy.gui.display_media.QHBoxLayout"), \
         patch("matchypatchy.gui.display_media.QPushButton"), \
         patch("matchypatchy.gui.display_media.QLabel"), \
         patch("matchypatchy.gui.display_media.QComboBox"), \
         patch("matchypatchy.gui.display_media.QTableView"), \
         patch("matchypatchy.gui.display_media.QHeaderView"), \
         patch("matchypatchy.gui.display_media.FilterBar"), \
         patch("matchypatchy.gui.display_media.StandardButton"), \
         patch("matchypatchy.gui.display_media.VerticalSeparator"), \
         patch("matchypatchy.gui.display_media.MediaTable"), \
         patch("matchypatchy.gui.display_media.load_model", 
               return_value={"None": "None", "0": "Left", "1": "Any", "2": "Right"}):

        dm = DisplayMedia.__new__(DisplayMedia)
        dm.parent = parent
        dm.logger = parent.logger
        dm.cfg = parent.cfg
        dm.mpDB = parent.mpDB
        dm.VIEWPOINTS = {"None": "None", "0": "Left", "1": "Any", "2": "Right"}
        dm.data_type = 1  # ROI mode
        dm.valid_stations = {1: "S1", 2: "S2"}
        dm._data_raw = pd.DataFrame()
        dm._data_filtered = pd.DataFrame()
        dm.edit_stack = []
        dm.progress = None

        # Mock widgets
        dm.filterbar = MagicMock()
        dm.filterbar.get_filters.return_value = {
            "active_region": (0,),
            "active_survey": (0,),
            "active_station": (0,),
            "active_viewpoint": (0,),
            "active_individual": (0,),
            "unidentified_only": False,
            "favorites_only": False,
            "no_roi_mids": False,
        }
        dm.filterbar.get_valid_stations.return_value = {1: "S1", 2: "S2"}
        dm.filters = dm.filterbar.get_filters()

        dm.media_table = MagicMock()
        dm.media_table._data_filtered = pd.DataFrame()
        dm.media_table.rowCount.return_value = 0
        dm.media_table.selectedRows.return_value = []

        dm.show_type = MagicMock()
        dm.button_save = MagicMock()
        dm.button_undo = MagicMock()
        dm.button_edit = MagicMock()
        dm.button_duplicate = MagicMock()
        dm.button_delete = MagicMock()
        dm.button_select = MagicMock()
        dm.count_label = MagicMock()
        dm.view = MagicMock()

        dm.SAVE_STYLE = " QPushButton { background-color: #2a3e5e; color: white; }"

        # Mock methods
        dm.show_progress = MagicMock()
        dm.update_prompt = MagicMock()
        dm.set_progress_max = MagicMock()
        dm.update_progress = MagicMock()
        dm.close_progress = MagicMock()
        dm.home = MagicMock()
        dm.handle_data_loaded = MagicMock()
        dm.refresh_table = MagicMock()
        dm.apply_edits = MagicMock()
        dm.filter_data = MagicMock()

    return dm


def _sample_roi_data():
    """Create sample ROI data for testing."""
    return pd.DataFrame({
        "id": [10, 11, 12],
        "media_id": [1, 1, 2],
        "station_id": [1, 1, 2],
        "individual_id": [100, 100, None],
        "viewpoint": [0, 1, None],
        "reviewed": [1, 0, 0],
        "favorite": [0, 1, 0],
        "comment": ["", "", ""],
        "select": [0, 0, 0],
        "sex": ["M", "F", None],
        "age": ["Adult", "Juvenile", None],
        "timestamp": ["2024-01-01", "2024-01-01", "2024-01-02"],
        "filepath": ["a.jpg", "b.jpg", "c.jpg"],
        "ext": [".jpg", ".jpg", ".jpg"],
        "thumbnail_path": ["a.jpg", "b.jpg", "c.jpg"],
    })


# ---------------------------------------------------------------------------
# TestLoadTable
# ---------------------------------------------------------------------------

class TestLoadTable:
    def test_load_table_no_media(self):
        """load_table returns False when no media in database."""
        dm = _make_display_media()
        dm.mpDB.count.side_effect = lambda tbl: 0
        
        # Create a proper mock progress dialog with rejected signal
        mock_progress = MagicMock()
        mock_progress.exec.return_value = True
        mock_progress.rejected = MagicMock()
        dm.progress = mock_progress
        
        result = dm.load_table()
        
        assert result is False
        dm.home.assert_called_once()

    def test_load_table_has_media(self):
        """load_table returns True when media exists."""
        dm = _make_display_media()
        dm.mpDB.count.side_effect = lambda tbl: (5 if tbl == "media" else 3)
        
        # Create a proper mock progress dialog with rejected signal
        mock_progress = MagicMock()
        mock_progress.rejected = MagicMock()
        dm.progress = mock_progress
        
        with patch("matchypatchy.gui.display_media.FetchTableThread") as mock_thread:
            with patch("matchypatchy.gui.display_media.fetch_individual", return_value=pd.DataFrame()):
                mock_instance = MagicMock()
                mock_thread.return_value = mock_instance
                result = dm.load_table()
        
        assert result is True
        mock_instance.start.assert_called_once()

    def test_load_table_no_rois_defaults_to_media(self):
        """When ROI mode is selected but no ROIs exist, default to media mode."""
        dm = _make_display_media()
        dm.data_type = 1
        dm.mpDB.count.side_effect = lambda tbl: (5 if tbl == "media" else 0)
        
        # Create a proper mock progress dialog with rejected signal
        mock_progress = MagicMock()
        mock_progress.rejected = MagicMock()
        dm.progress = mock_progress
        
        with patch("matchypatchy.gui.display_media.FetchTableThread") as mock_thread:
            with patch("matchypatchy.gui.display_media.fetch_individual", return_value=pd.DataFrame()):
                mock_instance = MagicMock()
                mock_thread.return_value = mock_instance
                result = dm.load_table()
        
        assert dm.data_type == 0
        assert result is True


# ---------------------------------------------------------------------------
# TestToggleFilterbarDatatype
# ---------------------------------------------------------------------------

class TestToggleFilterbarDatatype:
    def test_roi_mode_shows_roi_filters(self):
        """In ROI mode, show ROI-specific filters."""
        dm = _make_display_media()
        dm.data_type = 1
        dm.toggle_filterbar_datatype()
        
        dm.filterbar.individual_visible.assert_called_with(True)
        dm.filterbar.unidentified_visible.assert_called_with(True)
        dm.filterbar.favorites_visible.assert_called_with(True)
        dm.filterbar.viewpoint_visible.assert_called_with(True)
        dm.filterbar.no_roi_visible.assert_called_with(False)

    def test_media_mode_hides_roi_filters(self):
        """In media mode, hide ROI-specific filters."""
        dm = _make_display_media()
        dm.data_type = 0
        dm.toggle_filterbar_datatype()
        
        dm.filterbar.individual_visible.assert_called_with(False)
        dm.filterbar.unidentified_visible.assert_called_with(False)
        dm.filterbar.favorites_visible.assert_called_with(False)
        dm.filterbar.viewpoint_visible.assert_called_with(False)
        dm.filterbar.no_roi_visible.assert_called_with(True)


# ---------------------------------------------------------------------------
# TestUpdateCountLabel
# ---------------------------------------------------------------------------

class TestUpdateCountLabel:
    def test_count_label_total(self):
        """update_count_label displays total count."""
        dm = _make_display_media()
        dm.media_table.rowCount.return_value = 5
        dm.update_count_label()
        dm.count_label.setText.assert_called_with("Total Media: 5")

    def test_count_label_selected(self):
        """update_count_label_selected displays selection count."""
        dm = _make_display_media()
        dm.media_table.selectedRows.return_value = [0, 2, 4]
        dm.media_table.rowCount.return_value = 10
        dm.update_count_label()
        dm.count_label.setText.assert_called_with("Selected: 3 / 10")


# ---------------------------------------------------------------------------
# TestCheckUndoButton
# ---------------------------------------------------------------------------

class TestCheckUndoButton:
    def test_undo_enabled_when_stack_nonempty(self):
        """Undo button enabled when edit stack has items."""
        dm = _make_display_media()
        dm.edit_stack = [MagicMock()]
        dm.check_undo_button()
        dm.button_undo.setEnabled.assert_called_with(True)
        dm.button_save.setStyleSheet.assert_called_with(dm.SAVE_STYLE)

    def test_undo_disabled_when_stack_empty(self):
        """Undo button disabled when edit stack is empty."""
        dm = _make_display_media()
        dm.edit_stack = []
        dm.check_undo_button()
        dm.button_undo.setEnabled.assert_called_with(False)
        dm.button_save.setStyleSheet.assert_called_with("")


# ---------------------------------------------------------------------------
# TestHandleSelectionChange
# ---------------------------------------------------------------------------

class TestHandleSelectionChange:
    def test_buttons_enabled_with_selection(self):
        """Edit/Delete buttons enabled when rows selected."""
        dm = _make_display_media()
        dm.media_table.selectedRows.return_value = [0, 1]
        dm.handle_selection_change()
        dm.button_edit.setEnabled.assert_called_with(True)
        dm.button_delete.setEnabled.assert_called_with(True)

    def test_buttons_disabled_without_selection(self):
        """Edit/Delete buttons disabled when no rows selected."""
        dm = _make_display_media()
        dm.media_table.selectedRows.return_value = []
        dm.handle_selection_change()
        dm.button_edit.setEnabled.assert_called_with(False)
        dm.button_delete.setEnabled.assert_called_with(False)


# ---------------------------------------------------------------------------
# TestUndoEdit
# ---------------------------------------------------------------------------

class TestUndoEdit:
    def test_undo_pops_from_stack_and_refreshes(self):
        """undo() pops from edit stack and refreshes table."""
        dm = _make_display_media()
        dm._data_raw = _sample_roi_data()
        dm._data_filtered = _sample_roi_data()
        
        from matchypatchy.database.media import EditObject
        edit = EditObject(rid=10, mid=1, reference="reviewed",
                         previous_value=1, new_value=0)
        dm.edit_stack = [edit]
        dm._data_filtered.loc[0, "reviewed"] = 0

        dm.undo()

        # Verify edit was popped from stack
        assert len(dm.edit_stack) == 0
        # Verify refresh_table was called (it's a mock)
        dm.refresh_table.assert_called_once()
