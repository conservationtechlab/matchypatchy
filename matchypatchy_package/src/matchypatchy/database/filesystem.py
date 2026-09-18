import os
import platform
import subprocess
from pathlib import Path


class RemoteFilesystemError(Exception):
    """Raised when the database path is on a network/SMB mount."""
    pass


def is_network_path(path: Path) -> tuple[bool, str]:
    """
    Detect if a path lives on a network filesystem (SMB/CIFS/NFS/AFP).
    Returns (is_network, filesystem_type_or_reason).
    """
    path = path.resolve()
    system = platform.system()

    if system == "Linux":
        return _check_linux(path)
    elif system == "Darwin":
        return _check_macos(path)
    elif system == "Windows":
        return _check_windows(path)
    else:
        # Unknown platform: don't block, but flag as unverified
        return False, "unknown platform, could not verify"


def _check_linux(path: Path) -> tuple[bool, str]:
    """Use /proc/mounts to find the filesystem type of the containing mount."""
    network_fs_types = {"cifs", "smb", "smbfs", "nfs", "nfs4", "afpfs", "fuse.sshfs"}
    try:
        with open("/proc/mounts", "r") as f:
            mounts = [line.split() for line in f.readlines()]
        # Find the longest matching mount point (most specific)
        best_match = None
        for mount in mounts:
            mount_point, fs_type = mount[1], mount[2]
            if str(path).startswith(mount_point):
                if best_match is None or len(mount_point) > len(best_match[0]):
                    best_match = (mount_point, fs_type)
        if best_match and best_match[1].lower() in network_fs_types:
            return True, best_match[1]
        return False, best_match[1] if best_match else "unknown"
    except OSError:
        return False, "could not read /proc/mounts"


def _check_macos(path: Path) -> tuple[bool, str]:
    """Use `mount` output; macOS labels SMB mounts as 'smbfs'."""
    network_fs_types = {"smbfs", "nfs", "afpfs", "webdav"}
    try:
        result = subprocess.run(["mount"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            # e.g. "//user@server/share on /Volumes/share (smbfs, ...)"
            if " on " in line and str(path).startswith(line.split(" on ")[1].split(" (")[0]):
                fs_type = line.split("(")[1].split(",")[0].strip()
                if fs_type.lower() in network_fs_types:
                    return True, fs_type
                return False, fs_type
        return False, "unknown"
    except (subprocess.SubprocessError, OSError, IndexError):
        return False, "could not determine"


def _check_windows(path: Path) -> tuple[bool, str]:
    """A UNC path (\\\\server\\share) or a mapped drive whose DriveType is REMOTE."""
    import ctypes

    path_str = str(path)
    if path_str.startswith("\\\\") or path_str.startswith("//"):
        return True, "UNC path"

    drive = os.path.splitdrive(path_str)[0]  # e.g. "Z:"
    if not drive:
        return False, "no drive letter"

    DRIVE_REMOTE = 4
    drive_type = ctypes.windll.kernel32.GetDriveTypeW(f"{drive}\\")
    if drive_type == DRIVE_REMOTE:
        return True, "mapped network drive"
    return False, "local drive"