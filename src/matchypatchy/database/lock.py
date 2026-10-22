'''
Check-out lock for a project database

SQLite and Chroma rely on file locks to keep two writers apart, which network
shares mounted without byte-range locks (eg. cifs with nobrl) don't enforce
between machines. A lock file next to the database, created only if it doesn't
already exist, lets one MatchyPatchy at a time open it. Creating a file that
must not exist is checked by the file server, so it holds across machines.
'''
import datetime
import getpass
import json
import logging
import os
import socket
import sys
import uuid
from pathlib import Path


logger = logging.getLogger(__name__)

LOCK_NAME = 'matchypatchy.lock'


class ProjectLockedError(Exception):
    """The database is checked out by another MatchyPatchy, holder describes it"""
    def __init__(self, path, holder):
        self.path = path
        self.holder = holder
        super().__init__(f"Database at {path.parent} is in use by {describe_holder(holder)}")


def describe_holder(holder):
    """Who holds a lock and since when, eg. 'kswanson on saguaro since 2026-10-22 10:42'"""
    if not holder:
        return "an unknown user (the lock file could not be read)"
    return (f"{holder.get('user', '?')} on {holder.get('host', '?')} "
            f"since {holder.get('opened', '?')}")


def _process_alive(pid):
    """Whether a process with this pid is running on this machine"""
    if sys.platform == "win32":
        # os.kill on Windows terminates the process, ask for its exit code instead
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by another user
    return True


class ProjectLock():
    """
    Lock file in a project's Database folder, held while the project is open

    Project.open acquires it before opening the database and Project.close
    releases it. A lock left by a MatchyPatchy on this machine that is no longer
    running is cleared without asking; one from another machine can only be
    taken over with force, since there is no way to tell if it is still in use.
    """
    def __init__(self, db_dir):
        self.path = Path(db_dir) / LOCK_NAME
        self.token = None  # set while held, identifies our lock file

    def _read(self):
        """The current lock file's contents, None if it can't be read"""
        try:
            return json.loads(self.path.read_text())
        except (OSError, ValueError):
            return None

    def _is_stale(self, holder):
        """Left by a MatchyPatchy on this machine that has since exited"""
        if not holder or holder.get('host') != socket.gethostname():
            return False
        pid = holder.get('pid')
        return isinstance(pid, int) and pid != os.getpid() and not _process_alive(pid)

    def acquire(self, force=False):
        """
        Take the lock, raise ProjectLockedError if another MatchyPatchy holds it

        force replaces a lock held by someone else, for one left behind by a
        crash on another machine.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        token = uuid.uuid4().hex
        holder = {"user": getpass.getuser(), "host": socket.gethostname(), "pid": os.getpid(),
                  "opened": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "token": token}
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            current = self._read()
            if not force and not self._is_stale(current):
                raise ProjectLockedError(self.path, current)
            logger.warning(f"Replacing lock on {self.path} held by {describe_holder(current)}")
            self.path.write_text(json.dumps(holder))
        else:
            with os.fdopen(fd, 'w') as f:
                f.write(json.dumps(holder))
        self.token = token
        logger.info(f"Locked database at {self.path.parent}")

    def release(self):
        """Remove the lock file, unless someone has since taken it over with force"""
        if self.token is None:
            return
        current = self._read()
        if current and current.get('token') == self.token:
            try:
                self.path.unlink()
                logger.info(f"Unlocked database at {self.path.parent}")
            except OSError as e:
                logger.error(f"Could not remove lock {self.path}: {e}")
        else:
            logger.warning(f"Lock on {self.path} was taken over by {describe_holder(current)}, leaving it")
        self.token = None
