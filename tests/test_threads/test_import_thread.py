"""Tests for matchypatchy thread workers in import_thread.py."""
import threading
import time
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

    def test_two_rois_on_one_image(self, tmp_db, null_logger, tmp_path, monkeypatch):
        """The second roi of an image reuses the media added for the first"""
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        image = tmp_path / "import" / "s1" / "a.jpg"
        image.parent.mkdir(parents=True)
        image.write_bytes(b"a")
        row = {"frame": 0, "bbox_x": 0.1, "bbox_y": 0.2, "bbox_w": 0.3, "bbox_h": 0.4, "viewpoint": 1,
               "reviewed": 1, "media_id": 1, "individual_id": None, "emb": 1, "base_dir_id": 7, "ext": ".jpg",
               "timestamp": "2024-01-01 12:00:00", "station_id": 10, "sequence_id": 11, "camera_id": None,
               "external_id": None, "comment": None, "favorite": 0, "name": None, "sex": None,
               "station_name": "station-a", "lat": None, "long": None, "station_survey_id": 1,
               "survey_name": "survey-a", "region_name": "region-a", "camera_name": None,
               "filepath": str(image), "relative_path": "s1/a.jpg"}
        data = pd.DataFrame([{"id": 1, **row}, {"id": 2, **row, "bbox_x": 0.5}])

        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
        monkeypatch.setattr(import_thread, "save_roi_thumbnail", lambda *_: "roi-thumb.jpg")
        thread = import_thread.CSVMigrateThread(parent, data)
        thread.progress_update = SignalSpy()
        thread.error_update = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        thread.run()

        assert db.count("media") == 1
        assert db.count("roi") == 2
        assert {r[0] for r in db.select("roi", "media_id")} == {db.select("media", "id")[0][0]}

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
            "survey": None,  # None means use active_survey
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
            "favorite": "favorite",
        }

    def test_get_base_dir_finds_common_parent(self, tmp_db, null_logger, tmp_path):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        thread = import_thread.CSVImportThread(parent, pd.DataFrame().groupby(lambda _: 0), self._selected_columns(), "Default Survey")
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
        thread = import_thread.CSVImportThread(parent, grouped, self._selected_columns(), "Default Survey")
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
        thread = import_thread.CSVImportThread(parent, grouped, self._selected_columns(), "Default Survey")
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False
        thread.run()

        media = db.select("media", columns="camera_id, sequence_id, external_id, comment")
        roi = db.select("roi", columns="bbox_x, bbox_y, bbox_w, bbox_h, viewpoint, reviewed, favorite, individual_id")[0]
        assert media[0] == (None, None, None, None)
        assert roi[0:4] == (0.11, 0.22, 0.33, 0.44)
        assert roi[4:] == (None, 0, 0, None)
        assert len(thread.finished.calls) == 1

    def test_rerun_skips_existing_rois(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")

        image_path = tmp_path / "r" / "img.jpg"
        image_path.parent.mkdir(parents=True)
        image_path.write_bytes(b"img")

        def _row(frame, bbox):
            return {"filepath": str(image_path), "timestamp": "2024-01-01 10:00:00",
                    "station": "Station A", "lat": pd.NA, "long": pd.NA, "camera": pd.NA,
                    "sequence_id": pd.NA, "external_id": pd.NA, "comment": pd.NA,
                    "viewpoint": pd.NA, "individual": pd.NA, "sex": pd.NA, "favorite": pd.NA,
                    "frame": frame, "bbox_x": bbox[0], "bbox_y": bbox[1], "bbox_w": bbox[2], "bbox_h": bbox[3]}

        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
        monkeypatch.setattr(import_thread, "save_roi_thumbnail", lambda *_: "roi-thumb.jpg")

        def _run(df):
            thread = import_thread.CSVImportThread(parent, df.groupby("filepath", sort=False),
                                                   self._selected_columns(), "Default Survey")
            thread.progress_update = SignalSpy()
            thread.finished = SignalSpy()
            thread.isInterruptionRequested = lambda: False
            thread.run()
            return thread

        # first (partial) import
        _run(pd.DataFrame([_row(0, (0.123456, 0.2, 0.3, 0.4))]))
        assert db.count("roi") == 1

        # resumed import with full csv: existing roi skipped, new one added
        thread = _run(pd.DataFrame([_row(0, (0.123456, 0.2, 0.3, 0.4)),
                                    _row(1, (0.5, 0.6, 0.7, 0.8))]))
        assert db.count("media") == 1
        assert db.count("roi") == 2
        assert thread.progress_update.calls[-1] == (2,)

    def test_rerun_without_bboxes_adds_only_missing_rois(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")

        image_path = tmp_path / "e" / "img.jpg"
        image_path.parent.mkdir(parents=True)
        image_path.write_bytes(b"img")

        row = {"filepath": str(image_path), "timestamp": "2024-01-01 10:00:00",
               "station": "Station A", "lat": pd.NA, "long": pd.NA, "camera": pd.NA,
               "sequence_id": pd.NA, "external_id": pd.NA, "comment": pd.NA,
               "viewpoint": pd.NA, "individual": pd.NA, "sex": pd.NA, "favorite": pd.NA}

        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")

        def _run(n_rows):
            df = pd.DataFrame([row] * n_rows)
            thread = import_thread.CSVImportThread(parent, df.groupby("filepath", sort=False),
                                                   self._selected_columns(), "Default Survey")
            thread.finished = SignalSpy()
            thread.isInterruptionRequested = lambda: False
            thread.run()

        # interrupted partway through the image's rows
        _run(2)
        assert db.count("roi") == 2

        # resume: the two existing empty rois cover two rows, the third is added
        _run(3)
        assert db.count("roi") == 3

        # running again adds nothing
        _run(3)
        assert db.count("roi") == 3

    def test_convert_helpers_handle_none_and_nan(self, tmp_db, null_logger, tmp_path):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        thread = import_thread.CSVImportThread(parent, pd.DataFrame().groupby(lambda _: 0), self._selected_columns(), "Default Survey")

        assert thread._convert_to_str(None) is None
        assert thread._convert_to_str(pd.NA) is None
        assert thread._convert_to_str(" a'b ") == "a'b"
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
        thread = import_thread.CSVImportThread(parent, grouped, self._selected_columns(), "Default Survey")
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

    def test_shallower_files_fall_back_to_default_station_and_no_camera(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        base = tmp_path / "root"
        deep = base / "stationA" / "cameraA" / "deep.jpg"
        no_camera = base / "stationA" / "no_camera.jpg"
        no_station = base / "no_station.jpg"
        deep.parent.mkdir(parents=True)
        for n, path in enumerate((deep, no_camera, no_station)):
            path.write_bytes(bytes([n]))

        # levels are picked from the first, deepest file
        parts = deep.parts
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        data = pd.DataFrame([{"filepath": str(p), "datetime": "2024-01-01 12:00:00"}
                             for p in (deep, no_camera, no_station)])
        thread = import_thread.FolderImportThread(parent, (1,), data, station_level=parts.index("stationA"),
                                                  camera_level=parts.index("cameraA"))
        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
        thread.finished = SignalSpy()
        thread.import_failed = SignalSpy()
        thread.isInterruptionRequested = lambda: False
        thread.run()

        assert thread.import_failed.calls == []
        assert sorted(db.select("station", columns="name")) == [("Default Station",), ("stationA",)]
        assert db.select("camera", columns="name") == [("cameraA",)]
        media = db.select("media m JOIN station s ON m.station_id = s.id",
                          columns="m.relative_path, s.name, m.camera_id")
        assert sorted(media) == [("no_station.jpg", "Default Station", None),
                                 (str(Path("stationA") / "cameraA" / "deep.jpg"), "stationA", 1),
                                 (str(Path("stationA") / "no_camera.jpg"), "stationA", None)]

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


def _csv_import(db, parent, rows, selected_columns, monkeypatch):
    """Run a CSVImportThread over rows as they would read from a csv (blank cells are NaN)"""
    monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
    monkeypatch.setattr(import_thread, "save_roi_thumbnail", lambda *_: "roi-thumb.jpg")
    df = pd.DataFrame(rows)
    thread = import_thread.CSVImportThread(parent, df.groupby("filepath", sort=False),
                                           selected_columns, "Default Survey")
    thread.finished = SignalSpy()
    thread.import_failed = SignalSpy()
    thread.isInterruptionRequested = lambda: False
    thread.run()
    return thread


class TestCSVImportBlankCells:
    def _selected_columns(self):
        return TestCSVImportThread._selected_columns(None)

    def _image(self, tmp_path, name):
        path = tmp_path / "imgs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode())
        return str(path)

    def test_blank_camera_adds_no_camera(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        rows = [{"filepath": self._image(tmp_path, "a.jpg"), "timestamp": "2024-01-01 10:00:00",
                 "station": "Station A", "camera": float("nan")}]

        _csv_import(db, parent, rows, self._selected_columns(), monkeypatch)

        assert db.count("camera") == 0
        assert db.select("media", columns="camera_id") == [(None,)]

    def test_apostrophes_are_stored_as_typed(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        rows = [{"filepath": self._image(tmp_path, "a.jpg"), "timestamp": "2024-01-01 10:00:00",
                 "station": "O'Brien Creek", "camera": "Cam 'B'", "individual": "D'Artagnan",
                 "comment": "don't"}]

        _csv_import(db, parent, rows, self._selected_columns(), monkeypatch)

        assert db.select("station", columns="name") == [("O'Brien Creek",)]
        assert db.select("camera", columns="name") == [("Cam 'B'",)]
        assert db.select("individual", columns="name") == [("D'Artagnan",)]
        assert db.select("media", columns="comment") == [("don't",)]

    def test_blank_bbox_and_frame_import_as_boxless_roi(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        nan = float("nan")
        rows = [{"filepath": self._image(tmp_path, "a.jpg"), "timestamp": "2024-01-01 10:00:00",
                 "station": "Station A", "frame": 3, "bbox_x": 0.1, "bbox_y": 0.2, "bbox_w": 0.3, "bbox_h": 0.4},
                {"filepath": self._image(tmp_path, "b.jpg"), "timestamp": "2024-01-01 10:00:00",
                 "station": "Station A", "frame": nan, "bbox_x": nan, "bbox_y": nan, "bbox_w": nan, "bbox_h": nan}]

        thread = _csv_import(db, parent, rows, self._selected_columns(), monkeypatch)

        assert thread.import_failed.calls == []
        assert db.select("roi", columns="frame, bbox_x, bbox_y, bbox_w, bbox_h") == [
            (3, 0.1, 0.2, 0.3, 0.4), (0, -1, -1, -1, -1)]

    def test_same_station_and_camera_names_in_two_surveys_stay_separate(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        selected = {**self._selected_columns(), "survey": "survey"}
        rows = [{"filepath": self._image(tmp_path, f"{survey}.jpg"), "timestamp": "2024-01-01 10:00:00",
                 "survey": survey, "station": "Site01", "camera": "Cam1"}
                for survey in ("Survey 2023", "Survey 2024")]

        _csv_import(db, parent, rows, selected, monkeypatch)

        stations = db.select("station", columns="id, survey_id")
        cameras = db.select("camera", columns="station_id")
        assert len(stations) == 2
        assert len({survey_id for _, survey_id in stations}) == 2
        assert sorted(c[0] for c in cameras) == sorted(s[0] for s in stations)


class TestFolderImportLookups:
    def _import(self, db, parent, file_path, survey_id, monkeypatch):
        parts = file_path.parts
        data = pd.DataFrame([{"filepath": str(file_path), "datetime": "2024-01-01 12:00:00"}])
        thread = import_thread.FolderImportThread(parent, (survey_id,), data,
                                                  station_level=parts.index("Site01"),
                                                  camera_level=parts.index("Cam1"))
        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False
        thread.run()

    def test_same_station_name_in_a_second_survey_gets_its_own_station(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        survey_1 = db.add_survey("Survey 2023", None, None, None)
        survey_2 = db.add_survey("Survey 2024", None, None, None)
        for year, survey_id in (("2023", survey_1), ("2024", survey_2)):
            file_path = tmp_path / year / "Site01" / "Cam1" / f"{year}.jpg"
            file_path.parent.mkdir(parents=True)
            file_path.write_bytes(year.encode())
            self._import(db, parent, file_path, survey_id, monkeypatch)

        stations = db.select("station", columns="id, survey_id")
        assert sorted(survey_id for _, survey_id in stations) == sorted([survey_1, survey_2])
        assert db.count("camera") == 2

    def test_reimport_does_not_regenerate_thumbnails(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        file_path = tmp_path / "2023" / "Site01" / "Cam1" / "a.jpg"
        file_path.parent.mkdir(parents=True)
        file_path.write_bytes(b"a")
        self._import(db, parent, file_path, 1, monkeypatch)

        saved = []
        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *a: saved.append(a) or "t.jpg")
        data = pd.DataFrame([{"filepath": str(file_path), "datetime": "2024-01-01 12:00:00"}])
        parts = file_path.parts
        thread = import_thread.FolderImportThread(parent, (1,), data,
                                                  station_level=parts.index("Site01"),
                                                  camera_level=parts.index("Cam1"))
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False
        thread.run()

        assert saved == []
        assert db.count("media") == 1


class TestImportFailuresAreReported:
    """An exception escaping QThread.run aborts the app, so it must be reported instead"""

    def _boom(self, *args, **kwargs):
        raise RuntimeError("boom")

    def test_folder_import(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        file_path = tmp_path / "a.jpg"
        file_path.write_bytes(b"a")
        data = pd.DataFrame([{"filepath": str(file_path), "datetime": "2024-01-01 12:00:00"}])
        thread = import_thread.FolderImportThread(parent, (1,), data, station_level=0, camera_level=0)
        monkeypatch.setattr(import_thread, "get_sha256", self._boom)
        thread.import_failed = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        thread.run()

        assert thread.import_failed.calls == [("boom",)]
        assert thread.finished.calls == []

    def test_thumbnail_failure_rolls_back_import(self, tmp_db, null_logger, tmp_path, monkeypatch):
        """An exception on a thumbnail worker reaches the import thread and fails the import"""
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        file_path = tmp_path / "a.jpg"
        file_path.write_bytes(b"a")
        data = pd.DataFrame([{"filepath": str(file_path), "datetime": "2024-01-01 12:00:00"}])
        thread = import_thread.FolderImportThread(parent, (1,), data, station_level=0, camera_level=0)
        monkeypatch.setattr(import_thread, "save_media_thumbnail", self._boom)
        thread.import_failed = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        thread.run()

        assert thread.import_failed.calls == [("boom",)]
        assert db.count("media") == 0

    def test_csv_migrate(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        row = {column: None for column in import_thread.CSVMigrateThread.EXPECTED_COLUMNS}
        thread = import_thread.CSVMigrateThread(parent, pd.DataFrame([row]))
        monkeypatch.setattr(thread, "survey", self._boom)
        thread.import_failed = SignalSpy()
        thread.error_update = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        thread.run()

        assert thread.import_failed.calls == [("boom",)]
        assert thread.error_update.calls == []


class TestImportDetectionDone:
    """Imported files with a boxed roi are already detected, box-less or roi-less ones still need it"""

    def _image(self, tmp_path, name):
        path = tmp_path / "imgs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode())
        return path

    def _detection_done(self, db):
        return {Path(path).name: done for path, done in db.select("media", columns="relative_path, detection_done")}

    def test_csv_import(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        nan = float("nan")
        rows = [{"filepath": str(self._image(tmp_path, name)), "timestamp": "2024-01-01 10:00:00",
                 "station": "Station A", "bbox_x": box, "bbox_y": box, "bbox_w": box, "bbox_h": box}
                for name, box in (("boxed.jpg", 0.2), ("boxless.jpg", nan))]

        _csv_import(db, parent, rows, TestCSVImportThread._selected_columns(None), monkeypatch)

        assert self._detection_done(db) == {"boxed.jpg": 1, "boxless.jpg": 0}

    def test_csv_migrate(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
        monkeypatch.setattr(import_thread, "save_roi_thumbnail", lambda *_: "roi-thumb.jpg")
        rows = []
        for n, (name, box) in enumerate((("boxed.jpg", 0.2), ("boxless.jpg", -1))):
            path = self._image(tmp_path, name)
            row = {column: None for column in import_thread.CSVMigrateThread.EXPECTED_COLUMNS}
            row.update({"id": n, "media_id": n, "frame": 0, "bbox_x": box, "bbox_y": box, "bbox_w": box,
                        "bbox_h": box, "base_dir_id": 1, "filepath": str(path), "relative_path": name,
                        "ext": ".jpg", "timestamp": "2024-01-01 12:00:00", "station_id": 1,
                        "station_name": "Station A", "survey_name": "Survey A"})
            rows.append(row)
        thread = import_thread.CSVMigrateThread(parent, pd.DataFrame(rows))
        thread.progress_update = SignalSpy()
        thread.error_update = SignalSpy()
        thread.import_failed = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        thread.run()

        assert thread.import_failed.calls == []
        assert self._detection_done(db) == {"boxed.jpg": 1, "boxless.jpg": 0}


def _migrate_row(path, n, box=0.2, **overrides):
    """An exported roi row for path, with a square bbox of size box"""
    row = {column: None for column in import_thread.CSVMigrateThread.EXPECTED_COLUMNS}
    row.update({"id": n, "media_id": 1, "frame": 0, "bbox_x": box, "bbox_y": box, "bbox_w": box,
                "bbox_h": box, "base_dir_id": 1, "filepath": str(path), "relative_path": path.name,
                "ext": ".jpg", "timestamp": "2024-01-01 12:00:00", "station_id": 1,
                "station_name": "Station A", "survey_name": "Survey A"})
    row.update(overrides)
    return row


class TestCSVMigrateRerun:
    """Migrating into a project that already has some of the files"""

    _row = staticmethod(_migrate_row)

    def _migrate(self, db, parent, rows):
        thread = import_thread.CSVMigrateThread(parent, pd.DataFrame(rows))
        thread.progress_update = SignalSpy()
        thread.error_update = SignalSpy()
        thread.import_failed = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False
        thread.run()
        assert thread.import_failed.calls == []
        return thread

    @pytest.fixture
    def image(self, tmp_path, monkeypatch):
        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
        monkeypatch.setattr(import_thread, "save_roi_thumbnail", lambda *_: "roi-thumb.jpg")
        path = tmp_path / "imgs" / "a.jpg"
        path.parent.mkdir()
        path.write_bytes(b"a")
        return path

    def test_existing_upload_is_reused(self, tmp_db, null_logger, tmp_path, image):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        upload_id = db.add_upload(str(image.parent))

        self._migrate(db, parent, [self._row(image, 0)])

        assert db.count("uploads") == 1
        assert db.select("media", columns="base_dir_id") == [(upload_id,)]

    def test_media_thumbnail_saved_once_per_new_file(self, tmp_db, null_logger, tmp_path, image, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        saved = []
        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *a: saved.append(a) or "t.jpg")

        self._migrate(db, parent, [self._row(image, 0), self._row(image, 1, box=0.5)])
        assert len(saved) == 1

        # migrating the same file again adds no thumbnail
        self._migrate(db, parent, [self._row(image, 0)])
        assert len(saved) == 1
        assert db.count("media_thumbnails") == 1

    def test_boxless_roi_gets_no_thumbnail(self, tmp_db, null_logger, tmp_path, image, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        saved = []
        monkeypatch.setattr(import_thread, "save_roi_thumbnail", lambda *a: saved.append(a) or "t.jpg")

        self._migrate(db, parent, [self._row(image, 0, box=-1)])

        assert db.count("roi") == 1
        assert saved == []
        assert db.count("roi_thumbnails") == 0

    def test_rerun_adds_only_missing_rois(self, tmp_db, null_logger, tmp_path, image):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        self._migrate(db, parent, [self._row(image, 0), self._row(image, 1, box=-1)])

        # resuming with the same rows plus one new box and one more box-less roi
        rows = [self._row(image, 0), self._row(image, 1, box=-1),
                self._row(image, 2, box=0.5), self._row(image, 3, box=-1)]
        thread = self._migrate(db, parent, rows)

        assert db.count("roi") == 4
        assert thread.progress_update.calls[-1] == (4,)

    def test_individual_is_looked_up_once(self, tmp_db, null_logger, tmp_path, image, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        tables = []
        original_select = db.select
        monkeypatch.setattr(db, "select", lambda table, *a, **k: tables.append(table) or original_select(table, *a, **k))

        self._migrate(db, parent, [self._row(image, n, box=0.1 * (n + 1), individual_id=5, name="Lion")
                                   for n in range(3)])

        assert tables.count("individual") == 1
        assert db.select("roi", columns="individual_id") == [(1,)] * 3

    def test_survey_is_looked_up_once(self, tmp_db, null_logger, tmp_path, image, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        tables = []
        original_select = db.select
        monkeypatch.setattr(db, "select", lambda table, *a, **k: tables.append(table) or original_select(table, *a, **k))

        self._migrate(db, parent, [self._row(image, n, box=0.1 * (n + 1)) for n in range(3)])

        assert tables.count("survey") == 1


class CommitCounter:
    """Wraps a sqlite connection, counting commits"""
    def __init__(self, connection):
        self._connection = connection
        self.commits = 0

    def commit(self):
        self.commits += 1
        self._connection.commit()

    def __getattr__(self, name):
        return getattr(self._connection, name)


class TestFolderImportCaching:
    def test_station_and_camera_are_looked_up_once(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        paths = []
        for name in ("a.jpg", "b.jpg", "c.jpg"):
            path = tmp_path / "Site01" / "Cam1" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
            paths.append(str(path))
        data = pd.DataFrame({"filepath": paths, "datetime": ["2024-01-01 12:00:00"] * 3})
        parts = Path(paths[0]).parts
        thread = import_thread.FolderImportThread(parent, (1,), data,
                                                  station_level=parts.index("Site01"),
                                                  camera_level=parts.index("Cam1"))
        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
        tables = []
        original_select = db.select
        monkeypatch.setattr(db, "select", lambda table, *a, **k: tables.append(table) or original_select(table, *a, **k))
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        thread.run()

        assert db.count("media") == 3
        assert tables.count("station") == 1
        assert tables.count("camera") == 1

    def test_commits_and_progress_are_batched(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        paths = []
        for n in range(12):
            path = tmp_path / f"{n}.jpg"
            path.write_bytes(str(n).encode())
            paths.append(str(path))
        data = pd.DataFrame({"filepath": paths, "datetime": ["2024-01-01 12:00:00"] * 12})
        thread = import_thread.FolderImportThread(parent, (1,), data, station_level=0, camera_level=0)
        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
        # no interval passes during the import, so only the setup rows and the final commit commit
        monkeypatch.setattr(thread, "COMMIT_INTERVAL", 3600)
        connection = CommitCounter(db.db)
        monkeypatch.setattr(db.local, "db", connection)
        thread.progress_update = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        thread.run()

        assert db.count("media") == 12
        assert thread.progress_update.calls == [(10,), (12,)]
        assert connection.commits < 12


class TestCSVMigrateInsertFailures:
    def test_failed_station_insert_is_reported(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        image = tmp_path / "a.jpg"
        image.write_bytes(b"a")
        row = _migrate_row(image, 0)
        monkeypatch.setattr(db, "add_station", lambda *_: None)
        thread = import_thread.CSVMigrateThread(parent, pd.DataFrame([row]))
        thread.import_failed = SignalSpy()
        thread.error_update = SignalSpy()
        thread.finished = SignalSpy()
        thread.isInterruptionRequested = lambda: False

        thread.run()

        assert len(thread.import_failed.calls) == 1
        assert thread.import_failed.calls[0][0].startswith("Failed to add station 'Station A'")
        assert db.count("media") == 0


class TestCSVMigrateInterruption:
    def test_interruption_stops_the_loop_and_keeps_finished_rows(self, tmp_db, null_logger, tmp_path, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
        monkeypatch.setattr(import_thread, "save_roi_thumbnail", lambda *_: "roi-thumb.jpg")
        image = tmp_path / "a.jpg"
        image.write_bytes(b"a")
        rows = [_migrate_row(image, n, box=0.1 * (n + 1)) for n in range(5)]
        thread = import_thread.CSVMigrateThread(parent, pd.DataFrame(rows))
        thread.progress_update = SignalSpy()
        thread.error_update = SignalSpy()
        thread.finished = SignalSpy()
        checks = []
        # cancel after the first row
        thread.isInterruptionRequested = lambda: checks.append(None) or len(checks) > 1

        thread.run()

        assert db.count("roi") == 1
        # checked once per row until cancelled, then once more before reporting
        assert len(checks) == 3
        assert thread.finished.calls == []


class TestFileReplacedAtSamePath:
    """A file already in the project is replaced by one with new content at the same path"""

    @pytest.fixture
    def images(self, tmp_path, monkeypatch):
        monkeypatch.setattr(import_thread, "save_media_thumbnail", lambda *_: "media-thumb.jpg")
        monkeypatch.setattr(import_thread, "save_roi_thumbnail", lambda *_: "roi-thumb.jpg")
        a = tmp_path / "imgs" / "a.jpg"
        b = tmp_path / "imgs" / "b.jpg"
        a.parent.mkdir()
        a.write_bytes(b"old a")
        b.write_bytes(b"b")
        return a, b

    def test_csv_import_skips_the_file(self, tmp_db, null_logger, tmp_path, images, monkeypatch):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        a, b = images
        selected = TestCSVImportThread._selected_columns(None)

        def _row(path, box):
            return {"filepath": str(path), "timestamp": "2024-01-01 10:00:00", "station": "Station A",
                    "bbox_x": box, "bbox_y": box, "bbox_w": box, "bbox_h": box}

        _csv_import(db, parent, [_row(a, 0.1)], selected, monkeypatch)
        a.write_bytes(b"new a")
        thread = _csv_import(db, parent, [_row(a, 0.2), _row(b, 0.3)], selected, monkeypatch)

        assert thread.import_failed.calls == []
        assert db.select("media", columns="relative_path") == [("a.jpg",), ("b.jpg",)]
        # the new file's roi isn't attached to the old file
        assert db.select("roi", columns="media_id, bbox_x") == [(1, 0.1), (2, 0.3)]

    def test_csv_migrate_reports_the_file(self, tmp_db, null_logger, tmp_path, images):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        a, b = images

        def _migrate(rows):
            thread = import_thread.CSVMigrateThread(parent, pd.DataFrame(rows))
            thread.progress_update = SignalSpy()
            thread.error_update = SignalSpy()
            thread.import_failed = SignalSpy()
            thread.finished = SignalSpy()
            thread.isInterruptionRequested = lambda: False
            thread.run()
            return thread

        _migrate([_migrate_row(a, 0, box=0.1)])
        a.write_bytes(b"new a")
        # two rois of the replaced file, then a new file
        thread = _migrate([_migrate_row(a, 0, box=0.2), _migrate_row(a, 1, box=0.3),
                           _migrate_row(b, 2, box=0.4, media_id=2)])

        assert thread.import_failed.calls == []
        assert thread.error_update.calls == [([str(a)],)]
        assert db.select("media", columns="relative_path") == [("a.jpg",), ("b.jpg",)]
        assert db.select("roi", columns="media_id, bbox_x") == [(1, 0.1), (2, 0.4)]


class FakeThumbnailDB:
    """Records add_thumbnail calls, noting which thread made them"""
    def __init__(self):
        self.rows = []
        self.threads = set()

    def add_thumbnail(self, table, fid, filepath, commit=True):
        self.threads.add(threading.get_ident())
        self.rows.append((table, fid, filepath))


class TestThumbnailQueue:
    def test_rows_recorded_in_order_from_calling_thread(self):
        db = FakeThumbnailDB()
        queue = import_thread.ThumbnailQueue(db, workers=4)
        for fid in range(50):
            # later work finishes first, rows must still be in order
            queue.add("media", fid, lambda n: time.sleep((50 - n) / 10000) or f"{n}.jpg", fid)
        queue.finish()
        queue.close()

        assert db.rows == [("media", fid, f"{fid}.jpg") for fid in range(50)]
        assert db.threads == {threading.get_ident()}

    def test_pending_work_is_bounded(self):
        db = FakeThumbnailDB()
        queue = import_thread.ThumbnailQueue(db, workers=2)
        for fid in range(20):
            queue.add("roi", fid, str, fid)
            assert len(queue.pending) <= 2 * queue.PENDING_PER_WORKER
        queue.finish()
        queue.close()
        assert len(db.rows) == 20

    def test_worker_exception_raised_on_record(self):
        def fail():
            raise RuntimeError("bad image")

        queue = import_thread.ThumbnailQueue(FakeThumbnailDB(), workers=1)
        queue.add("media", 1, fail)
        with pytest.raises(RuntimeError, match="bad image"):
            queue.finish()
        queue.close()

    def test_work_runs_in_parallel(self):
        barrier = threading.Barrier(3, timeout=5)
        queue = import_thread.ThumbnailQueue(FakeThumbnailDB(), workers=3)
        for fid in range(3):
            # each worker waits for the other two, which deadlocks (and times out) if run one at a time
            queue.add("media", fid, lambda: barrier.wait() and "t.jpg")
        queue.finish()
        queue.close()


class TestCSVImportFiles:
    """_files must give what iterating the groupby gave, it replaces that loop"""

    def _data(self):
        return pd.DataFrame({
            "filepath": ["c.jpg", "a.jpg", "c.jpg", None, "b.jpg", "a.jpg"],
            "station": ["S1", "S2", "S1", "S3", pd.NA, "S2"],
            "frame": [0, 1, 2, 3, 4, 5],
            "bbox_x": [0.1, float("nan"), 0.3, 0.4, 0.5, 0.6],
            "timestamp": pd.to_datetime(["2024-01-01"] * 6),
        })

    def _expected(self, grouped):
        return [(filepath, group.head(1).to_dict(orient="records")[0], list(group.itertuples(index=False)))
                for filepath, group in grouped]

    @pytest.mark.parametrize("sort", [True, False])
    def test_matches_groupby(self, tmp_db, null_logger, tmp_path, sort):
        db, _ = tmp_db
        parent = _make_parent(db, null_logger, tmp_path / "thumbs")
        grouped = self._data().groupby("filepath", sort=sort)
        thread = import_thread.CSVImportThread(parent, grouped, {}, "Default Survey")

        files = thread._files()

        expected = self._expected(grouped)
        assert [f[0] for f in files] == [e[0] for e in expected]
        for (_, exemplar, rois), (_, expected_exemplar, expected_rois) in zip(files, expected):
            # compare as strings so nan == nan
            assert {k: str(v) for k, v in exemplar.items()} == {k: str(v) for k, v in expected_exemplar.items()}
            assert [str(r) for r in rois] == [str(r) for r in expected_rois]
