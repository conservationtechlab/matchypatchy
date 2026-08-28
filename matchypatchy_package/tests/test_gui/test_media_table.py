"""
Unit tests for matchypatchy.gui.media_table.MediaTable

Tests focus on pure-Python logic methods that do not require a running Qt
display server.  Qt widgets are stubbed out by conftest.py.
"""
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cfg():
    cfg = MagicMock()
    cfg.THUMBNAIL_DIR = "/tmp/thumbs"
    return cfg


def _make_mpdb():
    db = MagicMock()
    db.select.return_value = []
    return db


def _sample_roi_filtered():
    """Minimal data_filtered DataFrame for ROI mode."""
    return pd.DataFrame(
        {
            "id":           [10, 11, 12],
            "media_id":     [1,  1,  2],
            "station_id":   [1,  1,  2],
            "station":      ["S1", "S1", "S2"],
            "individual_id": [100, 100, None],
            "viewpoint":    [0,    1,   None],
            "reviewed":     [1,    0,   0],
            "favorite":     [0,    1,   0],
            "comment":      ["",  "",   ""],
            "select":       [0,    0,   0],
            "sex":          ["Male", "Female", None],
            "age":          ["Adult", "Juvenile", None],
        }
    )


def _make_media_table():
    """Build a MediaTable with all Qt dependencies mocked."""
    from matchypatchy.gui.media_table import MediaTable

    parent = MagicMock()
    parent.cfg = _make_cfg()
    parent.mpDB = _make_mpdb()
    parent.filters = {
        "active_region":    (0,),
        "active_survey":    (0,),
        "active_station":   (0,),
        "active_viewpoint": (0,),
        "active_individual":(0,),
        "unidentified_only": False,
        "favorites_only":   False,
        "no_roi_mids":      False,
    }
    parent.valid_stations = {1: "S1", 2: "S2"}

    with patch("matchypatchy.gui.media_table.load_model",
               return_value={"None": "None", "0": "Left", "1": "Any", "2": "Right"}):
        with patch("matchypatchy.gui.media_table.fetch_individual",
                   return_value=pd.DataFrame({"id": [100], "name": ["Ind-1"]})):
            mt = MediaTable.__new__(MediaTable)
            mt.parent = parent
            mt.cfg = parent.cfg
            mt.mpDB = parent.mpDB
            mt.data = pd.DataFrame()
            mt.data_filtered = pd.DataFrame()
            mt.individual_list = pd.DataFrame()
            mt.thumbnails = {}
            mt.data_type = 1
            mt.VIEWPOINTS = {"None": "None", "0": "Left", "1": "Any", "2": "Right"}
            mt.thumbnail_size = 150
            mt.thumbnail_dir = "/tmp/thumbs"
            mt.valid_stations = {1: "S1", 2: "S2"}
            mt.valid_cameras = {}
            mt.edit_stack = []
            # Qt objects
            mt.table = MagicMock()
            mt.table.rowCount.return_value = 3
            mt.columns = {
                0: "select", 1: "thumbnail", 2: "filepath", 3: "timestamp",
                4: "station", 5: "camera_id", 6: "sequence_id", 7: "external_id",
                8: "viewpoint", 9: "individual_id", 10: "sex", 11: "age",
                12: "reviewed", 13: "favorite", 14: "comment",
            }
            # Signals
            from tests.conftest import _SignalStub
            mt.update_signal = _SignalStub()
            mt.checkbox_signal = _SignalStub()
            mt.loaded_data = _SignalStub()
    return mt


# ---------------------------------------------------------------------------
# TestSelectedRows
# ---------------------------------------------------------------------------

class TestSelectedRows:
    def test_no_selection_returns_empty(self):
        mt = _make_media_table()
        mt.data_filtered = _sample_roi_filtered()
        assert mt.selectedRows() == []

    def test_selected_rows_returns_correct_indices(self):
        mt = _make_media_table()
        df = _sample_roi_filtered()
        df.loc[1, "select"] = 1
        mt.data_filtered = df
        result = mt.selectedRows()
        assert result == [1]

    def test_multiple_selected_rows(self):
        mt = _make_media_table()
        df = _sample_roi_filtered()
        df.loc[0, "select"] = 1
        df.loc[2, "select"] = 1
        mt.data_filtered = df
        result = mt.selectedRows()
        assert set(result) == {0, 2}


# ---------------------------------------------------------------------------
# TestGetEditTableItem
# ---------------------------------------------------------------------------

class TestGetEditTableItem:
    def test_finds_existing_roi(self):
        mt = _make_media_table()
        mt.data_filtered = _sample_roi_filtered()
        mt.data_type = 1

        from matchypatchy.database.media import EditObject
        edit = EditObject(rid=11, mid=1, reference="reviewed",
                          previous_value=0, new_value=1)
        row, col = mt.get_edit_table_item(edit)
        assert row == 1
        assert col == "reviewed"

    def test_returns_none_for_missing_rid(self):
        mt = _make_media_table()
        mt.data_filtered = _sample_roi_filtered()
        mt.data_type = 1

        from matchypatchy.database.media import EditObject
        edit = EditObject(rid=None, mid=1, reference="reviewed",
                          previous_value=0, new_value=1)
        row, col = mt.get_edit_table_item(edit)
        assert row is None
        assert col is None

    def test_returns_none_when_rid_not_in_data(self):
        mt = _make_media_table()
        mt.data_filtered = _sample_roi_filtered()
        mt.data_type = 1

        from matchypatchy.database.media import EditObject
        edit = EditObject(rid=9999, mid=1, reference="reviewed",
                          previous_value=0, new_value=1)
        row, col = mt.get_edit_table_item(edit)
        assert row is None

    def test_media_mode_uses_mid(self):
        mt = _make_media_table()
        mt.data_type = 0
        df = pd.DataFrame({"id": [1, 2], "select": [0, 0]})
        mt.data_filtered = df

        from matchypatchy.database.media import EditObject
        edit = EditObject(rid=None, mid=2, reference="comment",
                          previous_value="", new_value="new")
        row, col = mt.get_edit_table_item(edit)
        assert row == 1
        assert col == "comment"


# ---------------------------------------------------------------------------
# TestApplyEdits
# ---------------------------------------------------------------------------

class TestApplyEdits:
    def test_apply_edits_no_edits_noop(self):
        mt = _make_media_table()
        mt.data_filtered = _sample_roi_filtered()
        original = mt.data_filtered["reviewed"].copy()
        mt.apply_edits()
        pd.testing.assert_series_equal(mt.data_filtered["reviewed"], original)

    def test_apply_edits_updates_value(self):
        mt = _make_media_table()
        mt.data_filtered = _sample_roi_filtered()

        from matchypatchy.database.media import EditObject
        edit = EditObject(rid=10, mid=1, reference="reviewed",
                          previous_value=1, new_value=0)
        mt.edit_stack = [edit]
        mt.apply_edits()
        assert mt.data_filtered.loc[0, "reviewed"] == 0

    def test_apply_edits_skips_missing_column(self):
        mt = _make_media_table()
        mt.data_filtered = _sample_roi_filtered()

        from matchypatchy.database.media import EditObject
        edit = EditObject(rid=10, mid=1, reference="nonexistent_col",
                          previous_value=None, new_value="x")
        mt.edit_stack = [edit]
        # Should not raise even if column not in data_filtered
        mt.apply_edits()


# ---------------------------------------------------------------------------
# TestUndoEdit
# ---------------------------------------------------------------------------

class TestUndoEdit:
    def test_undo_reverts_last_edit(self):
        mt = _make_media_table()
        mt.data_filtered = _sample_roi_filtered()

        from matchypatchy.database.media import EditObject
        edit = EditObject(rid=10, mid=1, reference="reviewed",
                          previous_value=1, new_value=0)
        mt.edit_stack = [edit]
        mt.data_filtered.loc[0, "reviewed"] = 0  # simulate applied edit

        with patch.object(mt, "refresh_table"):
            mt.undo()

        assert mt.data_filtered.loc[0, "reviewed"] == 1
        assert len(mt.edit_stack) == 0

    def test_undo_does_nothing_on_empty_stack(self):
        mt = _make_media_table()
        mt.data_filtered = _sample_roi_filtered()
        mt.edit_stack = []
        original = mt.data_filtered["reviewed"].copy()
        with patch.object(mt, "refresh_table"):
            mt.undo()
        pd.testing.assert_series_equal(mt.data_filtered["reviewed"], original)


# ---------------------------------------------------------------------------
# TestFilterLogic
# ---------------------------------------------------------------------------

class TestFilterLogic:
    def test_filter_empty_valid_stations_empties_data(self):
        mt = _make_media_table()
        mt.data = _sample_roi_filtered()
        mt.parent.valid_stations = {}
        mt.parent.filters = {
            "active_station": (0,), "active_viewpoint": (0,),
            "active_individual": (0,), "unidentified_only": False,
            "favorites_only": False, "no_roi_mids": False,
        }
        with patch.object(mt, "refresh_table"):
            with patch("matchypatchy.gui.media_table.fetch_individual",
                       return_value=pd.DataFrame()):
                mt.filter()
        assert mt.data_filtered.empty

    def test_filter_station_match(self):
        mt = _make_media_table()
        mt.data = _sample_roi_filtered()
        mt.data.rename(columns={"station": "station_name"}, inplace=True)
        # Re-add station col
        mt.data["station"] = mt.data["station_name"]
        mt.parent.valid_stations = {1: "S1"}
        mt.mpDB.select.return_value = [(1, "Cam1")]
        mt.parent.filters = {
            "active_station": (1,), "active_viewpoint": (0,),
            "active_individual": (0,), "unidentified_only": False,
            "favorites_only": False, "no_roi_mids": False,
        }
        with patch.object(mt, "refresh_table"):
            with patch("matchypatchy.gui.media_table.fetch_individual",
                       return_value=pd.DataFrame()):
                mt.filter()
        assert all(mt.data_filtered["station_id"] == 1)

    def test_filter_favorites_only(self):
        mt = _make_media_table()
        mt.data = _sample_roi_filtered()
        mt.parent.valid_stations = {1: "S1", 2: "S2"}
        mt.mpDB.select.return_value = [(1, "Cam1")]
        mt.parent.filters = {
            "active_station": (0,), "active_viewpoint": (0,),
            "active_individual": (0,), "unidentified_only": False,
            "favorites_only": True, "no_roi_mids": False,
        }
        with patch.object(mt, "refresh_table"):
            with patch("matchypatchy.gui.media_table.fetch_individual",
                       return_value=pd.DataFrame()):
                mt.filter()
        assert all(mt.data_filtered["favorite"] == 1)

    def test_filter_unidentified_only(self):
        mt = _make_media_table()
        mt.data = _sample_roi_filtered()
        mt.parent.valid_stations = {1: "S1", 2: "S2"}
        mt.mpDB.select.return_value = [(1, "Cam1")]
        mt.parent.filters = {
            "active_station": (0,), "active_viewpoint": (0,),
            "active_individual": (0,), "unidentified_only": True,
            "favorites_only": False, "no_roi_mids": False,
        }
        with patch.object(mt, "refresh_table"):
            with patch("matchypatchy.gui.media_table.fetch_individual",
                       return_value=pd.DataFrame()):
                mt.filter()
        assert all(mt.data_filtered["individual_id"].isna())


# ---------------------------------------------------------------------------
# TestEditStack
# ---------------------------------------------------------------------------

class TestEditStack:
    def test_add_edit_stack_appends(self):
        mt = _make_media_table()
        mt.data_filtered = _sample_roi_filtered()

        from matchypatchy.database.media import EditObject
        edits = [
            EditObject(rid=10, mid=1, reference="reviewed",
                       previous_value=1, new_value=0),
        ]
        with patch.object(mt, "refresh_table"):
            mt.add_edit_stack(edits)
        assert len(mt.edit_stack) == 1

    def test_save_changes_clears_edit_stack(self):
        mt = _make_media_table()
        mt.data_filtered = _sample_roi_filtered()
        mt.data_type = 1

        from matchypatchy.database.media import EditObject
        edit = EditObject(rid=10, mid=1, reference="reviewed",
                          previous_value=1, new_value=0)
        mt.edit_stack = [edit]

        with patch.object(mt, "clear_and_load_contents"):
            mt.save_changes()

        assert mt.edit_stack == []
        mt.mpDB.edit_row.assert_called()

    def test_save_changes_media_mode(self):
        mt = _make_media_table()
        mt.data_filtered = pd.DataFrame({"id": [1], "select": [0]})
        mt.data_type = 0

        from matchypatchy.database.media import EditObject
        edit = EditObject(rid=None, mid=1, reference="comment",
                          previous_value="", new_value="updated")
        mt.edit_stack = [edit]

        with patch.object(mt, "clear_and_load_contents"):
            mt.save_changes()

        mt.mpDB.edit_row.assert_called_with(
            "media", 1, {"comment": "updated"}, allow_none=False, quiet=False
        )
