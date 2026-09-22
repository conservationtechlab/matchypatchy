"""
Unit tests for matchypatchy.gui.media_table.MediaTable

Tests focus on pure-Python logic methods that do not require a running Qt
display server. Qt widgets are stubbed out by conftest.py.
"""
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_headers():
    """Return a minimal header dict matching MediaTable's expected format."""
    return {
        0: ("select",         ""),
        1: ("thumbnail_path", "Thumbnail"),
        2: ("filepath",       "File"),
        3: ("timestamp",      "Time"),
        4: ("station_id",     "Station"),
        5: ("comment",        "Comment"),
    }


def _make_media_table():
    """Build a MediaTable instance with all external dependencies mocked."""
    from matchypatchy.gui.media_table import MediaTable

    parent = MagicMock()
    parent.cfg = MagicMock()
    parent.cfg.THUMBNAIL_DIR = "/tmp/thumbs"
    parent.mpDB = MagicMock()

    with patch("matchypatchy.gui.media_table.load_model",
               return_value={"None": "None", "0": "Left", "1": "Right"}):
        with patch("matchypatchy.gui.media_table.fetch_individual",
                   return_value=pd.DataFrame(columns=["id", "name"])):
            with patch("matchypatchy.gui.media_table.fetch_stations",
                       return_value=pd.DataFrame(columns=["id", "name"])):
                with patch("matchypatchy.gui.media_table.fetch_cameras",
                           return_value=pd.DataFrame(columns=["id", "name"])):
                    mt = MediaTable(parent, _make_headers())
    return mt


def _sample_df():
    """Minimal DataFrame with required columns."""
    return pd.DataFrame({
        "select":         [0, 1, 0],
        "thumbnail_path": ["a.jpg", "b.jpg", "c.jpg"],
        "filepath":       ["/f/a.jpg", "/f/b.jpg", "/f/c.jpg"],
        "timestamp":      ["2024-01-01", "2024-01-02", "2024-01-03"],
        "station_id":     [1, 2, 1],
        "comment":        ["", "hi", ""],
    })


# ---------------------------------------------------------------------------
# TestRowColumnCount
# ---------------------------------------------------------------------------

class TestRowColumnCount:
    def test_rowcount_empty(self):
        mt = _make_media_table()
        assert mt.rowCount() == 0

    def test_rowcount_with_data(self):
        mt = _make_media_table()
        mt._data_filtered = _sample_df()
        assert mt.rowCount() == 3

    def test_columncount_matches_headers(self):
        mt = _make_media_table()
        assert mt.columnCount() == len(_make_headers())


# ---------------------------------------------------------------------------
# TestSelectedRows
# ---------------------------------------------------------------------------

class TestSelectedRows:
    def test_selected_rows_none_selected(self):
        """selectedRows returns empty list when nothing selected."""
        mt = _make_media_table()
        df = _sample_df()
        df["select"] = 0  # ensure nothing is selected
        mt._data_filtered = df
        assert mt.selectedRows() == []

    def test_selected_rows_one_selected(self):
        """selectedRows returns correct row index."""
        mt = _make_media_table()
        mt._data_filtered = _sample_df()
        result = mt.selectedRows()
        assert result == [1]

    def test_selected_rows_multiple_selected(self):
        """selectedRows returns all selected row indices."""
        mt = _make_media_table()
        df = _sample_df()
        df.loc[0, "select"] = 1
        df.loc[2, "select"] = 1
        mt._data_filtered = df
        assert set(mt.selectedRows()) == {0, 1, 2}


# ---------------------------------------------------------------------------
# TestSelectAll
# ---------------------------------------------------------------------------

class TestSelectAll:
    def test_select_all_marks_all_rows(self):
        mt = _make_media_table()
        mt._data_filtered = _sample_df()
        mt.selectAll(select=True)
        assert list(mt._data_filtered["select"]) == [1, 1, 1]

    def test_deselect_all_clears_all_rows(self):
        mt = _make_media_table()
        mt._data_filtered = _sample_df()
        mt.selectAll(select=False)
        assert list(mt._data_filtered["select"]) == [0, 0, 0]


# ---------------------------------------------------------------------------
# TestSort
# ---------------------------------------------------------------------------

class TestSort:
    def test_sort_ascending_by_column(self):
        mt = _make_media_table()
        from PyQt6.QtCore import Qt
        mt._data_filtered = _sample_df()
        # Sort by station_id (col 4) ascending
        mt.sort(4, Qt.SortOrder.AscendingOrder)
        assert list(mt._data_filtered["station_id"]) == [1, 1, 2]

    def test_sort_descending_by_column(self):
        mt = _make_media_table()
        from PyQt6.QtCore import Qt
        mt._data_filtered = _sample_df()
        mt.sort(4, Qt.SortOrder.DescendingOrder)
        assert list(mt._data_filtered["station_id"]) == [2, 1, 1]

    def test_sort_skips_thumbnail_column(self):
        mt = _make_media_table()
        from PyQt6.QtCore import Qt
        mt._data_filtered = _sample_df()
        original_order = list(mt._data_filtered["filepath"])
        mt.sort(1, Qt.SortOrder.AscendingOrder)  # column 1 = thumbnail_path
        assert list(mt._data_filtered["filepath"]) == original_order

    def test_sort_empty_data_is_noop(self):
        mt = _make_media_table()
        from PyQt6.QtCore import Qt
        mt._data_filtered = pd.DataFrame()
        mt.sort(0, Qt.SortOrder.AscendingOrder)  # should not raise


# ---------------------------------------------------------------------------
# TestReceiveData
# ---------------------------------------------------------------------------

class TestReceiveData:
    def test_receive_data_sets_data_filtered(self):
        mt = _make_media_table()
        df = _sample_df()
        with patch("matchypatchy.gui.media_table.fetch_individual",
                   return_value=pd.DataFrame(columns=["id", "name"])):
            with patch("matchypatchy.gui.media_table.fetch_stations",
                       return_value=pd.DataFrame(columns=["id", "name"])):
                with patch("matchypatchy.gui.media_table.fetch_cameras",
                           return_value=pd.DataFrame(columns=["id", "name"])):
                    mt.receiveData(df)
        assert len(mt._data_filtered) == 3

    def test_receive_data_with_selected_rows(self):
        mt = _make_media_table()
        df = _sample_df()
        df["select"] = 0
        with patch("matchypatchy.gui.media_table.fetch_individual",
                   return_value=pd.DataFrame(columns=["id", "name"])):
            with patch("matchypatchy.gui.media_table.fetch_stations",
                       return_value=pd.DataFrame(columns=["id", "name"])):
                with patch("matchypatchy.gui.media_table.fetch_cameras",
                           return_value=pd.DataFrame(columns=["id", "name"])):
                    mt.receiveData(df, selected_rows=[0, 2])
        assert mt._data_filtered.loc[0, "select"] == 1
        assert mt._data_filtered.loc[1, "select"] == 0
        assert mt._data_filtered.loc[2, "select"] == 1

    def test_receive_data_updates_headers(self):
        mt = _make_media_table()
        new_headers = {
            0: ("select", ""),
            1: ("filepath", "Path"),
        }
        df = pd.DataFrame({"select": [0], "filepath": ["/a/b.jpg"]})
        with patch("matchypatchy.gui.media_table.fetch_individual",
                   return_value=pd.DataFrame(columns=["id", "name"])):
            with patch("matchypatchy.gui.media_table.fetch_stations",
                       return_value=pd.DataFrame(columns=["id", "name"])):
                with patch("matchypatchy.gui.media_table.fetch_cameras",
                           return_value=pd.DataFrame(columns=["id", "name"])):
                    mt.receiveData(df, headers=new_headers)
        assert mt._headers == ["", "Path"]
        assert mt._columns == ["select", "filepath"]


# ---------------------------------------------------------------------------
# TestUpdateHeaderDict
# ---------------------------------------------------------------------------

class TestUpdateHeaderDict:
    def test_update_changes_columns_and_headers(self):
        mt = _make_media_table()
        new_headers = {0: ("id", "ID"), 1: ("comment", "Note")}
        mt.updateHeaderDict(new_headers)
        assert mt._columns == ["id", "comment"]
        assert mt._headers == ["ID", "Note"]

    def test_update_with_none_is_noop(self):
        mt = _make_media_table()
        original_columns = list(mt._columns)
        mt.updateHeaderDict(None)
        assert mt._columns == original_columns
