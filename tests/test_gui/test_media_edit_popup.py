"""
Unit tests for MediaEditPopup / MetadataPanel actions

Methods are called on a MagicMock standing in for the dialog, so no Qt
display is needed. PyQt6 is stubbed out in conftest.py.
"""
from unittest.mock import MagicMock, patch

import pandas as pd

POPUP = "matchypatchy.gui.dialogs.popup_media_edit"


def _confirm(accepted=True):
    popup = MagicMock()
    popup.exec.return_value = accepted
    return popup


def _popup(data, data_type, index=0):
    dialog = MagicMock()
    dialog.data = data
    dialog.ids = data["id"].tolist()
    dialog.data_type = data_type
    dialog.current_image_index = index
    dialog.roi_updated = False
    return dialog


def _roi_rows():
    """Two rois of media 1, plus the full-video row (no roi id)"""
    return pd.DataFrame({"id": [10, 11, pd.NA], "media_id": [1, 1, 1]})


class TestDelete:
    def test_full_images_view_deletes_the_media(self):
        """In the media view id is a media id; it must not delete the roi with that id"""
        from matchypatchy.gui.dialogs.popup_media_edit import MediaEditPopup
        dialog = _popup(pd.DataFrame({"id": [5, 6]}), data_type=0)
        with patch(f"{POPUP}.AlertPopup", return_value=_confirm()), \
                patch(f"{POPUP}.fetch_roi", return_value=pd.DataFrame({"roi_id": [20, 21]})):
            MediaEditPopup.delete(dialog)
        dialog.mpDB.delete.assert_called_once_with("media", "id=5")
        assert [c.args[0] for c in dialog.mpDB.delete_emb.call_args_list] == [20, 21]
        assert dialog.roi_updated is True
        assert dialog.ids == [6]
        dialog.refresh.assert_called_once()

    def test_roi_view_deletes_the_roi(self):
        from matchypatchy.gui.dialogs.popup_media_edit import MediaEditPopup
        dialog = _popup(_roi_rows(), data_type=1)
        with patch(f"{POPUP}.AlertPopup", return_value=_confirm()):
            MediaEditPopup.delete(dialog)
        dialog.mpDB.delete.assert_called_once_with("roi", "id=10")
        dialog.mpDB.delete_emb.assert_called_once_with(10)
        assert dialog.roi_updated is True

    def test_video_row_has_nothing_to_delete(self):
        from matchypatchy.gui.dialogs.popup_media_edit import MediaEditPopup
        dialog = _popup(_roi_rows(), data_type=1, index=2)
        with patch(f"{POPUP}.AlertPopup", return_value=_confirm()) as alert:
            MediaEditPopup.delete(dialog)
        alert.assert_not_called()
        dialog.mpDB.delete.assert_not_called()

    def test_cancel_deletes_nothing(self):
        from matchypatchy.gui.dialogs.popup_media_edit import MediaEditPopup
        dialog = _popup(_roi_rows(), data_type=1)
        with patch(f"{POPUP}.AlertPopup", return_value=_confirm(False)):
            MediaEditPopup.delete(dialog)
        dialog.mpDB.delete.assert_not_called()
        assert dialog.roi_updated is False

    def test_closes_when_only_the_video_row_is_left(self):
        from matchypatchy.gui.dialogs.popup_media_edit import MediaEditPopup
        dialog = _popup(pd.DataFrame({"id": [10, pd.NA], "media_id": [1, 1]}), data_type=1)
        with patch(f"{POPUP}.AlertPopup", return_value=_confirm()):
            MediaEditPopup.delete(dialog)
        dialog.close_out.assert_called_once()
        dialog.refresh.assert_not_called()


class TestCallersReloadAfterPopupChanges:
    def test_media_view_multi_edit_reloads_after_delete(self):
        from matchypatchy.gui.display_media import DisplayMedia
        dm = MagicMock()
        dm.media_table._data_filtered = pd.DataFrame({"id": [10, 11], "select": [1, 1]})
        dm.media_table.selectedRows.return_value = [0, 1]
        with patch("matchypatchy.gui.display_media.MediaEditPopup") as popup_cls:
            popup_cls.return_value.exec.return_value = False   # cancelled after deleting
            popup_cls.return_value.roi_updated = True
            DisplayMedia.edit_row_multiple(dm)
        dm.refresh_table.assert_called_once_with(reload=True)

    def test_compare_view_rebuilds_after_delete(self):
        from matchypatchy.gui.display_compare import DisplayCompare
        dc = MagicMock()
        dc.has_query.return_value = True
        with patch("matchypatchy.gui.display_compare.MediaEditPopup") as popup_cls:
            popup_cls.return_value.exec.return_value = False
            popup_cls.return_value.roi_updated = True
            DisplayCompare.edit_image(dc, 10)
        dc.filter_neighbors.assert_called_once()
        dc.QueryContainer.refresh_data.assert_not_called()


class TestSaveRoi:
    def test_redrawn_box_updates_the_roi_in_place(self):
        """Keeps the roi id (and so its individual, viewpoint, favorite); drops the stale embedding"""
        from matchypatchy.gui.dialogs.popup_media_edit import MediaEditPopup
        data = pd.DataFrame({"id": [10], "media_id": [1], "filepath": ["a.jpg"], "ext": [".jpg"],
                             "bbox_x": [0.1], "bbox_y": [0.1], "bbox_w": [0.2], "bbox_h": [0.2],
                             "thumbnail_path": ["old.jpg"]})
        dialog = _popup(data, data_type=1)
        dialog.new_bbox = {"bbox_x": 0.3, "bbox_y": 0.4, "bbox_w": 0.25, "bbox_h": 0.5, "frame": 0}
        confirm = MagicMock()
        with patch(f"{POPUP}.QDialog") as qdialog, \
                patch(f"{POPUP}.AlertPopup", return_value=confirm), \
                patch(f"{POPUP}.save_roi_thumbnail", return_value="new.jpg"):
            confirm.exec.return_value = qdialog.DialogCode.Accepted
            MediaEditPopup.save_roi(dialog)
        dialog.mpDB.edit_row.assert_called_once_with(
            "roi", 10, {"frame": 0, "bbox_x": 0.3, "bbox_y": 0.4, "bbox_w": 0.25, "bbox_h": 0.5, "emb": 0})
        dialog.mpDB.delete_emb.assert_called_once_with(10)
        dialog.mpDB.batch_update_thumbnails.assert_called_once_with(
            "roi_thumbnails", "fid", {10: {"filepath": "new.jpg"}})
        dialog.mpDB.delete.assert_not_called()
        dialog.mpDB.add_roi.assert_not_called()
        assert dialog.data.loc[0, "id"] == 10
        assert dialog.data.loc[0, "bbox_x"] == 0.3
        assert dialog.roi_updated is True
