"""
Model download helpers and the model download dialog's bookkeeping
"""
from unittest.mock import MagicMock, patch

MDT = "matchypatchy.threads.model_download_thread"
MODELS = {"MiewID": [["miew.onnx", "miew.onnx.data"], ["u1", "u2"]],
          "MD": ["md.pt", "u3"]}


class TestGetPath:
    def _get(self, ml_dir, key):
        from matchypatchy.threads.model_download_thread import get_path
        with patch(f"{MDT}.load_model", return_value=MODELS):
            return get_path(ml_dir, key)

    def test_interrupted_download_is_not_available(self, tmp_path):
        """Only the .onnx of a two-file model: not usable"""
        (tmp_path / "miew.onnx").write_bytes(b"x")
        assert self._get(tmp_path, "MiewID") is None

    def test_all_files_present(self, tmp_path):
        (tmp_path / "miew.onnx").write_bytes(b"x")
        (tmp_path / "miew.onnx.data").write_bytes(b"x")
        assert self._get(tmp_path, "MiewID") == tmp_path / "miew.onnx"

    def test_single_file_given_as_string(self, tmp_path):
        (tmp_path / "md.pt").write_bytes(b"x")
        assert self._get(tmp_path, "MD") == tmp_path / "md.pt"

    def test_no_key(self, tmp_path):
        assert self._get(tmp_path, None) is None


def _popup(pending=(), available=()):
    popup = MagicMock()
    popup.models = list(MODELS)
    popup.pending = set(pending)
    popup.available_models = {k: f"/{k}" for k in available}
    return popup


class TestDownloadPopup:
    def test_ticking_skips_downloaded_and_queued_models(self):
        from matchypatchy.gui.dialogs.popup_ml import MLDownloadPopup
        popup = _popup(pending={"MiewID"})
        popup.checkbox_layout.itemAtPosition.return_value.widget.return_value.isChecked.return_value = True
        MLDownloadPopup.toggle_checkbox(popup)
        popup.download_ml.assert_called_once_with({"MD"})

    def test_progress_stays_while_other_models_are_pending(self):
        from matchypatchy.gui.dialogs.popup_ml import MLDownloadPopup
        popup = _popup(pending={"MiewID", "MD"})
        MLDownloadPopup.on_download_result(popup, "MiewID", True, "Download Complete")
        assert popup.pending == {"MD"}
        popup.progress_bar.hide.assert_not_called()
        popup.enable_close.assert_not_called()

    def test_last_result_finishes(self):
        from matchypatchy.gui.dialogs.popup_ml import MLDownloadPopup
        popup = _popup(pending={"MD"})
        MLDownloadPopup.on_download_result(popup, "MD", True, "Download Complete")
        popup.progress_bar.hide.assert_called_once()
        popup.enable_close.assert_called_once()
        popup.discover_models.assert_called()

    def test_failed_download_can_be_retried(self):
        from matchypatchy.gui.dialogs.popup_ml import MLDownloadPopup
        popup = _popup(pending={"MD"})
        MLDownloadPopup.on_download_result(popup, "MD", False, "Network error")
        checkbox = popup.checkbox_layout.itemAtPosition.return_value.widget.return_value
        checkbox.setChecked.assert_called_once_with(False)
        popup.warning_label.setText.assert_called_once_with("MD: Network error")
