import os
import platform
import re
import subprocess
from pathlib import Path


def _is_network_path(path: Path) -> tuple[bool, str]:
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


def _is_under(path: Path, mount_point: str) -> bool:
    """Whether path is mount_point or inside it, matching whole path components
    so /mnt/data2 is not treated as inside /mnt/data"""
    return path == Path(mount_point) or Path(mount_point) in path.parents


def _unescape_mount(field: str) -> str:
    """Decode the octal escapes (e.g. "\\040" for a space) used in /proc/mounts"""
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), field)


def _check_linux(path: Path) -> tuple[bool, str]:
    """Use /proc/mounts to find the filesystem type of the containing mount."""
    network_fs_types = {"cifs", "smb", "smbfs", "nfs", "nfs4", "afpfs", "fuse.sshfs"}
    try:
        with open("/proc/mounts", "r") as f:
            mounts = [line.split() for line in f.readlines()]
        # Find the longest matching mount point (most specific)
        best_match = None
        for mount in mounts:
            # /proc/mounts escapes spaces and other characters as octal, e.g. "\040"
            mount_point, fs_type = _unescape_mount(mount[1]), mount[2]
            if _is_under(path, mount_point):
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
        # Find the longest matching mount point (most specific), "/" matches every path
        best_match = None
        for line in result.stdout.splitlines():
            # e.g. "//user@server/share on /Volumes/share (smbfs, ...)"
            if " on " not in line or " (" not in line:
                continue
            mount_point = line.split(" on ", 1)[1].rsplit(" (", 1)[0]
            fs_type = line.rsplit(" (", 1)[1].split(",")[0].strip(" )")
            if _is_under(path, mount_point):
                if best_match is None or len(mount_point) > len(best_match[0]):
                    best_match = (mount_point, fs_type)
        if best_match and best_match[1].lower() in network_fs_types:
            return True, best_match[1]
        return False, best_match[1] if best_match else "unknown"
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
