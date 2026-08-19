# matchypatchy_package/tests/conftest.py
import pytest
import tempfile
from pathlib import Path
from matchypatchy.database.mpdb import MatchyPatchyDB
from matchypatchy.logging_config import setup_logger

@pytest.fixture
def temp_db():
    """Temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = setup_logger()
        db = MatchyPatchyDB(tmpdir, logger)
        yield db, Path(tmpdir)
        db.close()

@pytest.fixture
def mock_logger():
    return setup_logger(log_level="DEBUG")