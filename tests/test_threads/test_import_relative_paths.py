"""Importing files whose path within their folder matches a file imported from another folder."""
from types import SimpleNamespace

import pandas as pd

from matchypatchy.threads import import_thread


class SignalSpy:
    def __init__(self):
        self.calls = []

    def emit(self, *args):
        self.calls.append(args)


def _folder_import(db, tmp_path, file_path, monkeypatch):
    parent = SimpleNamespace(mpDB=db, cfg=SimpleNamespace(THUMBNAIL_DIR=str(tmp_path / "thumbs")))
    data = pd.DataFrame([{"filepath": str(file_path), "datetime": "2024-01-01 12:00:00"}])
    thread = import_thread.FolderImportThread(parent, (1,), data, station_level=0, camera_level=0)
    monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "t.jpg")
    thread.finished = SignalSpy()
    thread.isInterruptionRequested = lambda: False
    thread.run()


def test_same_relative_path_from_two_folders_imports_both(tmp_db, tmp_path, monkeypatch):
    db, _ = tmp_db
    for year in ("2023", "2024"):
        file_path = tmp_path / year / "Site01" / "IMG_0001.JPG"
        file_path.parent.mkdir(parents=True)
        file_path.write_bytes(year.encode())
        _folder_import(db, tmp_path, file_path, monkeypatch)

    media = db.select("media", columns="base_dir_id, relative_path")
    assert len(media) == 2
    assert {relative_path for _, relative_path in media} == {"IMG_0001.JPG"}
    assert len({base_dir_id for base_dir_id, _ in media}) == 2
