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


def _panel(data):
    """MagicMock standing in for a MetadataPanel over the given rows"""
    from matchypatchy.gui.dialogs.popup_media_edit import MetadataPanel
    panel = MagicMock()
    panel.data = data
    panel.individuals = pd.DataFrame({"name": ["Spot", "Spot"], "sex": ["F", "M"]}, index=[3, 4])
    panel._roi_rows = lambda: MetadataPanel._roi_rows(panel)
    panel._name_index = lambda iid: MetadataPanel._name_index(panel, iid)
    return panel


def _edit_rows():
    return pd.DataFrame({"id": [10, pd.NA], "media_id": [1, 1], "individual_id": [None, None],
                         "sex": [None, None], "viewpoint": [None, None]})


class TestMetadataPanel:
    def test_name_with_duplicate_names_uses_position(self):
        """Two individuals named Spot: picking the second assigns id 4"""
        from matchypatchy.gui.dialogs.popup_media_edit import MetadataPanel
        panel = _panel(_edit_rows())
        panel.name.currentIndex.return_value = 2
        MetadataPanel.change_name(panel)
        edits = [c.args[0] for c in panel.send_edit.call_args_list]
        assert [(e.rid, e.new_value) for e in edits] == [(10, 4)]  # video row skipped

    def test_viewpoint_edits_skip_video_row(self):
        from matchypatchy.gui.dialogs.popup_media_edit import MetadataPanel
        panel = _panel(_edit_rows())
        panel.ids = [10, pd.NA]
        panel.VIEWPOINTS = {"Any": "Any", "None": "None", "0": "Right", "1": "Left"}
        panel.viewpoint.currentIndex.return_value = 2  # multi-row list: Mixed, None, Right, Left
        MetadataPanel.change_viewpoint(panel)
        assert [c.args[0].rid for c in panel.send_edit.call_args_list] == [10]

    def test_new_individual_cancel_assigns_nothing(self):
        from matchypatchy.gui.dialogs.popup_media_edit import MetadataPanel
        panel = _panel(_edit_rows())
        with patch(f"{POPUP}.IndividualFillPopup") as fill:
            fill.return_value.exec.return_value = False
            MetadataPanel.new_individual(panel)
        panel.mpDB.add_individual.assert_not_called()
        panel.name.setCurrentIndex.assert_not_called()

    def test_new_individual_is_selected_not_written_directly(self):
        from matchypatchy.gui.dialogs.popup_media_edit import MetadataPanel
        panel = _panel(_edit_rows())
        panel.mpDB.add_individual.return_value = 4
        with patch(f"{POPUP}.IndividualFillPopup") as fill:
            fill.return_value.exec.return_value = True
            MetadataPanel.new_individual(panel)
        panel.mpDB.edit_row.assert_not_called()   # assignment goes through the edit stack
        panel.name.setCurrentIndex.assert_called_once_with(2)


class TestPopupFavorite:
    def test_favorite_goes_through_the_edit_stack(self):
        from matchypatchy.gui.dialogs.popup_media_edit import MediaEditPopup
        dialog = _popup(pd.DataFrame({"id": [10], "media_id": [1], "favorite": [0]}), data_type=1)
        dialog.edit_stack = []
        dialog.button_favorite.isChecked.return_value = True
        MediaEditPopup.favorite(dialog)
        dialog.mpDB.edit_row.assert_not_called()
        assert [(e.rid, e.reference, e.new_value) for e in dialog.edit_stack] == [(10, "favorite", 1)]
        assert dialog.data.loc[0, "favorite"] == 1

    def test_video_row_cannot_be_favorited(self):
        from matchypatchy.gui.dialogs.popup_media_edit import MediaEditPopup
        dialog = _popup(pd.DataFrame({"id": [pd.NA], "media_id": [1], "favorite": [0]}), data_type=1)
        dialog.edit_stack = []
        dialog.button_favorite.isChecked.return_value = True
        MediaEditPopup.favorite(dialog)
        assert dialog.edit_stack == []
        dialog.mpDB.edit_row.assert_not_called()


class TestComment:
    def test_pending_comment_is_emitted_before_switching_image(self):
        from matchypatchy.gui.dialogs.popup_media_edit import MetadataPanel
        panel = MagicMock()
        panel.comment.timer.isActive.return_value = True
        MetadataPanel.flush_comment(panel)
        panel.comment.timer.stop.assert_called_once()
        panel.change_comment.assert_called_once()

    def test_nothing_pending(self):
        from matchypatchy.gui.dialogs.popup_media_edit import MetadataPanel
        panel = MagicMock()
        panel.comment.timer.isActive.return_value = False
        MetadataPanel.flush_comment(panel)
        panel.change_comment.assert_not_called()

    def test_ok_flushes_pending_comment(self):
        from matchypatchy.gui.dialogs.popup_media_edit import MediaEditPopup
        dialog = MagicMock()
        MediaEditPopup.save(dialog)
        dialog.metadatapanel.flush_comment.assert_called_once()
        dialog.accept.assert_called_once()
