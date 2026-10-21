"""
The open MatchyPatchy project

One Project lives as long as the main window. Opening another project swaps the
config and database inside it, so every object holding the Project sees the new
one, instead of each object keeping its own copy of the database.
"""
from PyQt6.QtCore import QObject, pyqtSignal

from matchypatchy.config import mpConfig
from matchypatchy.database.mpdb import MatchyPatchyDB


class Project(QObject):
    """Config and database of the open project"""

    changed = pyqtSignal()  # emitted after cfg and db point at a newly opened project

    def __init__(self, logger):
        super().__init__()
        self.logger = logger
        self._cfg = None
        self._db = None

    @property
    def cfg(self):
        """Config of the open project, None before the first open()"""
        return self._cfg

    @property
    def db(self):
        """Database of the open project, None before the first open()"""
        return self._db

    def open(self, home_dir):
        """
        Open the project in home_dir, raise if its database is unusable

        The new project is loaded before the current one is closed, so a failed
        open leaves the current project open and unchanged.
        """
        cfg = mpConfig(home_dir)
        db = MatchyPatchyDB(cfg.DB_DIR, self.logger)
        if not db.key:
            db.close()
            raise ValueError(f"Database at {cfg.DB_DIR} is invalid.")

        old_db = self._db
        self._cfg, self._db = cfg, db
        if old_db is not None:
            old_db.close()
        self.changed.emit()

    def close(self):
        """Close the open project's database"""
        if self._db is not None:
            self._db.close()


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
