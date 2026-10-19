"""
Unit tests for matchypatchy GUI dialog classes:
  - IndividualFillPopup  (popup_individual.py)
  - IndividualPopup      (popup_individual.py)
  - AlertPopup           (popup_alert.py)

PyQt6 is stubbed out in conftest.py.  All dialog classes are instantiated
via __new__ so we can exercise their pure-Python logic without a real display.
"""
import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_individual_fill_popup(name=None, sex=None, existing_names=None):
    """
    Build an IndividualFillPopup bypassing __init__ and injecting stubs.
    """
    from matchypatchy.gui.dialogs.popup_individual import IndividualFillPopup

    parent = MagicMock()
    mpDB = MagicMock()
    mpDB.select.return_value = [(n,) for n in (existing_names or [])]
    parent.mpDB = mpDB

    popup = IndividualFillPopup.__new__(IndividualFillPopup)
    popup.mpDB = mpDB
    popup.existing_name = name
    popup.existing_sex = sex

    # Stub Qt widgets
    name_widget = MagicMock()
    name_widget.text.return_value = name or ""
    popup.name = name_widget

    sex_widget = MagicMock()
    sex_widget.currentText.return_value = sex or "Unknown"
    popup.sex = sex_widget

    secret = MagicMock()
    popup.secret_text = secret

    ok_button = MagicMock()
    popup.okButton = ok_button

    return popup


# ---------------------------------------------------------------------------
# TestIndividualFillPopupGetters
# ---------------------------------------------------------------------------

class TestIndividualFillPopupGetters:
    def test_get_name_returns_name_text(self):
        popup = _make_individual_fill_popup(name="Tiger-01")
        assert popup.get_name() == "Tiger-01"

    def test_get_name_empty(self):
        popup = _make_individual_fill_popup(name="")
        assert popup.get_name() == ""

    def test_get_sex_returns_selected(self):
        popup = _make_individual_fill_popup(sex="Female")
        assert popup.get_sex() == "Female"

    def test_get_sex_default_unknown(self):
        popup = _make_individual_fill_popup()
        assert popup.get_sex() == "Unknown"


# ---------------------------------------------------------------------------
# TestCheckExistingName
# ---------------------------------------------------------------------------

class TestCheckExistingName:
    def test_same_as_existing_name_is_ok(self):
        """Same name as the individual being edited should be allowed."""
        popup = _make_individual_fill_popup(name="Tiger-01", existing_names=["Tiger-01"])
        popup.name.text.return_value = "Tiger-01"
        assert popup.check_existing_name() is True

    def test_new_unique_name_is_ok(self):
        popup = _make_individual_fill_popup(name="Tiger-01", existing_names=["Leopard-02"])
        popup.name.text.return_value = "Tiger-01"
        assert popup.check_existing_name() is True

    def test_duplicate_name_is_rejected(self):
        """A name already used by another individual should be rejected."""
        popup = _make_individual_fill_popup(name="NewName",
                                            existing_names=["Tiger-01", "NewName"])
        popup.existing_name = "Tiger-01"  # we are editing Tiger-01
        popup.name.text.return_value = "NewName"  # trying to rename to NewName
        result = popup.check_existing_name()
        assert result is False
        popup.secret_text.show.assert_called()

    def test_unique_name_hides_secret_text(self):
        popup = _make_individual_fill_popup(name="UniqueOne",
                                            existing_names=["OtherName"])
        popup.existing_name = "OldName"
        popup.name.text.return_value = "UniqueOne"
        popup.check_existing_name()
        popup.secret_text.hide.assert_called()


# ---------------------------------------------------------------------------
# TestCheckInput
# ---------------------------------------------------------------------------

class TestCheckInput:
    def test_ok_button_enabled_when_name_present_and_unique(self):
        popup = _make_individual_fill_popup(name="Lion-03",
                                            existing_names=["Tiger-01"])
        popup.existing_name = "Lion-03"  # same name = editing mode
        popup.name.text.return_value = "Lion-03"
        popup.checkInput()
        popup.okButton.setEnabled.assert_called_with(True)

    def test_ok_button_disabled_when_name_empty(self):
        popup = _make_individual_fill_popup(name="", existing_names=[])
        popup.name.text.return_value = ""
        popup.checkInput()
        popup.okButton.setEnabled.assert_called_with(False)

    def test_ok_button_disabled_when_duplicate_name(self):
        popup = _make_individual_fill_popup(name="Taken",
                                            existing_names=["Taken"])
        popup.existing_name = "OldName"
        popup.name.text.return_value = "Taken"
        popup.checkInput()
        popup.okButton.setEnabled.assert_called_with(False)


# ---------------------------------------------------------------------------
# TestAcceptVerify
# ---------------------------------------------------------------------------

class TestAcceptVerify:
    def test_accept_called_when_name_present(self):
        popup = _make_individual_fill_popup(name="Cheetah-05")
        popup.name.text.return_value = "Cheetah-05"
        popup.accept = MagicMock()
        popup.accept_verify()
        popup.accept.assert_called_once()

    def test_accept_not_called_when_name_empty(self):
        popup = _make_individual_fill_popup(name="")
        popup.name.text.return_value = ""
        popup.accept = MagicMock()
        popup.accept_verify()
        popup.accept.assert_not_called()


# ---------------------------------------------------------------------------
# TestIndividualPopupSetEditview
# ---------------------------------------------------------------------------

class TestIndividualPopupSetEditview:
    def _make_individual_popup(self):
        from matchypatchy.gui.dialogs.popup_individual import IndividualPopup

        parent = MagicMock()
        parent.mpDB = MagicMock()
        parent.mpDB._command.return_value = []
        parent.mpDB.select.return_value = [(0,)]

        popup = IndividualPopup.__new__(IndividualPopup)
        popup.parent = parent
        popup.mpDB = parent.mpDB
        popup.selected_ind = None

        list_widget = MagicMock()
        popup.list = list_widget
        popup.button_edit = MagicMock()
        popup.button_view = MagicMock()
        popup.individuals = []
        popup.nulls = 0
        return popup

    def test_set_editview_enables_buttons_when_row_selected(self):
        popup = self._make_individual_popup()
        popup.list.currentRow.return_value = 1  # valid row
        popup.set_editview()
        popup.button_edit.setEnabled.assert_called_with(True)
        popup.button_view.setEnabled.assert_called_with(True)

    def test_set_editview_disables_buttons_when_no_row(self):
        popup = self._make_individual_popup()
        popup.list.currentRow.return_value = -1  # nothing selected
        popup.set_editview()
        popup.button_edit.setEnabled.assert_called_with(False)
        popup.button_view.setEnabled.assert_called_with(False)


# ---------------------------------------------------------------------------
# TestIndividualPopupUpdate
# ---------------------------------------------------------------------------

class TestIndividualPopupUpdate:
    def _make_individual_popup(self, individuals=None, null_count=0):
        from matchypatchy.gui.dialogs.popup_individual import IndividualPopup

        parent = MagicMock()
        parent.mpDB = MagicMock()
        parent.mpDB._command.return_value = individuals or []
        parent.mpDB.select.return_value = [(null_count,)]

        popup = IndividualPopup.__new__(IndividualPopup)
        popup.parent = parent
        popup.mpDB = parent.mpDB
        popup.selected_ind = None

        list_widget = MagicMock()
        popup.list = list_widget
        popup.button_edit = MagicMock()
        popup.button_view = MagicMock()
        return popup

    def test_update_sets_correct_row_count(self):
        """Row count = number of individuals + 1 (unidentified row)."""
        individuals = [("Tiger-01", 1, 5), ("Leopard-02", 2, 3)]
        popup = self._make_individual_popup(individuals=individuals, null_count=2)
        popup.update()
        popup.list.setRowCount.assert_called_with(3)  # 2 named + 1 unidentified

    def test_update_empty_database(self):
        """With no named individuals, only the unidentified row is added."""
        popup = self._make_individual_popup(individuals=[], null_count=10)
        popup.update()
        popup.list.setRowCount.assert_called_with(1)

    def test_update_stores_individuals(self):
        individuals = [("Tiger-01", 1, 5)]
        popup = self._make_individual_popup(individuals=individuals)
        popup.update()
        assert popup.individuals == individuals


# ---------------------------------------------------------------------------
# TestAlertPopup
# ---------------------------------------------------------------------------

class TestAlertPopup:
    def test_importable(self):
        """AlertPopup should be importable (not raise ImportError)."""
        from matchypatchy.gui.dialogs.popup_alert import AlertPopup
        assert AlertPopup is not None


# ---------------------------------------------------------------------------
# ImportCSVPopup
# ---------------------------------------------------------------------------

def _csv_popup(tmp_path):
    import pandas as pd
    from matchypatchy.gui.dialogs.popup_import_csv import ImportCSVPopup
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame({"filepath": ["a.jpg"], "timestamp": ["2024-01-01"], "station": ["S1"]}).to_csv(manifest, index=False)
    parent = MagicMock()
    parent.active_survey = (1, "Default Survey")
    # the shared widget stub runs out of side effects when built repeatedly
    with patch("matchypatchy.gui.dialogs.popup_import_csv.ComboBoxSeparator"):
        return ImportCSVPopup(parent, str(manifest))


class TestImportCSVSurvey:
    def test_defaults_to_the_active_survey_not_a_column(self, tmp_path):
        """The thread reads a non-None survey selection as a CSV column name"""
        popup = _csv_popup(tmp_path)
        assert popup.selections["survey"] is None

    def test_switching_back_to_active_survey_rechecks_ok(self, tmp_path):
        from matchypatchy.gui.dialogs.popup_import_csv import ImportCSVPopup
        popup = MagicMock()
        popup.selections = {"survey": "None"}
        popup.survey.currentIndex.return_value = 0
        ImportCSVPopup.select_survey(popup)
        assert popup.selections["survey"] is None
        popup.check_ok_button.assert_called_once()

    def test_thread_uses_active_survey_for_none_selection(self):
        """With the active survey selected, no survey named 'None' is created"""
        from matchypatchy.threads.import_thread import CSVImportThread
        thread = MagicMock()
        thread.selected_columns = {"survey": None}
        thread.active_survey = "Default Survey"
        thread.survey_ref = {}
        thread.mpDB.select.return_value = [(1,)]
        assert CSVImportThread.survey(thread, {"filepath": "a.jpg"}) == 1
        thread.mpDB.add_survey.assert_not_called()


class TestImportCSVOkButton:
    def test_ok_disabled_while_importing(self, tmp_path):
        popup = _csv_popup(tmp_path)
        popup.okButton = MagicMock()
        popup.selections.update(filepath="filepath", timestamp="timestamp", station="station")
        with patch("matchypatchy.gui.dialogs.popup_import_csv.CSVImportThread"):
            popup.import_manifest()
        popup.okButton.setEnabled.assert_called_with(False)
