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


# ---------------------------------------------------------------------------
# ImportFolderPopup / FolderImportThread
# ---------------------------------------------------------------------------

FOLDER = "matchypatchy.gui.dialogs.popup_import_folder"


class TestImportFolderTimezone:
    def _timezone(self, select_results):
        from matchypatchy.gui.dialogs.popup_import_folder import ImportFolderPopup
        popup = MagicMock()
        popup.mpDB.select.side_effect = select_results
        return ImportFolderPopup._survey_timezone(popup, 5)

    def test_survey_without_region_uses_local_time(self):
        assert self._timezone([[(None,)]]) is None

    def test_region_timezone(self):
        assert self._timezone([[(2,)], [("America/Los_Angeles",)]]) == "America/Los_Angeles"


class TestImportFolderCancel:
    def test_cancel_during_import_stops_it_and_waits(self):
        from matchypatchy.gui.dialogs.popup_import_folder import ImportFolderPopup
        popup = MagicMock()
        popup.import_thread.isRunning.return_value = True
        ImportFolderPopup.reject(popup)
        popup.import_thread.requestInterruption.assert_called_once()

    def test_manifest_after_cancel_is_ignored(self):
        from matchypatchy.gui.dialogs.popup_import_folder import ImportFolderPopup
        import pandas as pd
        popup = MagicMock()
        popup._closed = True
        ImportFolderPopup.get_manifest(popup, pd.DataFrame({"filepath": ["a.jpg"]}))
        popup.get_options.assert_not_called()

    def test_no_images_flags_for_another_directory(self):
        from matchypatchy.gui.dialogs.popup_import_folder import ImportFolderPopup
        import pandas as pd
        popup = MagicMock()
        popup._closed = False
        popup.no_images = False
        with patch(f"{FOLDER}.AlertPopup"):
            ImportFolderPopup.get_manifest(popup, pd.DataFrame())
        assert popup.no_images is True
        popup.reject.assert_called_once()

    def _import_folder(self, no_images):
        from matchypatchy.gui.display_base import DisplayBase
        base = MagicMock()
        base.select_survey.return_value = True
        with patch("matchypatchy.gui.display_base.QFileDialog.getExistingDirectory", return_value="/data"), \
                patch("matchypatchy.gui.display_base.ImportFolderPopup") as popup_cls:
            popup_cls.return_value.no_images = no_images
            DisplayBase.import_folder(base)
        return base

    def test_user_cancel_does_not_reopen_picker(self):
        base = self._import_folder(no_images=False)
        base.import_folder.assert_not_called()

    def test_no_images_reopens_picker(self):
        base = self._import_folder(no_images=True)
        base.import_folder.assert_called_once()


class TestFolderImportCamera:
    def test_camera_level_without_station_level(self, tmp_path):
        """Camera under the default station instead of UnboundLocalError"""
        import pandas as pd
        from matchypatchy.threads.import_thread import FolderImportThread
        image = tmp_path / "cam1" / "a.jpg"
        image.parent.mkdir()
        image.write_bytes(b"x")
        thread = MagicMock()
        thread.data = pd.DataFrame({"filepath": [str(image)], "datetime": ["2024-01-01 10:00:00"]})
        thread.station_level, thread.camera_level = 0, 2
        thread.default_station = None
        thread.PROGRESS_BATCH_SIZE = FolderImportThread.PROGRESS_BATCH_SIZE
        thread.active_survey = (1, "S")
        thread.isInterruptionRequested.return_value = False
        thread.mpDB.select.return_value = [(1,)]
        thread.mpDB.add_station.return_value = 3
        thread.camera.return_value = 7
        with patch("matchypatchy.threads.import_thread.get_sha256", return_value="h"), \
                patch("matchypatchy.threads.import_thread.save_media_thumbnail", return_value="t.jpg"):
            FolderImportThread.run(thread)
        # run() reports exceptions instead of raising them
        thread.import_failed.emit.assert_not_called()
        thread.camera.assert_called_once_with(str(image), 3)
        assert thread.mpDB.add_media.call_args.kwargs["camera_id"] == 7


# ---------------------------------------------------------------------------
# UploadManagerPopup
# ---------------------------------------------------------------------------

UPLOADS = "matchypatchy.gui.dialogs.popup_uploads"


def _uploads_popup(updates=(), errors=(), verified=True, contains_errors=False):
    popup = MagicMock()
    popup.updates = list(updates)
    popup.errors = list(errors)
    popup.verified = verified
    popup.contains_errors = contains_errors
    return popup


class TestUploadManagerList:
    def test_uploads_without_media_are_listed(self, tmp_db):
        """Grouping on the media side folded every empty upload into one row"""
        from matchypatchy.gui.dialogs.popup_uploads import UploadManagerPopup
        db, _ = tmp_db
        station = db.add_station("S", None, None, 1)
        a, b, c = db.add_upload("/a"), db.add_upload("/b"), db.add_upload("/c")
        db.add_media(a, "x.jpg", "h1", ".jpg", "2024", station)
        popup = MagicMock()
        popup.mpDB = db
        UploadManagerPopup.update(popup)
        assert sorted((row[1], row[3]) for row in popup.base_dirs) == [("/a", 1), ("/b", 0), ("/c", 0)]


class TestUploadManagerSave:
    def _save(self, popup, confirm):
        from matchypatchy.gui.dialogs.popup_uploads import UploadManagerPopup
        with patch(f"{UPLOADS}.AlertPopup") as alert:
            alert.return_value.exec.return_value = confirm
            UploadManagerPopup.save(popup)

    def test_cancel_on_unverified_warning_saves_nothing(self):
        popup = _uploads_popup(updates=[(1, "/new")], verified=False)
        self._save(popup, confirm=0)
        popup.mpDB.update_base_dir.assert_not_called()

    def test_cancel_on_missing_files_warning_saves_nothing(self):
        popup = _uploads_popup(updates=[(1, "/new")], errors=[["a.jpg"]], contains_errors=True)
        self._save(popup, confirm=0)
        popup.mpDB.update_base_dir.assert_not_called()

    def test_save_without_verify(self):
        popup = _uploads_popup(updates=[(1, "/new")], verified=False)
        self._save(popup, confirm=1)
        popup.mpDB.update_base_dir.assert_called_once_with(1, "/new")
        assert popup.updates == []

    def _status(self, popup):
        return popup.status_label.setText.call_args.args[0]

    def test_failed_update_is_reported(self):
        """update_base_dir returning False (e.g. directory already another upload's) was ignored"""
        popup = _uploads_popup(updates=[(1, "/taken"), (2, "/ok")], errors=[[], []])
        popup.mpDB.update_base_dir.side_effect = lambda base_dir_id, _: base_dir_id != 1
        popup.base_dirs = [(1, "/old1", "2024", 1), (2, "/ok", "2024", 1)]
        self._save(popup, confirm=1)
        text = self._status(popup)
        assert "Saved 1 of 2" in text
        assert "/taken" in text and "/ok" not in text
        popup.list.item.assert_any_call(0, 0)

    def test_skipped_update_is_reported(self):
        popup = _uploads_popup(updates=[(1, "/new")], errors=[["a.jpg", "b.jpg"]], contains_errors=True)
        popup.base_dirs = [(1, "/old", "2024", 2)]
        self._save(popup, confirm=1)
        popup.mpDB.update_base_dir.assert_not_called()
        text = self._status(popup)
        assert "Saved 0 of 1" in text
        assert "/new (2 files missing)" in text

    def test_choosing_another_directory_needs_verifying_again(self):
        from matchypatchy.gui.dialogs.popup_uploads import UploadManagerPopup
        popup = _uploads_popup(verified=True)
        popup.base_dirs = [(1, "/old", "2024", 0)]
        popup.list.currentRow.return_value = 0
        with patch(f"{UPLOADS}.QFileDialog.getExistingDirectory", return_value="/new"):
            UploadManagerPopup.edit(popup)
        assert popup.verified is False


class TestUploadManagerVerify:
    def _popup(self, updates=((1, "/new"),)):
        from matchypatchy.gui.dialogs.popup_uploads import UploadManagerPopup
        popup = _uploads_popup(updates=updates, verified=False)
        popup.verifying = False
        popup.build_thread = None
        popup.list.currentRow.return_value = 0
        popup.set_verifying = lambda v: UploadManagerPopup.set_verifying(popup, v)
        popup.set_editdel = lambda: UploadManagerPopup.set_editdel(popup)
        return popup

    def _verify(self, popup):
        from matchypatchy.gui.dialogs.popup_uploads import UploadManagerPopup
        with patch(f"{UPLOADS}.VerifyNewBaseDirsThread") as thread:
            UploadManagerPopup.verify(popup)
        return thread

    def test_verify_while_running_is_ignored(self):
        """Replacing a running thread aborted the app"""
        popup = self._popup()
        thread = self._verify(popup)
        running = popup.build_thread
        running.isRunning.return_value = True
        thread = self._verify(popup)
        thread.assert_not_called()
        assert popup.build_thread is running

    def test_buttons_disabled_and_progress_shown_while_verifying(self):
        popup = self._popup()
        self._verify(popup)
        popup.button_verify.setEnabled.assert_called_with(False)
        popup.button_save.setEnabled.assert_called_with(False)
        popup.button_edit.setEnabled.assert_called_with(False)
        popup.progress_bar.show.assert_called_once()

    def test_buttons_enabled_when_verification_finishes(self):
        from matchypatchy.gui.dialogs.popup_uploads import UploadManagerPopup
        popup = self._popup()
        self._verify(popup)
        UploadManagerPopup.on_verify_finished(popup)
        popup.button_verify.setEnabled.assert_called_with(True)
        popup.button_save.setEnabled.assert_called_with(True)
        popup.button_edit.setEnabled.assert_called_with(True)
        popup.progress_bar.hide.assert_called()

    def test_thread_gets_a_copy_of_updates(self):
        popup = self._popup()
        thread = self._verify(popup)
        passed = thread.call_args.args[1]
        assert passed == [(1, "/new")]
        assert passed is not popup.updates


class TestUploadManagerLog:
    def _log(self, popup):
        from matchypatchy.gui.dialogs.popup_uploads import UploadManagerPopup
        with patch(f"{UPLOADS}.AlertPopup") as alert:
            UploadManagerPopup.log(popup)
        return alert

    def test_missing_files_reported_in_popup_label(self):
        popup = _uploads_popup(updates=[(1, "/new")], errors=[["a.jpg", "b.jpg"]], contains_errors=True)
        alert = self._log(popup)
        alert.assert_not_called()
        text = popup.status_label.setText.call_args.args[0]
        assert "2 files" in text

    def test_all_found_reported_in_popup_label(self):
        popup = _uploads_popup(updates=[(1, "/new")], errors=[[]])
        alert = self._log(popup)
        alert.assert_not_called()
        assert "All files were found" in popup.status_label.setText.call_args.args[0]


class TestIndividualPopupList:
    def test_individuals_without_rois_are_listed(self, tmp_db):
        """Grouping on the roi side folded every individual without rois into one row"""
        from matchypatchy.gui.dialogs.popup_individual import IndividualPopup
        db, _ = tmp_db
        station = db.add_station("S", None, None, 1)
        up = db.add_upload("/a")
        mid = db.add_media(up, "x.jpg", "h1", ".jpg", "2024", station)
        a, b, c = db.add_individual("A"), db.add_individual("B"), db.add_individual("C")
        db.add_roi(mid, 0, 0.1, 0.1, 0.1, 0.1, individual_id=a)
        popup = MagicMock()
        popup.mpDB = db
        IndividualPopup.update(popup)
        assert sorted((name, count) for name, _, count in popup.individuals) == [("A", 1), ("B", 0), ("C", 0)]


class TestViewIndividualPrefilter:
    """Manage Individuals > View sends the individual's database id"""

    def _refresh(self, individual_id):
        from matchypatchy.gui.widgets.widget_filterbar import FilterBar
        bar = MagicMock()
        tables = {"region": [], "survey": [], "individual": [(4, "Spot"), (9, "Dot")]}
        bar.mpDB.select.side_effect = lambda table, columns=None, row_cond=None: tables.get(table, [])
        bar.region_select.currentIndex.return_value = 0
        bar.survey_select.currentIndex.return_value = 0
        bar.station_select.currentIndex.return_value = 0
        bar.viewpoint_select.currentIndex.return_value = 0
        bar.individual_select.currentIndex.return_value = 0
        bar.station_list_ordered = [(0, "Station")]
        bar.viewpoint_list_ordered = [(0, "Viewpoint")]
        FilterBar.refresh_filters(bar, prefilter={"individual_id": individual_id})
        return bar

    def test_selects_individual_by_id(self):
        bar = self._refresh(9)
        assert bar.filters["active_individual"] == (9, "Dot")
        bar.individual_select.setCurrentIndex.assert_called_with(2)

    def test_unidentified_row_filters_unidentified(self):
        bar = self._refresh(0)
        assert bar.unidentified_only is True
        bar.unidentified.setChecked.assert_called_with(True)


# ---------------------------------------------------------------------------
# FilterBar survey / region station lists
# ---------------------------------------------------------------------------

class TestFilterBarStations:
    def _bar(self):
        bar = MagicMock()
        bar.mpDB.select.return_value = [(1, "S1"), (2, "S2")]
        return bar

    def test_survey_placeholder_without_region_shows_all_stations(self):
        from matchypatchy.gui.widgets.widget_filterbar import FilterBar
        bar = self._bar()
        bar.survey_list_ordered = [(0, "Survey"), (5, "A")]
        bar.survey_select.currentIndex.return_value = 0
        bar.region_select.currentIndex.return_value = 0
        FilterBar.select_survey(bar)
        bar.filter_stations.assert_called_once_with()

    def test_survey_placeholder_with_region_shows_region_stations(self):
        from matchypatchy.gui.widgets.widget_filterbar import FilterBar
        bar = self._bar()
        bar.survey_list_ordered = [(0, "Survey"), (5, "A")]
        bar.valid_surveys = {5: "A", 6: "B"}
        bar.survey_select.currentIndex.return_value = 0
        bar.region_select.currentIndex.return_value = 1
        FilterBar.select_survey(bar)
        bar.filter_stations.assert_called_once_with(survey_ids=[(5, "A"), (6, "B")])

    def test_region_without_surveys_has_no_stations(self):
        from matchypatchy.gui.widgets.widget_filterbar import FilterBar
        bar = self._bar()
        FilterBar.filter_stations(bar, survey_ids=[])
        assert bar.valid_stations == {}

    def test_no_survey_filter_has_all_stations(self):
        from matchypatchy.gui.widgets.widget_filterbar import FilterBar
        bar = self._bar()
        FilterBar.filter_stations(bar)
        assert bar.valid_stations == {1: "S1", 2: "S2"}


class TestThresholdInput:
    @pytest.mark.parametrize("text", ["", ".", "-", "abc"])
    def test_partial_input_is_ignored(self, text):
        from matchypatchy.gui.widgets.gui_assets import SliderWithLabel
        slider = MagicMock()
        SliderWithLabel.value_edit_changed(slider, text)
        slider.slider_value_changed.emit.assert_not_called()

    def test_value_sets_slider_once(self):
        from matchypatchy.gui.widgets.gui_assets import SliderWithLabel
        slider = MagicMock()
        SliderWithLabel.value_edit_changed(slider, "0.35")
        slider.slider.setValue.assert_called_once_with(35)
        slider.slider_value_changed.emit.assert_called_once_with(35)


# ---------------------------------------------------------------------------
# SurveyPopup
# ---------------------------------------------------------------------------

SURVEY = "matchypatchy.gui.dialogs.popup_survey"


def _survey_popup(db):
    from matchypatchy.gui.dialogs.popup_survey import SurveyPopup
    popup = MagicMock()
    popup.mpDB = db
    popup._year = SurveyPopup._year
    popup._region_id = lambda name, tz: SurveyPopup._region_id(popup, name, tz)
    return popup


def _fill(name, region, start="", end=""):
    fill = MagicMock()
    fill.exec.return_value = True
    fill.get_name.return_value = name
    fill.get_region.return_value = region
    fill.get_timezone.return_value = "UTC"
    fill.get_year_start.return_value = start
    fill.get_year_end.return_value = end
    return fill


class TestSurveyPopup:
    def _add(self, db, name, region, **years):
        from matchypatchy.gui.dialogs.popup_survey import SurveyPopup
        popup = _survey_popup(db)
        with patch(f"{SURVEY}.SurveyFillPopup", return_value=_fill(name, region, **years)):
            SurveyPopup.add(popup)
        return popup

    def test_region_name_with_quote_is_reused(self, tmp_db):
        db, _ = tmp_db
        self._add(db, "A", "O'Brien")
        popup = self._add(db, "B", "O'Brien")
        regions = {r for (r,) in db.select("survey", "region_id", "name IN ('A', 'B')")}
        assert len(regions) == 1 and None not in regions
        popup._warn.assert_not_called()

    def test_duplicate_survey_name_warns(self, tmp_db):
        db, _ = tmp_db
        self._add(db, "A", "R")
        popup = self._add(db, "A", "R")
        popup._warn.assert_called_once()

    def test_empty_years_are_null(self, tmp_db):
        db, _ = tmp_db
        self._add(db, "A", "R", start="2020", end="")
        assert db.select("survey", "year_start, year_end", "name='A'") == [(2020, None)]

    def test_edit_survey_without_region(self, tmp_db):
        from matchypatchy.gui.dialogs.popup_survey import SurveyPopup
        db, _ = tmp_db
        sid = db.add_survey("No Region", None, None, None)
        popup = _survey_popup(db)
        popup.survey_list_ordered = [(sid, "No Region")]
        popup.list.currentRow.return_value = 0
        with patch(f"{SURVEY}.SurveyFillPopup", return_value=_fill("No Region", "R")) as fill_cls:
            SurveyPopup.edit(popup)
        assert fill_cls.call_args.kwargs["region_name"] == ""
        assert db.select("survey", "region_id", f"id={sid}")[0][0] is not None

    def test_rename_to_existing_name_warns(self, tmp_db):
        from matchypatchy.gui.dialogs.popup_survey import SurveyPopup
        db, _ = tmp_db
        sid = db.add_survey("A", 1, None, None)
        db.add_survey("B", 1, None, None)
        popup = _survey_popup(db)
        popup.survey_list_ordered = [(sid, "A")]
        popup.list.currentRow.return_value = 0
        with patch(f"{SURVEY}.SurveyFillPopup", return_value=_fill("B", "Default Region")):
            SurveyPopup.edit(popup)
        popup._warn.assert_called_once()


# ---------------------------------------------------------------------------
# StationPopup / StationFillPopup
# ---------------------------------------------------------------------------

STATION = "matchypatchy.gui.dialogs.popup_station"


def _station_fill(name="S1", lat="", long=""):
    from matchypatchy.gui.dialogs.popup_station import StationFillPopup
    fill = MagicMock()
    fill.name.text.return_value = name
    fill.lat.text.return_value = lat
    fill.long.text.return_value = long
    fill.get_name = lambda: name
    fill._coordinate = StationFillPopup._coordinate
    fill._valid = lambda: StationFillPopup._valid(fill)
    return fill


class TestStationCoordinates:
    def test_empty_coordinates_are_none(self):
        from matchypatchy.gui.dialogs.popup_station import StationFillPopup
        fill = _station_fill()
        assert StationFillPopup.get_lat(fill) is None
        assert StationFillPopup.get_long(fill) is None

    def test_coordinates_are_floats(self):
        from matchypatchy.gui.dialogs.popup_station import StationFillPopup
        fill = _station_fill(lat="32.7", long="-117.1")
        assert StationFillPopup.get_lat(fill) == 32.7
        assert StationFillPopup.get_long(fill) == -117.1

    @pytest.mark.parametrize("lat,long,ok", [("", "", True), ("32.7", "-117.1", True),
                                             ("abc", "", False), ("95", "", False), ("", "-181", False)])
    def test_ok_button(self, lat, long, ok):
        from matchypatchy.gui.dialogs.popup_station import StationFillPopup
        fill = _station_fill(lat=lat, long=long)
        StationFillPopup.checkInput(fill)
        fill.okButton.setEnabled.assert_called_once_with(ok)

    def test_missing_coordinates_shown_empty_not_none(self):
        """Folder import creates stations without coordinates; they were shown (and saved) as 'None'"""
        from matchypatchy.gui.dialogs.popup_station import StationFillPopup
        parent = MagicMock()
        parent.survey_id = (1, "Survey")
        with patch(f"{STATION}.QLineEdit") as line_edit:
            StationFillPopup(parent, name="S", lat=None, long=None)
        texts = [c.args[0] for c in line_edit.return_value.setText.call_args_list]
        assert texts == ["S", "", ""]


class TestStationPopup:
    def test_failed_add_warns(self):
        from matchypatchy.gui.dialogs.popup_station import StationPopup
        popup = MagicMock()
        popup.survey_id = (1, "Survey")
        popup.mpDB.add_station.return_value = None
        with patch(f"{STATION}.StationFillPopup") as fill_cls:
            fill_cls.return_value.exec.return_value = True
            StationPopup.add(popup)
        popup._warn.assert_called_once()


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

class TestExport:
    def test_export_can_be_migrated_back(self, tmp_db, tmp_path):
        """The CSV has exactly the migrate columns (no index column) and UTF-8 names"""
        import pandas as pd
        from matchypatchy.gui.display_base import DisplayBase
        from matchypatchy.threads.import_thread import CSVMigrateThread
        from matchypatchy.gui.dialogs.popup_import_csv import ImportCSVPopup
        db, _ = tmp_db
        station = db.add_station("Estación Ñ", 1.0, 2.0, 1)
        mid = db.add_media(db.add_upload("/a"), "x.jpg", "h1", ".jpg", "2024-01-01 10:00:00", station)
        db.add_roi(mid, 0, 0.1, 0.1, 0.1, 0.1)
        base = MagicMock()
        base.mpDB = db
        out = tmp_path / "export"
        with patch("matchypatchy.gui.display_base.QFileDialog.getSaveFileName", return_value=(str(out), "")):
            DisplayBase.export(base)
        data = pd.read_csv(f"{out}.csv")
        assert set(data.columns) == ImportCSVPopup.EXPECTED_COLUMNS == CSVMigrateThread.EXPECTED_COLUMNS
        assert data.loc[0, "station_name"] == "Estación Ñ"


# ---------------------------------------------------------------------------
# ConfigPopup
# ---------------------------------------------------------------------------

class TestConfigRefresh:
    def test_shows_every_value_of_the_new_project(self, tmp_path):
        """After switching project, video/device fields and the models folder came from the old one"""
        from matchypatchy.gui.dialogs.popup_config import ConfigPopup
        popup = MagicMock()
        popup.DEVICE_OPTIONS = ConfigPopup.DEVICE_OPTIONS
        popup.cfg.ML_DIR = tmp_path / "new" / "Models"
        popup.cfg.SMART_FRAMES = False
        popup.cfg.VIDEO_FPS = 5
        popup.cfg.N_FRAMES = 7
        popup.cfg.DEVICE = "CUDAExecutionProvider"
        with patch("matchypatchy.gui.dialogs.popup_config.get_path", return_value=None) as get_path:
            ConfigPopup.refresh(popup)
        assert popup.ml_dir == tmp_path / "new" / "Models"
        get_path.assert_called_once_with(tmp_path / "new" / "Models", popup.cfg.REID_KEY)
        popup.smart_frames.setCurrentIndex.assert_called_once_with(1)
        popup.video_fps.setText.assert_called_once_with("5")
        popup.n_frames.setText.assert_called_once_with("7")
        popup.device.setCurrentText.assert_called_once_with("CUDA-enabled GPU")
        # filling the fields doesn't re-save the config through their handlers
        popup.video_fps.blockSignals.assert_any_call(True)


# ---------------------------------------------------------------------------
# Processing steps (DisplayBase)
# ---------------------------------------------------------------------------

class TestProcessingSteps:
    def test_cancel_stops_later_steps(self):
        """QThread.start() clears an earlier interruption request, so later steps check a flag"""
        from matchypatchy.gui.display_base import DisplayBase
        base = MagicMock()
        DisplayBase._cancel_processing(base)
        assert base._process_cancelled is True
        base.animl_thread.requestInterruption.assert_called_once()
        DisplayBase._start_animl(base)
        DisplayBase._start_reid(base)
        base.animl_thread.start.assert_not_called()
        base.miew_thread.start.assert_not_called()

    def test_steps_start_in_turn(self):
        from matchypatchy.gui.display_base import DisplayBase
        base = MagicMock()
        base._process_cancelled = False
        DisplayBase._start_animl(base)
        base.animl_thread.start.assert_called_once()
        DisplayBase._start_reid(base)
        base.miew_thread.start.assert_called_once()

    def test_model_not_downloaded_stops_before_processing(self):
        from matchypatchy.gui.display_base import DisplayBase
        base = MagicMock()
        mloptions = {"sequence_checked": True, "DETECTOR_KEY": "md", "REID_KEY": "miew", "VIEWPOINT_KEY": None}
        with patch("matchypatchy.gui.display_base.get_path", side_effect=lambda _d, key: None if key == "md" else "/m"), \
             patch("matchypatchy.gui.display_base.AlertPopup") as popup, \
             patch("matchypatchy.gui.display_base.SequenceThread") as sequence_thread:
            DisplayBase.process_images(base, mloptions)
        assert popup.call_args[0][1] == "Model(s) not downloaded: md"
        sequence_thread.assert_not_called()

    def test_popup_closes_when_every_file_was_read(self):
        from matchypatchy.gui.display_base import DisplayBase
        base = MagicMock()
        base.animl_thread.failed = set()
        base.miew_thread.failed = set()
        DisplayBase._finish_processing(base)
        base._process_dialog.accept.assert_called_once()

    def test_popup_stays_open_to_report_unreadable_files(self):
        from matchypatchy.gui.display_base import DisplayBase
        base = MagicMock()
        base.animl_thread.failed = {"/a.jpg"}
        base.miew_thread.failed = {"/b.jpg"}
        DisplayBase._finish_processing(base)
        base._process_dialog.accept.assert_not_called()
        assert "2 file(s)" in base._process_dialog.update_prompt.call_args[0][0]


class TestConfigSaveCancel:
    def _popup(self):
        from types import SimpleNamespace
        from matchypatchy.gui.dialogs.popup_config import ConfigPopup
        # a real instance (accept/reject call super()), without building the widgets
        popup = ConfigPopup.__new__(ConfigPopup)
        popup.logger = MagicMock()
        popup.nummatches = MagicMock()
        popup.cfg = SimpleNamespace(**{name: f"old-{name}" for name in ConfigPopup.SETTINGS}, save=MagicMock())
        popup._original = popup._settings()
        return popup

    def test_editing_doesnt_save(self):
        from matchypatchy.gui.dialogs.popup_config import ConfigPopup
        popup = self._popup()
        popup.nummatches.text.return_value = "7"
        ConfigPopup.update_nummatches(popup)
        assert popup.cfg.KNN == 7
        popup.cfg.save.assert_not_called()

    def test_cancel_restores_settings(self):
        from matchypatchy.gui.dialogs.popup_config import ConfigPopup
        popup = self._popup()
        popup.cfg.KNN = 7
        popup.cfg.DEVICE = "CUDAExecutionProvider"
        with patch("matchypatchy.gui.dialogs.popup_config.QDialog.reject", create=True):
            ConfigPopup.reject(popup)
        assert popup.cfg.KNN == "old-KNN"
        assert popup.cfg.DEVICE == "old-DEVICE"
        popup.cfg.save.assert_not_called()

    def test_save_writes_config(self):
        from matchypatchy.gui.dialogs.popup_config import ConfigPopup
        popup = self._popup()
        with patch("matchypatchy.gui.dialogs.popup_config.QDialog.accept", create=True):
            ConfigPopup.accept(popup)
        popup.cfg.save.assert_called_once()
