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

    def test_failed_match_thread_warns(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = MagicMock()
        dc._cancelled = False
        dc.QueryContainer.filter_matched = False
        DisplayCompare.check_matchthread_success(dc, False)
        dc.warn.assert_called_once_with(prompt="No matches found within filter.")
        dc.change_query.assert_not_called()
