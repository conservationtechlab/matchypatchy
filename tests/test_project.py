"""Tests for the open Project and the UsesProject mixin."""
from types import SimpleNamespace

import pytest

from matchypatchy.project import Project, UsesProject


def _project():
    project = Project()
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
    def test_open_loads_config_and_database(self, tmp_path):
        project, opened = _project()
        project.open(tmp_path / "a")
        assert project.cfg.HOME_DIR == tmp_path / "a"
        assert project.db.key
        assert opened == [tmp_path / "a"]
        project.close()

    def test_switching_closes_the_previous_database(self, tmp_path, monkeypatch):
        project, opened = _project()
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

    def test_failed_open_keeps_the_current_project(self, tmp_path, monkeypatch):
        """The current project stays open and usable when the new one can't be opened"""
        project, opened = _project()
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

    def test_close_before_open_does_nothing(self):
        Project().close()


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


class TestDataChanged:
    def _written(self, tmp_path):
        project, _ = _project()
        project.open(tmp_path / "a")
        tables = []
        project.changed.connect(lambda: None)
        project.data_changed.connect(tables.append)
        return project, tables

    def test_writes_to_listed_tables_are_reported(self, tmp_path):
        project, tables = self._written(tmp_path)
        db = project.db
        survey = db.add_survey("S", None, None, None)
        station = db.add_station("St", None, None, survey)
        db.add_camera("Cam", station)
        iid = db.add_individual("Spot")
        db.edit_row("individual", iid, {"name": "Dot"})
        assert tables == ["survey", "station", "camera", "individual", "individual"]
        project.close()

    def test_deletes_report_the_tables_they_cascade_to(self, tmp_path):
        project, tables = self._written(tmp_path)
        db = project.db
        survey = db.add_survey("S", None, None, None)
        tables.clear()
        db.delete("survey", "id=?", (survey,))
        assert tables == ["survey", "station", "camera"]
        project.close()

    def test_media_and_roi_writes_are_not_reported(self, tmp_path):
        """An import makes thousands of these"""
        project, tables = self._written(tmp_path)
        db = project.db
        station = db.add_station("St", None, None, 1)
        tables.clear()
        mid = db.add_media(db.add_upload("/a"), "x.jpg", "h", ".jpg", "2024-01-01 10:00:00", station)
        db.add_roi(mid, 0, 0.1, 0.1, 0.1, 0.1)
        db.edit_row("roi", 1, {"favorite": 1})
        assert tables == []
        project.close()

    def test_failed_write_is_not_reported(self, tmp_path):
        project, tables = self._written(tmp_path)
        db = project.db
        db.add_survey("Taken", None, None, None)
        tables.clear()
        assert db.add_survey("Taken", None, None, None) is None
        assert tables == []
        project.close()

    def test_console_commands_report_every_listed_table(self, tmp_path):
        project, tables = self._written(tmp_path)
        project.db._command("UPDATE survey SET year_start=2024;")
        assert sorted(tables) == sorted(["region", "survey", "station", "camera", "individual"])
        project.close()
