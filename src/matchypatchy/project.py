"""
The open MatchyPatchy project

One Project lives as long as the main window. Opening another project swaps the
config and database inside it, so every object holding the Project sees the new
one, instead of each object keeping its own copy of the database.
"""
import logging

from PyQt6.QtCore import QObject, pyqtSignal

from matchypatchy.config import mpConfig
from matchypatchy.database.mpdb import MatchyPatchyDB
from matchypatchy.database.lock import ProjectLock


logger = logging.getLogger(__name__)


class Project(QObject):
    """Config and database of the open project"""

    changed = pyqtSignal()  # emitted after cfg and db point at a newly opened project
    # emitted with a table name after a write to one of the tables the gui keeps lists of
    # (mpdb.REPORTED_TABLES). Writes from import threads arrive queued in the main thread
    data_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._cfg = None
        self._db = None
        self._lock = None  # check-out lock on the open project's database

    @property
    def cfg(self):
        """Config of the open project, None before the first open()"""
        return self._cfg

    @property
    def db(self):
        """Database of the open project, None before the first open()"""
        return self._db

    def open(self, home_dir, force=False):
        """
        Open the project in home_dir, raise if its database is unusable

        Raises ProjectLockedError if another MatchyPatchy has the database open,
        force takes over its lock. The new project is loaded before the current
        one is closed, so a failed open leaves the current project open and unchanged.
        """
        cfg = mpConfig(home_dir)
        lock = ProjectLock(cfg.DB_DIR)
        # reopening the open project keeps its lock, it would otherwise lock itself out
        reopening = self._lock is not None and self._lock.path.resolve() == lock.path.resolve()
        if reopening:
            lock = self._lock
        else:
            lock.acquire(force=force)
        try:
            db = MatchyPatchyDB(cfg.DB_DIR)
            if not db.key:
                db.close()
                raise ValueError(f"Database at {cfg.DB_DIR} is invalid.")
        except Exception:
            if not reopening:
                lock.release()
            raise
        db.add_change_listener(self.data_changed.emit)

        old_db, old_lock = self._db, self._lock
        self._cfg, self._db, self._lock = cfg, db, lock
        if old_db is not None:
            old_db.close()
        if old_lock is not None and not reopening:
            old_lock.release()
        self.changed.emit()

    def close(self):
        """Close the open project's database and release its lock"""
        if self._db is not None:
            self._db.close()
        if self._lock is not None:
            self._lock.release()
            self._lock = None


class UsesProject:
    """
    Read-only mpDB and cfg that always point at the open project

    Mixed into gui classes that need the database, in place of keeping their own
    self.mpDB, which went stale when the user opened another project: the old
    database reconnects on use, so stale copies silently read and wrote the
    previous project. Classes set self.project in __init__, normally to
    parent.project. There is no setter on purpose, assigning mpDB or cfg would
    bring back the copy this replaces.

    Threads don't use this. They copy mpDB when created and finish against the
    project they started in.
    """

    @property
    def mpDB(self):
        return self.project.db

    @property
    def cfg(self):
        return self.project.cfg
