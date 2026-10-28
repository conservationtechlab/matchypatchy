"""
Name lookups in the import threads, against a real database
"""
import logging
from unittest.mock import MagicMock

import pytest

from matchypatchy.database.mpdb import MatchyPatchyDB, sql_text


@pytest.fixture
def db(tmp_path):
    database = MatchyPatchyDB(str(tmp_path))
    # survey 1 is the default survey; add a second one in the default region
    database.add_survey("Survey B", 1, None, None)
    yield database
    database.close()


def _thread(db, cls, **attrs):
    thread = MagicMock()
    thread.mpDB = db
    thread.station_ref, thread.camera_ref = {}, {}
    for k, v in attrs.items():
        setattr(thread, k, v)
    if cls is not None:
        thread._convert_to_str = lambda v: None if v is None else str(v)
        thread._convert_to_float = lambda v: None
    return thread


class TestSqlText:
    def test_quotes(self):
        assert sql_text("O'Brien") == "'O''Brien'"

    @pytest.mark.parametrize("name", ["O'Brien", "name", 'say "hi"'])
    def test_round_trip(self, db, name):
        sid = db.add_station(name, None, None, 1)
        assert db.select("station", "id", row_cond=f"name={sql_text(name)}") == [(sid,)]


class TestQuotedLookups:
    def test_station_name_with_quote(self, db):
        from matchypatchy.threads.import_thread import FolderImportThread
        thread = _thread(db, None, station_level=1)
        first = FolderImportThread.station(thread, "/O'Brien/img.jpg", 1)
        assert FolderImportThread.station(thread, "/O'Brien/img.jpg", 1) == first
