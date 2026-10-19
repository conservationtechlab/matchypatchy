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
