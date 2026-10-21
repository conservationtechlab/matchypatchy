"""
Unit tests for matchypatchy.gui.display_media.DisplayMedia

Tests focus on pure-Python helper/logic methods that do not require a
real Qt display server. Qt widgets are stubbed out by conftest.py.
"""
from types import SimpleNamespace

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
        dm.project = SimpleNamespace(db=parent.mpDB, cfg=parent.cfg, changed=MagicMock())
        dm.VIEWPOINTS = {"None": "None", "0": "Left", "1": "Any", "2": "Right"}
        dm.data_type = 1  # ROI mode
        dm.valid_stations = {1: "S1", 2: "S2"}
        dm._data_raw = pd.DataFrame()
        dm._data_filtered = pd.DataFrame()
        dm.edit_stack = []
        dm.progress = None
        dm._load_id = 0
        dm._loaders = []

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


# ---------------------------------------------------------------------------
# Viewpoint filter
# ---------------------------------------------------------------------------

class TestViewpointFilter:
    """models.yml labels stored viewpoints '0': Left, '1': Right"""

    @pytest.fixture(autouse=True)
    def _labels(self):
        with patch("matchypatchy.threads.match_object.load_model",
                   return_value={"Any": "Any", "None": "None", "0": "Left", "1": "Right"}):
            yield

    def _filter(self, viewpoint):
        from matchypatchy.gui.display_media import DisplayMedia
        dm = _make_display_media()
        dm.mpDB.select.return_value = []
        dm._data_filtered = pd.DataFrame({"id": [10, 11, 12], "station_id": [1, 1, 1],
                                          "viewpoint": [0, 1, None], "individual_id": [None] * 3,
                                          "favorite": [0, 0, 0]})
        dm.filters = dict(dm.filters, active_viewpoint=viewpoint)
        DisplayMedia.filter_data(dm)  # the helper mocks filter_data
        return dm._data_filtered["id"].tolist()

    def test_left_shows_left_labelled_rois(self):
        assert self._filter((1, "Left")) == [10]

    def test_right_shows_right_labelled_rois(self):
        assert self._filter((2, "Right")) == [11]

    def test_no_viewpoint_filter(self):
        assert self._filter((0, "Viewpoint")) == [10, 11, 12]


# ---------------------------------------------------------------------------
# Selection across refresh
# ---------------------------------------------------------------------------

class TestSelectionAcrossRefresh:
    def test_refresh_passes_selected_ids(self):
        from matchypatchy.gui.display_media import DisplayMedia
        dm = _make_display_media()
        dm.media_table.selectedIds.return_value = [11]
        dm._apply_sort = MagicMock()
        DisplayMedia.refresh_table(dm)
        assert dm.media_table.receiveData.call_args.kwargs["selected_ids"] == [11]


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def _edit(rid, mid, reference, new_value):
    from matchypatchy.database.media import EditObject
    return EditObject(rid=rid, mid=mid, reference=reference, previous_value=None, new_value=new_value)


class TestSave:
    def _save(self, edits, data_type=1, edit_ok=True):
        from matchypatchy.gui.display_media import DisplayMedia
        dm = _make_display_media()
        dm.data_type = data_type
        dm._data_raw = _sample_roi_data()          # ids 10, 11 -> individual 100; 12 none
        dm._data_filtered = dm._data_raw.iloc[[2]]  # 10 and 11 hidden by a filter
        dm.edit_stack = list(edits)
        dm.mpDB.edit_row.return_value = edit_ok
        with patch("matchypatchy.gui.display_media.AlertPopup") as popup:
            DisplayMedia.save(dm)
        return dm, popup

    def test_clearing_a_value_is_saved(self):
        """Setting a name to Unknown or viewpoint to None stores NULL instead of being refused"""
        dm, _ = self._save([_edit(10, 1, "individual_id", None), _edit(10, 1, "viewpoint", None)])
        dm.mpDB.edit_row.assert_any_call("roi", 10, {"individual_id": None}, allow_none=True)
        dm.mpDB.edit_row.assert_any_call("roi", 10, {"viewpoint": None}, allow_none=True)
        assert dm.edit_stack == []

    def test_media_columns_use_media_id(self):
        dm, _ = self._save([_edit(10, 1, "comment", "")])
        dm.mpDB.edit_row.assert_called_once_with("media", 1, {"comment": ""}, allow_none=True)

    def test_media_view_edits_media(self):
        dm, _ = self._save([_edit(None, 2, "external_id", "x")], data_type=0)
        dm.mpDB.edit_row.assert_called_once_with("media", 2, {"external_id": "x"}, allow_none=True)

    def test_sex_for_roi_hidden_by_filter(self):
        dm, _ = self._save([_edit(10, 1, "sex", "F")])
        dm.mpDB.edit_row.assert_called_once_with("individual", 100, {"sex": "F"}, allow_none=True)

    def test_sex_follows_name_change_in_same_save(self):
        dm, _ = self._save([_edit(12, 2, "individual_id", 7), _edit(12, 2, "sex", "M")])
        assert dm.mpDB.edit_row.call_args_list[-1].args == ("individual", 7, {"sex": "M"})

    def test_row_without_roi_id_is_skipped(self):
        dm, _ = self._save([_edit(pd.NA, 1, "viewpoint", 1)])
        dm.mpDB.edit_row.assert_not_called()

    def test_failed_edits_are_kept_and_reported(self):
        edit = _edit(10, 1, "viewpoint", 1)
        dm, popup = self._save([edit], edit_ok=False)
        assert dm.edit_stack == [edit]
        popup.assert_called_once()

    def test_reloads_after_saving(self):
        dm, _ = self._save([_edit(10, 1, "viewpoint", 1)])
        dm.refresh_table.assert_called_once_with(reload=True)


class TestUndoButtonState:
    def test_undo_last_edit_updates_buttons(self):
        from matchypatchy.gui.display_media import DisplayMedia
        dm = _make_display_media()
        dm.edit_stack = [_edit(10, 1, "viewpoint", 1)]
        DisplayMedia.undo(dm)
        dm.button_undo.setEnabled.assert_called_with(False)


class TestProjectChanged:
    def test_switching_project_drops_edits(self):
        dm = _make_display_media()
        dm.edit_stack = [_edit(10, 1, "viewpoint", 1)]
        dm.drop_edits()
        assert dm.edit_stack == []
        dm.button_undo.setEnabled.assert_called_with(False)

    def test_reads_the_open_project(self):
        """mpDB and cfg follow the project instead of a copy taken at startup"""
        dm = _make_display_media()
        db, cfg = MagicMock(), MagicMock()
        dm.project.db, dm.project.cfg = db, cfg
        assert dm.mpDB is db
        assert dm.cfg is cfg


class TestCompareSelection:
    def test_compare_uses_ticked_rows(self):
        """Compare sends the rois ticked in the Select column, not the highlighted rows"""
        from matchypatchy.gui.display_media import DisplayMedia
        dm = _make_display_media()
        dm.media_table._data_filtered = _sample_roi_data()
        dm.media_table.selectedIds.return_value = [10, 12]
        dm.view.selectionModel.return_value.selectedRows.return_value = []  # nothing highlighted
        with patch("matchypatchy.gui.display_media.AlertPopup") as popup, \
             patch("matchypatchy.gui.display_media.QDialog") as qdialog:
            popup.return_value.exec.return_value = qdialog.DialogCode.Accepted
            DisplayMedia.compare(dm)
        dm.parent._set_manual_view.assert_called_once_with(selected_ids=[10, 12])
        dm.parent._set_compare_view.assert_not_called()


class TestSexDelegate:
    def test_sex_combo_offers_unknown(self):
        """The Sex column offers Unknown like the edit popups, not 'None'"""
        from matchypatchy.gui.display_media import DisplayMedia
        dm = _make_display_media()
        with patch("matchypatchy.gui.display_media.ComboBoxDelegate") as delegate:
            DisplayMedia._set_delegates(dm)
        assert ['Unknown', 'Male', 'Female'] in [c.args[0] for c in delegate.call_args_list]


class TestIndividualPrefilter:
    """View from Manage Individuals filters rois, so the view must show rois"""

    def _refresh(self, prefilter):
        from matchypatchy.gui.display_media import DisplayMedia
        dm = _make_display_media()
        dm.data_type = 0  # left on Full Images
        DisplayMedia.refresh_filters(dm, prefilter=prefilter)
        return dm

    @pytest.mark.parametrize("prefilter", [{"individual_id": 5}, {"individual_id": 0},
                                           {"unidentified_only": True}])
    def test_switches_to_rois(self, prefilter):
        dm = self._refresh(prefilter)
        assert dm.data_type == 1
        dm.show_type.setCurrentIndex.assert_called_once_with(1)
        # signals blocked so change_type does not load the table a second time
        dm.show_type.blockSignals.assert_any_call(True)
        dm.filterbar.individual_visible.assert_called_with(True)

    @pytest.mark.parametrize("prefilter", [None, {"no_roi_mids": [1, 2]}])
    def test_other_filters_keep_view_type(self, prefilter):
        dm = self._refresh(prefilter)
        assert dm.data_type == 0
        dm.show_type.setCurrentIndex.assert_not_called()


class TestSupersededLoad:
    """A slow load finishing after the view type changed must not be shown"""

    def _two_loads(self):
        from matchypatchy.gui.display_media import DisplayMedia
        dm = _make_display_media()
        dm.mpDB.count.side_effect = lambda tbl: 5
        dm.handle_data_loaded = DisplayMedia.handle_data_loaded.__get__(dm)
        dm._apply_sort = MagicMock()
        dm._set_delegates = MagicMock()
        dm.close_alert = MagicMock()
        dm.show_alert = MagicMock()
        loaders = [MagicMock(), MagicMock()]
        with patch("matchypatchy.gui.display_media.FetchTableThread", side_effect=loaders), \
             patch("matchypatchy.gui.display_media.fetch_individual", return_value=pd.DataFrame()):
            dm.data_type = 1
            DisplayMedia.load_table(dm)
            dm.data_type = 0  # user switches to Full Images before the roi load finishes
            DisplayMedia.load_table(dm)
        return dm, loaders

    @staticmethod
    def _slot(signal):
        return signal.connect.call_args.args[0]

    def test_stale_results_are_ignored(self):
        dm, (old, new) = self._two_loads()
        self._slot(old.loaded_data)(pd.DataFrame({"id": [10]}))
        dm.media_table.receiveData.assert_not_called()
        self._slot(new.loaded_data)(pd.DataFrame({"id": [1]}))
        dm.media_table.receiveData.assert_called_once()

    def test_stale_done_keeps_progress_open(self):
        dm, (old, new) = self._two_loads()
        self._slot(old.done)()
        dm.close_alert.assert_not_called()
        self._slot(new.done)()
        dm.close_alert.assert_called_once()

    def test_previous_load_is_stopped_and_kept_until_finished(self):
        dm, (old, new) = self._two_loads()
        old.requestInterruption.assert_called_once()
        old.loaded_data.disconnect.assert_called_once()
        assert dm._loaders == [old, new]
        self._slot(old.finished)()
        assert dm._loaders == [new]


class TestSelectAllAfterReload:
    def test_reload_unchecks_select_all(self):
        """Reloaded rows are unticked, so the next Select All click selects again"""
        from matchypatchy.gui.display_media import DisplayMedia
        dm = _make_display_media()
        dm._apply_sort = MagicMock()
        dm._set_delegates = MagicMock()
        DisplayMedia.handle_data_loaded(dm, pd.DataFrame({"id": [10], "select": [0]}))
        dm.button_select.setChecked.assert_called_with(False)
