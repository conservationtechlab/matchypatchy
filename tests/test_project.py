"""Tests for the open Project and the UsesProject mixin."""
from types import SimpleNamespace

import pytest

from matchypatchy.project import Project, UsesProject


def _project(null_logger):
    project = Project(null_logger)
    opened = []
    project.changed.connect(lambda: opened.append(project.cfg.HOME_DIR))
    return project, opened


def _invalid_project(tmp_path):
    """A project folder whose database is missing its embedding store"""
    home = tmp_path / "broken"
    (home / "Database").mkdir(parents=True)
    (home / "Database" / "matchypatchy.db").write_bytes(b"")
    return home


class TestProject:
    def test_open_loads_config_and_database(self, null_logger, tmp_path):
        project, opened = _project(null_logger)
        project.open(tmp_path / "a")
        assert project.cfg.HOME_DIR == tmp_path / "a"
        assert project.db.key
        assert opened == [tmp_path / "a"]
        project.close()

    def test_switching_closes_the_previous_database(self, null_logger, tmp_path, monkeypatch):
        project, opened = _project(null_logger)
        project.open(tmp_path / "a")
        first = project.db
        closed = []
        monkeypatch.setattr(first, "close", lambda: closed.append(first))

        project.open(tmp_path / "b")

        assert project.db is not first
        assert project.cfg.HOME_DIR == tmp_path / "b"
        assert closed == [first]
        assert opened == [tmp_path / "a", tmp_path / "b"]
        project.close()

    def test_failed_open_keeps_the_current_project(self, null_logger, tmp_path, monkeypatch):
        """The current project stays open and usable when the new one can't be opened"""
        project, opened = _project(null_logger)
        project.open(tmp_path / "a")
        current_db, current_cfg = project.db, project.cfg
        closed = []
        monkeypatch.setattr(current_db, "close", lambda: closed.append(current_db))

        with pytest.raises(ValueError):
            project.open(_invalid_project(tmp_path))

        assert project.db is current_db
        assert project.cfg is current_cfg
        assert closed == []
        assert opened == [tmp_path / "a"]
        assert project.db.count("survey") == 1
        project.close()

    def test_close_before_open_does_nothing(self, null_logger):
        Project(null_logger).close()


class TestUsesProject:
    def test_reads_whatever_project_is_open(self):
        class View(UsesProject):
            def __init__(self, project):
                self.project = project

        project = SimpleNamespace(db="db-a", cfg="cfg-a")
        view = View(project)
        project.db, project.cfg = "db-b", "cfg-b"
        assert view.mpDB == "db-b"
        assert view.cfg == "cfg-b"

    def test_mpdb_cannot_be_replaced(self):
        """Assigning a copy would go stale again when the project changes"""
        class View(UsesProject):
            project = SimpleNamespace(db="db", cfg="cfg")

        with pytest.raises(AttributeError):
            View().mpDB = "copy"
