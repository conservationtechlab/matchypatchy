"""
Tests for matchypatchy.database.thumbnails
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

from matchypatchy.database import thumbnails


def _mpdb(no_thumbnail_rows, thumbnail_rows):
    """mpDB mock: _command returns ids without a thumbnail row, select returns (fid, filepath) rows"""
    mpDB = MagicMock()
    mpDB._command.return_value = no_thumbnail_rows
    mpDB.select.return_value = thumbnail_rows
    return mpDB


class TestCheckMissingThumbnails:
    def test_ids_without_thumbnail_row(self, tmp_path):
        mpDB = _mpdb([(1,), (2,)], [])
        assert thumbnails.check_missing_thumbnails(mpDB, tmp_path, data_type=1) == [1, 2]

    def test_existing_thumbnail_not_missing(self, tmp_path):
        (tmp_path / "a.jpg").touch()
        mpDB = _mpdb([], [(3, "a.jpg")])
        assert thumbnails.check_missing_thumbnails(mpDB, tmp_path, data_type=0) == []

    def test_thumbnail_file_missing(self, tmp_path):
        mpDB = _mpdb([], [(3, "gone.jpg")])
        assert thumbnails.check_missing_thumbnails(mpDB, tmp_path, data_type=0) == [3]

    def test_failed_query_does_not_raise(self, tmp_path):
        """_command returns None on an sqlite error"""
        mpDB = _mpdb(None, [(3, "gone.jpg")])
        assert thumbnails.check_missing_thumbnails(mpDB, tmp_path, data_type=1) == [3]

    def test_missing_placeholder_listed_once(self, tmp_path):
        """A not-found placeholder whose asset file is also missing is listed once, not twice"""
        placeholder = Path("/nonexistent/thumbnail_notfound.png")
        mpDB = _mpdb([], [(4, str(placeholder))])
        with patch("matchypatchy.database.thumbnails.asset_path", return_value=placeholder):
            assert thumbnails.check_missing_thumbnails(mpDB, tmp_path, data_type=1) == [4]

    def test_absolute_thumbnail_path(self, tmp_path):
        """Paths that are not plain filenames are checked on disk"""
        (tmp_path / "abs.jpg").touch()
        mpDB = _mpdb([], [(5, str(tmp_path / "abs.jpg")), (6, str(tmp_path / "gone.jpg"))])
        assert thumbnails.check_missing_thumbnails(mpDB, tmp_path, data_type=0) == [6]

    def test_missing_thumbnail_dir(self, tmp_path):
        """An unreadable thumbnail directory makes every listed thumbnail missing"""
        mpDB = _mpdb([], [(7, "a.jpg")])
        assert thumbnails.check_missing_thumbnails(mpDB, tmp_path / "nope", data_type=0) == [7]


class TestDecodeScale:
    """Decoding itself is not tested here: conftest stubs out cv2 and Qt"""
    def test_large_region_decodes_small(self):
        assert thumbnails._decode_scale(4000, 3000) == 8

    def test_region_is_kept_at_least_thumbnail_size(self):
        assert thumbnails._decode_scale(799, 400) == 2
        assert thumbnails._decode_scale(800, 400) == 4

    def test_small_or_unknown_region_decodes_full_size(self):
        assert thumbnails._decode_scale(300, 300) == 1
        assert thumbnails._decode_scale(0, 0) == 1
