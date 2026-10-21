"""
Unit tests for DisplayCompare actions (match, save, navigation guards)

DisplayCompare methods are called on a MagicMock standing in for the widget,
so no Qt display is needed. PyQt6 is stubbed out in conftest.py.
"""
from unittest.mock import MagicMock, patch

DC = "matchypatchy.gui.display_compare"


def _display():
    """MagicMock standing in for a DisplayCompare instance"""
    dc = MagicMock()
    dc.QueryContainer.both_unnamed.return_value = True
    return dc


def _fill_popup(accepted, name="Jaguar-1", sex="F"):
    popup = MagicMock()
    popup.exec.return_value = accepted
    popup.get_name.return_value = name
    popup.get_sex.return_value = sex
    return popup


class TestConfirmMatchNewIndividual:
    def test_creates_individual_with_name_and_sex(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = _display()
        dc.mpDB.add_individual.return_value = 7
        with patch(f"{DC}.IndividualFillPopup", return_value=_fill_popup(True)):
            DisplayCompare.confirm_match(dc)
        dc.mpDB.add_individual.assert_called_once_with("Jaguar-1", "F")
        dc.QueryContainer.new_iid.assert_called_once_with(7)

    def test_cancel_does_nothing(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = _display()
        with patch(f"{DC}.IndividualFillPopup", return_value=_fill_popup(False)):
            DisplayCompare.confirm_match(dc)
        dc.mpDB.add_individual.assert_not_called()
        dc.QueryContainer.new_iid.assert_not_called()

    def test_failed_insert_warns_and_assigns_nothing(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = _display()
        dc.mpDB.add_individual.return_value = None
        with patch(f"{DC}.IndividualFillPopup", return_value=_fill_popup(True)):
            DisplayCompare.confirm_match(dc)
        dc.warn.assert_called_once()
        dc.QueryContainer.new_iid.assert_not_called()


class TestSaveChanges:
    def _save(self, edits, individual_ids=None):
        from matchypatchy.gui.display_compare import DisplayCompare
        individual_ids = individual_ids or {}
        dc = MagicMock()
        dc.edit_stack = list(edits)
        dc.QueryContainer.get_info.side_effect = lambda rid, col: individual_ids.get(rid)
        DisplayCompare.save_changes(dc)
        return dc

    def _edit(self, rid, mid, reference, new_value, previous_value=None):
        from matchypatchy.database.media import EditObject
        return EditObject(rid=rid, mid=mid, reference=reference,
                          previous_value=previous_value, new_value=new_value)

    def test_roi_edit(self):
        dc = self._save([self._edit(5, 2, "viewpoint", 1)])
        dc.mpDB.edit_row.assert_called_once_with("roi", 5, {"viewpoint": 1}, allow_none=True)
        assert dc.edit_stack == []

    def test_clearing_a_value_is_allowed(self):
        """Setting a name to Unknown stores NULL"""
        dc = self._save([self._edit(5, 2, "individual_id", None)])
        dc.mpDB.edit_row.assert_called_once_with("roi", 5, {"individual_id": None}, allow_none=True)

    def test_comment_goes_to_media_by_media_id(self):
        dc = self._save([self._edit(None, 2, "comment", "hi")])
        dc.mpDB.edit_row.assert_called_once_with("media", 2, {"comment": "hi"}, allow_none=True)

    def test_edits_applied_oldest_first(self):
        dc = self._save([self._edit(5, 2, "viewpoint", 0), self._edit(5, 2, "viewpoint", 1)])
        values = [c.args[2]["viewpoint"] for c in dc.mpDB.edit_row.call_args_list]
        assert values == [0, 1]

    def test_sex_edits_the_rois_individual(self):
        dc = self._save([self._edit(5, 2, "sex", "M")], individual_ids={5: 3.0})
        dc.mpDB.edit_row.assert_called_once_with("individual", 3, {"sex": "M"}, allow_none=True)

    def test_sex_follows_a_name_change_in_the_same_edit(self):
        dc = self._save([self._edit(5, 2, "individual_id", 8), self._edit(5, 2, "sex", "M")],
                        individual_ids={5: 3.0})
        assert dc.mpDB.edit_row.call_args_list[-1].args == ("individual", 8, {"sex": "M"})

    def test_sex_without_individual_is_skipped(self):
        dc = self._save([self._edit(5, 2, "sex", "M")], individual_ids={5: None})
        dc.mpDB.edit_row.assert_not_called()

    def test_row_without_roi_id_is_skipped(self):
        import pandas as pd
        dc = self._save([self._edit(pd.NA, 2, "viewpoint", 1)])
        dc.mpDB.edit_row.assert_not_called()


class TestChangeQueryFavorites:
    def _change(self, compare_type, favorites_on):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = MagicMock()
        dc.compare_type = compare_type
        dc.button_match_favorites.isChecked.return_value = favorites_on
        DisplayCompare.change_query(dc, 1)
        return dc

    def test_favorites_reapplied_for_new_query(self):
        dc = self._change("default", True)
        dc.QueryContainer.set_query.assert_called_once_with(1)
        dc.QueryContainer.set_match_favorites.assert_called_once_with(True)

    def test_favorites_off(self):
        dc = self._change("default", False)
        dc.QueryContainer.set_match_favorites.assert_not_called()

    def test_not_in_qc_mode(self):
        dc = self._change("qc", True)
        dc.QueryContainer.set_match_favorites.assert_not_called()


class TestRefreshKeepsFilter:
    def test_favorite_refreshes_without_dropping_filter(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = MagicMock()
        dc.compare_type = "default"
        dc.button_match_favorites.isChecked.return_value = False
        DisplayCompare.favorite(dc, 5, 1)
        dc.mpDB.edit_row.assert_called_once_with("roi", 5, {"favorite": 1})
        dc.QueryContainer.refresh_data.assert_called_once()
        dc.QueryContainer.filter.assert_not_called()

    def test_favorite_rebuilds_favorites_when_showing(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = MagicMock()
        dc.compare_type = "default"
        dc.button_match_favorites.isChecked.return_value = True
        DisplayCompare.favorite(dc, 5, 1)
        dc.QueryContainer.set_match_favorites.assert_called_once_with(True)


class TestNoQueryGuards:
    """With nothing to compare, navigation and actions do nothing instead of crashing"""

    def _empty(self):
        dc = MagicMock()
        dc.QueryContainer.n_queries = 0
        dc.QueryContainer.current_query_rois = []
        return dc

    def test_has_query(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = self._empty()
        assert DisplayCompare.has_query(dc) is False
        dc.QueryContainer.n_queries = 2
        dc.QueryContainer.current_query_rois = [10]
        assert DisplayCompare.has_query(dc) is True
        dc.QueryContainer = None
        assert DisplayCompare.has_query(dc) is False

    def test_actions_are_noops_without_query(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = self._empty()
        dc.has_query.return_value = False
        DisplayCompare.change_query(dc, 1)
        DisplayCompare.change_match(dc, 1)
        DisplayCompare.change_query_in_sequence(dc, 1)
        DisplayCompare.toggle_viewpoint(dc, 0)
        DisplayCompare.press_match_button(dc)
        DisplayCompare.confirm_match(dc)
        DisplayCompare.unmatch(dc)
        DisplayCompare.press_favorite_button(dc, 10)
        DisplayCompare.edit_image(dc, 10)
        DisplayCompare.open_image(dc, 10)
        dc.QueryContainer.set_query.assert_not_called()
        dc.QueryContainer.set_match.assert_not_called()
        dc.QueryContainer.get_info.assert_not_called()
        dc.mpDB.edit_row.assert_not_called()
        assert dc.current_viewpoint == 0

    def test_unmatch_requires_existing_match(self):
        """U key: don't clear the query's individual when query and match differ"""
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = MagicMock()
        dc.has_query.return_value = True
        dc.QueryContainer.is_existing_match.return_value = False
        with patch(f"{DC}.AlertPopup") as popup:
            DisplayCompare.unmatch(dc)
        popup.assert_not_called()
        dc.QueryContainer.unmatch.assert_not_called()

    def test_failed_match_thread_shows_result_in_progress_popup(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = MagicMock()
        dc._cancelled = False
        dc.QueryContainer.filter_matched = False
        DisplayCompare.check_matchthread_success(dc, False)
        dc.notify.assert_called_once_with("No matches found within filter.")
        dc.close_progress.assert_not_called()
        dc.change_query.assert_not_called()

    def test_successful_match_thread_closes_progress(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = MagicMock()
        dc._cancelled = False
        DisplayCompare.check_matchthread_success(dc, True)
        dc.close_progress.assert_called_once()
        dc.change_query.assert_called_once_with(0)


class TestNotify:
    def test_replaces_text_of_open_progress_popup(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = MagicMock()
        DisplayCompare.notify(dc, "No matches found within filter.")
        dc.alert_box.update_prompt.assert_called_once_with("No matches found within filter.")
        dc.alert_box.show.assert_called_once()
        dc.warn.assert_not_called()

    def test_dismissing_the_popup_clears_it(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = MagicMock()
        DisplayCompare.notify(dc, "msg")
        on_finished = dc.alert_box.finished.connect.call_args.args[0]
        on_finished(1)
        dc.close_progress.assert_called_once()

    def test_single_alert_without_progress_popup(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = MagicMock()
        dc.alert_box = None
        DisplayCompare.notify(dc, "msg")
        dc.warn.assert_called_once_with(prompt="msg")


class TestModeSwitching:
    def test_teardown_handles_qc_and_manual_containers(self):
        """QC/manual containers have no thread signals or stop_calculation"""
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = MagicMock()
        dc.QueryContainer = MagicMock(spec=["deleteLater"])
        DisplayCompare._teardown_query_container(dc)
        assert dc.QueryContainer is None

    def test_entering_qc_tears_down_previous_container(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = MagicMock()
        with patch(f"{DC}.fetch_individual") as fetch, patch(f"{DC}.QC_QueryContainer"):
            fetch.return_value.empty = False
            DisplayCompare.compare_by_individual(dc)
        dc._teardown_query_container.assert_called_once()

    def test_manual_apply_filters_keeps_selection(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = MagicMock()
        dc.compare_type = "manual"
        dc.QueryContainer.selected_ids = [10, 11]
        DisplayCompare.filter_neighbors(dc)
        dc.compare_manual.assert_called_once_with(selected_ids=[10, 11])

    def test_manual_filter_removing_everything_warns(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = MagicMock()
        with patch(f"{DC}.ManualQueryContainer") as cls:
            cls.return_value.load_data.return_value = True
            cls.return_value.filter.return_value = False
            DisplayCompare.compare_manual(dc, selected_ids=[10, 11])
        dc.change_query.assert_not_called()
        dc.notify.assert_called_once()


class TestMatchCounter:
    def _dc(self, n_matches, current_match_after_toggle):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = MagicMock()
        dc.compare_type = "qc"
        dc.button_match_favorites.isChecked.return_value = False
        dc.QueryContainer.n_queries = 2
        dc.QueryContainer.current_match = 0
        dc.QueryContainer.current_match_rois = list(range(5))

        def toggle(viewpoint):
            # viewpoint filter shrinks the match list and moves current_match
            dc.QueryContainer.current_match_rois = list(range(n_matches))
            dc.QueryContainer.current_match = current_match_after_toggle
            return True
        dc.QueryContainer.toggle_viewpoint.side_effect = toggle
        dc.toggle_viewpoint = lambda v: DisplayCompare.toggle_viewpoint(dc, v)
        return dc

    def test_counter_follows_current_match_after_change_query(self):
        """QC/manual start at match index 1, so the counter must show 2/N"""
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = self._dc(n_matches=5, current_match_after_toggle=1)
        DisplayCompare.change_query(dc, 0)
        dc.match_counter.setText.assert_called_with("2/5")

    def test_counter_uses_filtered_total_after_viewpoint_toggle(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = self._dc(n_matches=3, current_match_after_toggle=0)
        DisplayCompare.toggle_viewpoint(dc, 0)
        dc.match_counter.setText.assert_called_with("1/3")


class TestProjectChanged:
    def test_new_query_container_uses_the_new_project(self):
        """A match after switching projects must not write through the old project's database"""
        from types import SimpleNamespace
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = DisplayCompare.__new__(DisplayCompare)
        dc.logger = MagicMock()
        dc.distance_metric, dc.k, dc.threshold = "cosine", 3, 50
        old_db, new_db = MagicMock(), MagicMock()
        dc.project = SimpleNamespace(db=old_db, cfg=MagicMock(DB_DIR="/old"))
        with patch(f"{DC}.QueryContainer") as container:
            container.side_effect = lambda parent: SimpleNamespace(mpDB=parent.mpDB)
            dc.QueryContainer = container(dc)
            dc._teardown_query_container = MagicMock()

            dc.project.db, dc.project.cfg = new_db, MagicMock(DB_DIR="/new")
            dc.drop_queries()

        dc._teardown_query_container.assert_called_once()
        assert dc.QueryContainer.mpDB is new_db
