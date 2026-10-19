"""
Tests for network filesystem detection in matchypatchy.database.filesystem
"""
from pathlib import PurePosixPath
from unittest.mock import MagicMock, mock_open, patch

from matchypatchy.database.filesystem import _check_linux, _check_macos, _is_under


PROC_MOUNTS = """\
/dev/nvme0n1p2 / ext4 rw,relatime 0 0
//server/share /mnt/data cifs rw,relatime 0 0
server:/export /mnt/nfs\\040share nfs4 rw,relatime 0 0
"""

MAC_MOUNT = """\
/dev/disk3s1s1 on / (apfs, sealed, local, read-only, journaled)
/dev/disk3s5 on /System/Volumes/Data (apfs, local, journaled, nobrowse)
//user@server/share on /Volumes/share (smbfs, nodev, nosuid, mounted by user)
/dev/disk4s1 on /Volumes/My Drive (apfs, local, nodev, nosuid, journaled)
"""


def _linux(path):
    with patch("builtins.open", mock_open(read_data=PROC_MOUNTS)):
        return _check_linux(PurePosixPath(path))


def _macos(path):
    result = MagicMock(stdout=MAC_MOUNT)
    with patch("matchypatchy.database.filesystem.subprocess.run", return_value=result):
        return _check_macos(PurePosixPath(path))


class TestIsUnder:
    def test_same_path(self):
        assert _is_under(PurePosixPath("/mnt/data"), "/mnt/data")

    def test_child_path(self):
        assert _is_under(PurePosixPath("/mnt/data/project"), "/mnt/data")

    def test_sibling_with_shared_prefix(self):
        assert not _is_under(PurePosixPath("/mnt/data2/project"), "/mnt/data")

    def test_root_contains_everything(self):
        assert _is_under(PurePosixPath("/home/user"), "/")


class TestCheckLinux:
    def test_local_path(self):
        assert _linux("/home/user/project") == (False, "ext4")

    def test_network_path(self):
        assert _linux("/mnt/data/project") == (True, "cifs")

    def test_shared_prefix_is_not_network(self):
        assert _linux("/mnt/data2/project") == (False, "ext4")

    def test_mount_point_with_escaped_space(self):
        assert _linux("/mnt/nfs share/project") == (True, "nfs4")


class TestCheckMacos:
    def test_local_path(self):
        assert _macos("/Users/me/project") == (False, "apfs")

    def test_network_path_not_masked_by_root(self):
        assert _macos("/Volumes/share/project") == (True, "smbfs")

    def test_mount_point_with_space(self):
        assert _macos("/Volumes/My Drive/project") == (False, "apfs")
