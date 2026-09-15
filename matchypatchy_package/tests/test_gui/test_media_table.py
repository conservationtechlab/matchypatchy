"""
Unit tests for matchypatchy.gui.media_table.MediaTable

Tests focus on pure-Python logic methods that do not require a running Qt
display server. Qt widgets are stubbed out by conftest.py.
"""
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_media_table(data_type=1):
    """Build a MediaTable with all Qt dependencies mocked."""
    from matchypatchy.gui.media_table import MediaTable

    parent = MagicMock()
    parent.cfg = MagicMock()
    parent.cfg.THUMBNAIL_DIR = Path("/tmp/thumbs")
    parent.mpDB = MagicMock()
    # Use side_effect to return a new list each time select is called
    parent.mpDB.select.side_effect = lambda table, columns: [(1, "Cam1"), (2, "Cam2")]

    headers = {
        0: ["select", "Select"],
        1: ["thumbnail_path", "Thumbnail"],
        2: ["filepath", "Filepath"],
        3: ["timestamp", "Timestamp"],
        4: ["station_id", "Station"],
        5: ["camera_id", "Camera"],
        6: ["sequence_id", "Sequence ID"],
        7: ["external_id", "External ID"],
    }
    if data_type == 1:  # ROI mode
        headers.update({
            8: ["viewpoint", "Viewpoint"],
            9: ["individual_id", "Individual"],
            10: ["sex", "Sex"],
            11: ["age", "Age"],
            12: ["reviewed", "Reviewed"],
            13: ["favorite", "Favorite"],
            14: ["comment", "Comment"],
        })
    else:  # Media mode
        headers.update({
            8: ["comment", "Comment"],
            9: ["roi_count", "# of Rois"],
        })

    with patch("matchypatchy.gui.media_table.load_model",
               return_value={"None": "None", "0": "Left", "1": "Any", "2": "Right"}):
        with patch("matchypatchy.gui.media_table.fetch_individual",
                   return_value=pd.DataFrame({"id": [100, 200], "name": ["Ind-1", "Ind-2"]}).set_index("id")):
            with patch("matchypatchy.gui.media_table.fetch_stations",
                       return_value=pd.DataFrame({"id": [1, 2], "name": ["S1", "S2"]}).set_index("id")):
                # Do NOT mock MediaTable itself - instantiate it
                mt = MediaTable(parent, headers)
                mt._data_filtered = pd.DataFrame()
    
    return mt


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
        "sex": ["Male", "Female", None],
        "age": ["Adult", "Juvenile", None],
        "timestamp": ["2024-01-01", "2024-01-01", "2024-01-02"],
        "filepath": ["a.jpg", "b.jpg", "c.jpg"],
        "ext": [".jpg", ".jpg", ".jpg"],
        "thumbnail_path": ["a.jpg", "b.jpg", "c.jpg"],
    })


def _sample_media_data():
    """Create sample media data for testing."""
    return pd.DataFrame({
        "id": [1, 2, 3],
        "station_id": [1, 1, 2],
        "comment": ["", "", ""],
        "select": [0, 0, 0],
        "timestamp": ["2024-01-01", "2024-01-01", "2024-01-02"],
        "filepath": ["a.jpg", "b.jpg", "c.jpg"],
        "ext": [".jpg", ".jpg", ".jpg"],
        "thumbnail_path": ["a.jpg", "b.jpg", "c.jpg"],
        "roi_count": [5, 3, 2],
    })


# ---------------------------------------------------------------------------
# TestRowCount and ColumnCount
# ---------------------------------------------------------------------------

class TestRowAndColumnCount:
    def test_row_count_returns_data_length(self):
        """rowCount returns the number of rows in _data_filtered."""
        mt = _make_media_table()
        mt._data_filtered = _sample_roi_data()
        assert mt.rowCount() == 3

    def test_row_count_empty(self):
        """rowCount returns 0 for empty data."""
        mt = _make_media_table()
        mt._data_filtered = pd.DataFrame()
        assert mt.rowCount() == 0

    def test_column_count_returns_header_count(self):
        """columnCount returns number of columns."""
        mt = _make_media_table()
        assert mt.columnCount() == len(mt._headers)


# ---------------------------------------------------------------------------
# TestSelectedRows
# ---------------------------------------------------------------------------

class TestSelectedRows:
    def test_selected_rows_none_selected(self):
        """selectedRows returns empty list when nothing selected."""
        mt = _make_media_table()
        mt._data_filtered = _sample_roi_data()
        assert mt.selectedRows() == []

    def test_selected_rows_one_selected(self):
        """selectedRows returns correct row index."""
        mt = _make_media_table()
        df = _sample_roi_data()
        df.loc[1, "select"] = 1
        mt._data_filtered = df
        assert mt.selectedRows() == [1]

    def test_selected_rows_multiple_selected(self):
        """selectedRows returns all selected row indices."""
        mt = _make_media_table()
        df = _sample_roi_data()
        df.loc[0, "select"] = 1
        df.loc[2, "select"] = 1
        mt._data_filtered = df
        result = mt.selectedRows()
        assert set(result) == {0, 2}


# ---------------------------------------------------------------------------
# TestSelectAll
# ---------------------------------------------------------------------------

class TestSelectAll:
    def test_select_all_true(self):
        """selectAll(True) selects all rows."""
        mt = _make_media_table()
        mt._data_filtered = _sample_roi_data()
        mt.selectAll(select=True)
        assert all(mt._data_filtered["select"] == 1)

    def test_select_all_false(self):
        """selectAll(False) deselects all rows."""
        mt = _make_media_table()
        df = _sample_roi_data()
        df["select"] = 1
        mt._data_filtered = df
        mt.selectAll(select=False)
        assert all(mt._data_filtered["select"] == 0)


# ---------------------------------------------------------------------------
# TestFlags
# ---------------------------------------------------------------------------

class TestFlags:
    def test_flags_checkbox_columns(self):
        """Checkbox columns have ItemIsUserCheckable flag."""
        mt = _make_media_table()
        from PyQt6.QtCore import Qt, QModelIndex
        
        # "select" column is index 0
        index = QModelIndex()
        index._row = 0
        index._col = 0
        
        flags = mt.flags(index)
        # Should include ItemIsUserCheckable
        assert flags & Qt.ItemFlag.ItemIsUserCheckable

    def test_flags_editable_columns(self):
        """Editable columns have ItemIsEditable flag."""
        mt = _make_media_table()
        from PyQt6.QtCore import Qt, QModelIndex
        
        # "comment" column is index 14
        index = QModelIndex()
        index._row = 0
        index._col = 14
        
        flags = mt.flags(index)
        assert flags & Qt.ItemFlag.ItemIsEditable


# ---------------------------------------------------------------------------
# TestData
# ---------------------------------------------------------------------------

class TestData:
    def test_data_checkbox_display_role(self):
        """Checkbox columns return None for DisplayRole."""
        mt = _make_media_table()
        mt._data_filtered = _sample_roi_data()
        from PyQt6.QtCore import Qt, QModelIndex
        
        index = QModelIndex()
        index._row = 0
        index._col = 0  # "select" column
        
        result = mt.data(index, Qt.ItemDataRole.DisplayRole)
        assert result is None

    def test_data_station_id_display(self):
        """Station ID column displays station name."""
        mt = _make_media_table()
        df = _sample_roi_data()
        mt._data_filtered = df
        from PyQt6.QtCore import Qt, QModelIndex
        
        index = QModelIndex()
        index._row = 0
        index._col = 4  # "station_id" column
        
        result = mt.data(index, Qt.ItemDataRole.DisplayRole)
        assert result == "S1"

    def test_data_individual_id_display(self):
        """Individual ID column displays individual name."""
        mt = _make_media_table()
        df = _sample_roi_data()
        mt._data_filtered = df
        from PyQt6.QtCore import Qt, QModelIndex
        
        index = QModelIndex()
        index._row = 0
        index._col = 9  # "individual_id" column
        
        result = mt.data(index, Qt.ItemDataRole.DisplayRole)
        assert result == "Ind-1"

    def test_data_individual_none_display(self):
        """Individual ID column displays None string when unidentified."""
        mt = _make_media_table()
        df = _sample_roi_data()
        mt._data_filtered = df
        from PyQt6.QtCore import Qt, QModelIndex
        
        index = QModelIndex()
        index._row = 2  # ROI with None individual_id
        index._col = 9
        
        result = mt.data(index, Qt.ItemDataRole.DisplayRole)
        assert result == "None"


# ---------------------------------------------------------------------------
# TestSetData
# ---------------------------------------------------------------------------

class TestSetData:
    def test_set_data_checkbox_change(self):
        """setData handles checkbox state changes."""
        mt = _make_media_table()
        df = _sample_roi_data()
        mt._data_filtered = df
        from PyQt6.QtCore import Qt, QModelIndex
        
        index = QModelIndex()
        index._row = 0
        index._col = 0  # "select" column
        
        result = mt.setData(index, Qt.CheckState.Checked, Qt.ItemDataRole.EditRole)
        assert result is True
        assert mt._data_filtered.at[0, "select"] == 1

    def test_set_data_emits_user_edit_signal(self):
        """setData emits user_edit signal."""
        mt = _make_media_table()
        df = _sample_roi_data()
        mt._data_filtered = df
        from PyQt6.QtCore import Qt, QModelIndex
        
        signal_captured = []
        mt.user_edit.connect(lambda edit: signal_captured.append(edit))
        
        index = QModelIndex()
        index._row = 0
        index._col = 14  # "comment" column
        
        mt.setData(index, "test comment", Qt.ItemDataRole.EditRole)
        
        assert len(signal_captured) == 1
        assert signal_captured[0].reference == "comment"
        assert signal_captured[0].new_value == "test comment"

    def test_set_data_viewpoint_conversion(self):
        """setData converts viewpoint display value to internal value."""
        mt = _make_media_table()
        df = _sample_roi_data()
        mt._data_filtered = df
        from PyQt6.QtCore import Qt, QModelIndex
        
        index = QModelIndex()
        index._row = 0
        index._col = 8  # "viewpoint" column
        
        # "Left" in VIEWPOINTS dict maps to "0"
        mt.setData(index, "Left", Qt.ItemDataRole.EditRole)
        
        assert mt._data_filtered.at[0, "viewpoint"] == 0


# ---------------------------------------------------------------------------
# TestReceiveData
# ---------------------------------------------------------------------------

class TestReceiveData:
    def test_receive_data_updates_filtered(self):
        """receiveData updates _data_filtered."""
        mt = _make_media_table()
        data = _sample_roi_data()
        
        mt.receiveData(data)
        
        pd.testing.assert_frame_equal(mt._data_filtered, data)

    def test_receive_data_with_headers(self):
        """receiveData updates headers when provided."""
        mt = _make_media_table()
        data = _sample_roi_data()
        new_headers = {0: ["select", "Select"], 1: ["id", "ID"]}
        
        mt.receiveData(data, headers=new_headers)
        
        assert mt.header_dict == new_headers
        assert mt._columns[0] == "select"
        assert mt._columns[1] == "id"


# ---------------------------------------------------------------------------
# TestUpdateMethods
# ---------------------------------------------------------------------------

class TestUpdateMethods:
    def test_update_individuals(self):
        """updateIndividuals fetches individual data from database."""
        mt = _make_media_table()
        mt.updateIndividuals()
        
        assert not mt.INDIVIDUALS.empty
        assert "name" in mt.INDIVIDUALS.columns

    def test_update_stations(self):
        """updateStations fetches station data from database."""
        mt = _make_media_table()
        mt.updateStations()
        
        assert not mt.STATIONS.empty
        assert "name" in mt.STATIONS.columns


# ---------------------------------------------------------------------------
# TestHeaderData
# ---------------------------------------------------------------------------

class TestHeaderData:
    def test_header_data_horizontal(self):
        """headerData returns column names for horizontal headers."""
        mt = _make_media_table()
        from PyQt6.QtCore import Qt
        
        result = mt.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        assert result == "Select"

    def test_header_data_vertical(self):
        """headerData returns row numbers for vertical headers."""
        mt = _make_media_table()
        from PyQt6.QtCore import Qt
        
        result = mt.headerData(0, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole)
        assert result == "1"


# ---------------------------------------------------------------------------
# TestSort
# ---------------------------------------------------------------------------

class TestSort:
    def test_sort_ascending(self):
        """sort sorts data in ascending order."""
        mt = _make_media_table()
        df = _sample_roi_data()
        mt._data_filtered = df
        from PyQt6.QtCore import Qt
        
        # Sort by column 3 (timestamp) ascending
        mt.sort(3, Qt.SortOrder.AscendingOrder)
        
        assert mt._data_filtered["timestamp"].iloc[0] <= mt._data_filtered["timestamp"].iloc[1]

    def test_sort_descending(self):
        """sort sorts data in descending order."""
        mt = _make_media_table()
        df = _sample_roi_data()
        mt._data_filtered = df
        from PyQt6.QtCore import Qt
        
        # Sort by column 3 (timestamp) descending
        mt.sort(3, Qt.SortOrder.DescendingOrder)
        
        assert mt._data_filtered["timestamp"].iloc[0] >= mt._data_filtered["timestamp"].iloc[1]

    def test_sort_skips_thumbnail_column(self):
        """sort does not sort by thumbnail column."""
        mt = _make_media_table()
        df = _sample_roi_data()
        original_order = df.copy()
        mt._data_filtered = df
        from PyQt6.QtCore import Qt
        
        # Try to sort by thumbnail column (index 1)
        mt.sort(1, Qt.SortOrder.AscendingOrder)
        
        # Data should remain unchanged
        pd.testing.assert_frame_equal(mt._data_filtered, original_order)

    def test_sort_empty_data(self):
        """sort handles empty data gracefully."""
        mt = _make_media_table()
        mt._data_filtered = pd.DataFrame()
        from PyQt6.QtCore import Qt
        
        # Should not raise exception
        mt.sort(0, Qt.SortOrder.AscendingOrder)
        assert mt._data_filtered.empty
