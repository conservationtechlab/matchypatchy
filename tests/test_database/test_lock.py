"""Tests for the project database check-out lock."""
import json
import os
import socket

import pytest

from matchypatchy.database.lock import ProjectLock, ProjectLockedError, describe_holder, LOCK_NAME


def _write_holder(db_dir, **fields):
    holder = {"user": "someone", "host": "elsewhere", "pid": 1, "opened": "2026-10-22 10:42", "token": "x"}
    holder.update(fields)
    (db_dir / LOCK_NAME).write_text(json.dumps(holder))
    return holder


class TestProjectLock:
    def test_acquire_creates_lock_and_release_removes_it(self, tmp_path):
        lock = ProjectLock(tmp_path)
        lock.acquire()
        holder = json.loads((tmp_path / LOCK_NAME).read_text())
        assert holder["host"] == socket.gethostname()
        assert holder["pid"] == os.getpid()
        lock.release()
        assert not (tmp_path / LOCK_NAME).exists()

    def test_acquire_creates_missing_database_folder(self, tmp_path):
        lock = ProjectLock(tmp_path / "Database")
        lock.acquire()
        assert (tmp_path / "Database" / LOCK_NAME).exists()
        lock.release()

    def test_second_lock_is_refused(self, tmp_path):
        first = ProjectLock(tmp_path)
        first.acquire()
        with pytest.raises(ProjectLockedError) as e:
            ProjectLock(tmp_path).acquire()
        assert e.value.holder["pid"] == os.getpid()
        first.release()

    def test_lock_from_another_machine_is_refused(self, tmp_path):
        _write_holder(tmp_path, host="elsewhere")
        with pytest.raises(ProjectLockedError) as e:
            ProjectLock(tmp_path).acquire()
        assert "someone on elsewhere" in str(e.value)

    def test_force_takes_over(self, tmp_path):
        _write_holder(tmp_path, host="elsewhere")
        lock = ProjectLock(tmp_path)
        lock.acquire(force=True)
        assert json.loads((tmp_path / LOCK_NAME).read_text())["token"] == lock.token
        lock.release()
        assert not (tmp_path / LOCK_NAME).exists()

    def test_stale_lock_from_this_machine_is_cleared(self, tmp_path, monkeypatch):
        """A MatchyPatchy on this machine that crashed doesn't lock the user out"""
        monkeypatch.setattr("matchypatchy.database.lock._process_alive", lambda pid: False)
        _write_holder(tmp_path, host=socket.gethostname(), pid=os.getpid() + 1)
        lock = ProjectLock(tmp_path)
        lock.acquire()
        assert lock.token is not None
        lock.release()

    def test_live_lock_from_this_machine_is_refused(self, tmp_path, monkeypatch):
        monkeypatch.setattr("matchypatchy.database.lock._process_alive", lambda pid: True)
        _write_holder(tmp_path, host=socket.gethostname(), pid=os.getpid() + 1)
        with pytest.raises(ProjectLockedError):
            ProjectLock(tmp_path).acquire()

    def test_unreadable_lock_is_refused(self, tmp_path):
        (tmp_path / LOCK_NAME).write_text("not json")
        with pytest.raises(ProjectLockedError) as e:
            ProjectLock(tmp_path).acquire()
        assert e.value.holder is None
        assert "unknown user" in describe_holder(e.value.holder)

    def test_release_leaves_a_lock_taken_over_by_someone_else(self, tmp_path):
        lock = ProjectLock(tmp_path)
        lock.acquire()
        _write_holder(tmp_path, token="theirs")
        lock.release()
        assert json.loads((tmp_path / LOCK_NAME).read_text())["token"] == "theirs"

    def test_release_without_acquire_does_nothing(self, tmp_path):
        _write_holder(tmp_path)
        ProjectLock(tmp_path).release()
        assert (tmp_path / LOCK_NAME).exists()
