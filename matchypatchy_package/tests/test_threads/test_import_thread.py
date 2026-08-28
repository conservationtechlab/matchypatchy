"""Tests for matchypatchy thread workers in import_thread.py."""
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from matchypatchy.threads import import_thread


class SignalSpy:
    def __init__(self):
        self.calls = []

    def emit(self, *args):
        self.calls.append(args)


def _make_parent(db, logger, thumbnail_dir):
    cfg = SimpleNamespace(THUMBNAIL_DIR=str(thumbnail_dir))
    return SimpleNamespace(mpDB=db, logger=logger, cfg=cfg)


class TestCSVMigrateThread:
    def test_raises_value_error_for_missing_columns(self, tmp_db, null_logger, tmp_path):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        data = pd.DataFrame([{"id": 1}])

        with pytest.raises(ValueError, match="missing the following required columns"):
            import_thread.CSVMigrateThread(parent, data)

    def test_run_imports_rows_and_emits_signals(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")

        img_dir = tmp_path / "import"
        img_dir.mkdir()
        file_1 = img_dir / "s1" / "c1" / "a.jpg"
        file_2 = img_dir / "s1" / "c1" / "b.jpg"
        file_1.parent.mkdir(parents=True)
        file_1.write_bytes(b"a")
        file_2.write_bytes(b"b")

        row_common = {
            "frame": 0,
            "bbox_x": 0.1,
            "bbox_y": 0.2,
            "bbox_w": 0.3,
            "bbox_h": 0.4,
            "viewpoint": 1,
            "reviewed": 1,
            "media_id": 1,
            "individual_id": 3,
            "emb": 1,
            "base_dir_id": 7,
            "ext": ".jpg",
            "timestamp": "2024-01-01 12:00:00",
            "station_id": 10,
            "sequence_id": 11,
            "camera_id": 12,
            "external_id": 99,
            "comment": "ok",
            "favorite": 0,
            "name": "ind-1",
            "sex": "F",
            "age": "adult",
            "station_name": "station-a",
            "lat": 1.1,
            "long": 2.2,
            "station_survey_id": 1,
            "survey_name": "survey-a",
            "region_name": "region-a",
            "camera_name": "cam-a",
        }

        data = pd.DataFrame(
            [
                {"id": 1, "filepath": str(file_1), "relative_path": "s1/c1/a.jpg", **row_common},
                {"id": 2, "filepath": str(file_2), "relative_path": "s1/c1/b.jpg", **row_common},
            ]
        )

        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
        monkeypatch.setattr(import_thread, "save_roi_thumbnail", lambda *_: "roi-thumb.jpg")

        add_upload_calls = []
        original_add_upload = db.add_upload

        def _track_add_upload(path):
            add_upload_calls.append(path)
            return original_add_upload(path)

        monkeypatch.setattr(db, "add_upload", _track_add_upload)

        thread = import_thread.CSVMigrateThread(parent, data)
        thread.progress_update = SignalSpy()
        thread.error_update = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        thread.run()

        assert db.count("media") == 2
        assert db.count("roi") == 2
        assert len(add_upload_calls) == 1
        assert len(thread.base_dir_ref) == 1
        assert len(thread.station_ref) == 1
        assert len(thread.camera_ref) == 1
        assert len(thread.sequence_ref) == 1
        assert thread.error_update.calls == [([],)]
        assert len(thread.finished.calls) == 1

    def test_missing_file_is_skipped_and_added_to_errors(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")

        missing_path = tmp_path / "missing.jpg"
        data = pd.DataFrame(
            [
                {
                    "id": 1,
                    "frame": 0,
                    "bbox_x": 0.1,
                    "bbox_y": 0.2,
                    "bbox_w": 0.3,
                    "bbox_h": 0.4,
                    "viewpoint": 1,
                    "reviewed": 1,
                    "media_id": 1,
                    "individual_id": 1,
                    "emb": 1,
                    "base_dir_id": 1,
                    "relative_path": "missing.jpg",
                    "ext": ".jpg",
                    "timestamp": "2024-01-01 12:00:00",
                    "station_id": 1,
                    "sequence_id": 1,
                    "camera_id": 1,
                    "external_id": 1,
                    "comment": "c",
                    "favorite": 0,
                    "name": "n",
                    "sex": "F",
                    "age": "adult",
                    "filepath": str(missing_path),
                    "station_name": "st",
                    "lat": 1.0,
                    "long": 2.0,
                    "station_survey_id": 1,
                    "survey_name": "sv",
                    "region_name": "rg",
                    "camera_name": "cam",
                }
            ]
        )

        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
        monkeypatch.setattr(import_thread, "save_roi_thumbnail", lambda *_: "roi-thumb.jpg")

        thread = import_thread.CSVMigrateThread(parent, data)
        thread.error_update = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        thread.run()

        assert db.count("media") == 0
        assert db.count("roi") == 0
        assert thread.error_update.calls == [([(str(missing_path))],)]
        assert len(thread.finished.calls) == 1

    def test_interruption_stops_processing(self, tmp_db, null_logger, tmp_path):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        data = pd.DataFrame(columns=list(import_thread.CSVMigrateThread.EXPECTED_COLUMNS))
        thread = import_thread.CSVMigrateThread(parent, data)
        thread.error_update = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: True

        thread.run()

        assert db.count("media") == 0
        assert db.count("roi") == 0
        assert thread.error_update.calls == []
        assert thread.finished.calls == []


class TestCSVImportThread:
    def _selected_columns(self):
        return {
            "timestamp": "timestamp",
            "survey": "Default Survey",
            "region": "region",
            "station": "station",
            "lat": "lat",
            "long": "long",
            "camera": "camera",
            "sequence_id": "sequence_id",
            "external_id": "external_id",
            "comment": "comment",
            "viewpoint": "viewpoint",
            "individual": "individual",
            "sex": "sex",
            "age": "age",
            "favorite": "favorite",
        }

    def test_get_base_dir_finds_common_parent(self, tmp_db, null_logger, tmp_path):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        thread = import_thread.CSVImportThread(parent, pd.DataFrame().groupby(lambda _: 0), self._selected_columns())
        common = thread._get_base_dir(
            [
                str(tmp_path / "x" / "a.jpg"),
                str(tmp_path / "x" / "y" / "b.jpg"),
            ]
        )
        assert common.endswith(str(tmp_path / "x"))

    def test_run_groups_by_filepath_and_imports_old_bbox(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")

        image_path = tmp_path / "a" / "b" / "img.jpg"
        image_path.parent.mkdir(parents=True)
        image_path.write_bytes(b"img")

        df = pd.DataFrame(
            [
                {
                    "filepath": str(image_path),
                    "timestamp": "2024-01-01 10:00:00",
                    "station": "Station A",
                    "lat": "1.23",
                    "long": "2.34",
                    "camera": "Cam 1",
                    "sequence_id": 77,
                    "external_id": "123",
                    "comment": " comment ",
                    "viewpoint": "2",
                    "individual": "Jaguar-1",
                    "sex": "F",
                    "age": "adult",
                    "favorite": "1",
                    "frame": 4,
                    "bbox1": 0.1,
                    "bbox2": 0.2,
                    "bbox3": 0.3,
                    "bbox4": 0.4,
                },
                {
                    "filepath": str(image_path),
                    "timestamp": "2024-01-01 10:00:00",
                    "station": "Station A",
                    "lat": "1.23",
                    "long": "2.34",
                    "camera": "Cam 1",
                    "sequence_id": 77,
                    "external_id": "123",
                    "comment": " comment ",
                    "viewpoint": "2",
                    "individual": "Jaguar-1",
                    "sex": "F",
                    "age": "adult",
                    "favorite": "1",
                    "frame": 5,
                    "bbox1": 0.5,
                    "bbox2": 0.6,
                    "bbox3": 0.7,
                    "bbox4": 0.8,
                },
            ]
        )

        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
        monkeypatch.setattr(import_thread, "save_roi_thumbnail", lambda *_: "roi-thumb.jpg")
        grouped = df.groupby("filepath", sort=False)
        thread = import_thread.CSVImportThread(parent, grouped, self._selected_columns())
        thread.progress_update = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        thread.run()

        rois = db.select("roi", columns="bbox_x, bbox_y, bbox_w, bbox_h, frame")
        assert db.count("media") == 1
        assert db.count("roi") == 2
        assert rois[0][0:4] == (0.1, 0.2, 0.3, 0.4)
        assert rois[1][0:4] == (0.5, 0.6, 0.7, 0.8)
        assert len(thread.finished.calls) == 1

    def test_run_handles_new_bbox_and_none_nan_conversion(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")

        image_path = tmp_path / "aa" / "bb" / "img2.jpg"
        image_path.parent.mkdir(parents=True)
        image_path.write_bytes(b"img2")

        df = pd.DataFrame(
            [
                {
                    "filepath": str(image_path),
                    "timestamp": "2024-01-01 11:00:00",
                    "station": "Station B",
                    "lat": pd.NA,
                    "long": "NaN",
                    "camera": None,
                    "sequence_id": pd.NA,
                    "external_id": "nan",
                    "comment": pd.NA,
                    "viewpoint": pd.NA,
                    "individual": pd.NA,
                    "sex": pd.NA,
                    "age": pd.NA,
                    "favorite": pd.NA,
                    "bbox_x": 0.11,
                    "bbox_y": 0.22,
                    "bbox_w": 0.33,
                    "bbox_h": 0.44,
                }
            ]
        )

        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
        monkeypatch.setattr(import_thread, "save_roi_thumbnail", lambda *_: "roi-thumb.jpg")
        grouped = df.groupby("filepath", sort=False)
        thread = import_thread.CSVImportThread(parent, grouped, self._selected_columns())
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False
        thread.run()

        media = db.select("media", columns="camera_id, sequence_id, external_id, comment")
        roi = db.select("roi", columns="bbox_x, bbox_y, bbox_w, bbox_h, viewpoint, reviewed, favorite, individual_id")[0]
        assert media[0] == (None, None, None, None)
        assert roi[0:4] == (0.11, 0.22, 0.33, 0.44)
        assert roi[4:] == (None, 0, 0, None)
        assert len(thread.finished.calls) == 1

    def test_convert_helpers_handle_none_and_nan(self, tmp_db, null_logger, tmp_path):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        thread = import_thread.CSVImportThread(parent, pd.DataFrame().groupby(lambda _: 0), self._selected_columns())

        assert thread._convert_to_str(None) is None
        assert thread._convert_to_str(pd.NA) is None
        assert thread._convert_to_str(" a'b ") == "a''b"
        assert thread._convert_to_int("7") == 7
        assert thread._convert_to_int("abc") is None
        assert thread._convert_to_float("1.5") == pytest.approx(1.5)
        assert thread._convert_to_float("x") is None

    def test_interruption_prevents_finished_signal(self, tmp_db, null_logger, tmp_path):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        file_path = tmp_path / "im.jpg"
        file_path.write_bytes(b"1")
        df = pd.DataFrame([{"filepath": str(file_path)}])
        grouped = df.groupby("filepath", sort=False)
        thread = import_thread.CSVImportThread(parent, grouped, self._selected_columns())
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: True

        thread.run()

        assert thread.finished.calls == []


class TestFolderImportThread:
    def test_extracts_station_and_camera_from_filepath(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        base = tmp_path / "root"
        file_path = base / "stationA" / "cameraA" / "img.jpg"
        file_path.parent.mkdir(parents=True)
        file_path.write_bytes(b"x")

        parts = file_path.parts
        station_level = parts.index("stationA")
        camera_level = parts.index("cameraA")
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        data = pd.DataFrame([{"filepath": str(file_path), "datetime": "2024-01-01 12:00:00"}])
        thread = import_thread.FolderImportThread(parent, (1,), data, station_level=station_level, camera_level=camera_level)

        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False
        thread.run()

        station_name = db.select("station", columns="name", row_cond="name='stationA'")[0][0]
        camera_name = db.select("camera", columns="name", row_cond="name='cameraA'")[0][0]
        assert station_name == "stationA"
        assert camera_name == "cameraA"
        assert db.count("media") == 1
        assert len(thread.finished.calls) == 1

    def test_creates_default_station_when_station_level_zero(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        file_1 = tmp_path / "x1.jpg"
        file_2 = tmp_path / "x2.jpg"
        file_1.write_bytes(b"1")
        file_2.write_bytes(b"2")
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        data = pd.DataFrame(
            [
                {"filepath": str(file_1), "datetime": "2024-01-01 12:00:00"},
                {"filepath": str(file_2), "datetime": "2024-01-01 12:01:00"},
            ]
        )
        thread = import_thread.FolderImportThread(parent, (1,), data, station_level=0, camera_level=0)
        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
        thread.isInterruptionRequested = lambda: False
        thread.run()

        stations = db.select("station", columns="id", row_cond="name='Default Station'")
        assert len(stations) == 1
        assert db.count("media") == 2

    def test_interruption_skips_processing_but_still_finishes(self, tmp_db, null_logger, tmp_path):
        db, _ = tmp_db
        file_1 = tmp_path / "y1.jpg"
        file_1.write_bytes(b"1")
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        data = pd.DataFrame([{"filepath": str(file_1), "datetime": "2024-01-01 12:00:00"}])
        thread = import_thread.FolderImportThread(parent, (1,), data, station_level=0, camera_level=0)
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: True

        thread.run()

        assert db.count("media") == 0
        assert len(thread.finished.calls) == 1


class TestBasePathUpdateThread:
    def test_updates_base_dir_and_emits_progress_finished(self, tmp_db):
        db, _ = tmp_db
        base_id = db.add_upload("/old/path")
        thread = import_thread.BasePathUpdateThread(db, base_id, "/new/path")
        thread.progress_update = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        thread.run()

        updated = db.select("uploads", columns="base_dir", row_cond=f"id={base_id}")[0][0]
        assert updated == "/new/path"
        assert thread.progress_update.calls == [((1),)]
        assert len(thread.finished.calls) == 1

    def test_interruption_does_not_update_base_dir(self, tmp_db):
        db, _ = tmp_db
        base_id = db.add_upload("/old/path")
        thread = import_thread.BasePathUpdateThread(db, base_id, "/new/path")
        thread.progress_update = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: True

        thread.run()

        updated = db.select("uploads", columns="base_dir", row_cond=f"id={base_id}")[0][0]
        assert updated == "/old/path"
        assert thread.progress_update.calls == []
        assert len(thread.finished.calls) == 1
