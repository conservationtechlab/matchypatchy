"""
Pytest fixtures for MatchyPatchy database tests.

PyQt6 and cv2 are hard dependencies pulled in via matchypatchy's top-level
__init__.py but are not needed for database-layer tests.  We stub out those
modules here at collection time (module level) so that the database layer can
be imported without a display server or OpenCV installation.
"""
import sys
import types
import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest


class _MockModule(types.ModuleType):
    """A stub module whose attribute access always returns a fresh MagicMock."""
    def __getattr__(self, name: str):
        return MagicMock()


def _stub_gui_dependencies():
    """
    Stub out Qt and OpenCV modules before matchypatchy is imported so that
    the GUI-related packages do not cause ImportErrors in a headless environment.
    """
    stub_names = [
        "cv2",
        "PyQt6",
        "PyQt6.QtWidgets",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtMultimedia",
        "PyQt6.QtMultimediaWidgets",
        "PyQt6.QtTest",
    ]
    for name in stub_names:
        if name not in sys.modules:
            sys.modules[name] = _MockModule(name)


_stub_gui_dependencies()

from matchypatchy.database.mpdb import MatchyPatchyDB  # noqa: E402


@pytest.fixture
def null_logger():
    """Return a silent logger suitable for testing."""
    logger = logging.getLogger("matchypatchy.test")
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


@pytest.fixture
def tmp_db(tmp_path, null_logger):
    """
    Create a fresh MatchyPatchyDB in a temporary directory.

    The fixture yields the MatchyPatchyDB instance and the directory Path.
    The database is closed and the temporary directory is cleaned up
    automatically when the test finishes.
    """
    db = MatchyPatchyDB(str(tmp_path), null_logger)
    yield db, tmp_path
    db.close()


@pytest.fixture
def populated_db(tmp_db):
    """
    A MatchyPatchyDB pre-populated with one region, survey, station,
    individual, and one media + ROI entry for use in tests that need
    existing data without caring about the insertion details.
    """
    db, path = tmp_db

    # The constructor already created a "Default Region" (id=1) and
    # "Default Survey" (id=1).  Add a dedicated station and media.
    station_id = db.add_station("Test Station", 1.0, 2.0, 1)
    individual_id = db.add_individual("Ind-1", "M", "Adult")
    media_id = db.add_media(
        filepath="/tmp/img001.jpg",
        sha256="abc123def456" * 4,
        ext=".jpg",
        timestamp="2024-01-01 12:00:00",
        station_id=station_id,
    )
    roi_id = db.add_roi(
        media_id=media_id,
        frame=0,
        bbox_x=0.1, bbox_y=0.2, bbox_w=0.3, bbox_h=0.4,
        reviewed=0,
        favorite=0,
        individual_id=individual_id,
    )

    yield db, path, {
        "region_id": 1,
        "survey_id": 1,
        "station_id": station_id,
        "individual_id": individual_id,
        "media_id": media_id,
        "roi_id": roi_id,
    }
