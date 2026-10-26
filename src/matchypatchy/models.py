"""
Functions for managing ML models

"""
import os
import sys
import tempfile
import httpx
import yaml
import logging
from pathlib import Path

from matchypatchy.config import asset_path


logger = logging.getLogger(__name__)

MODELS_YML_URL = "https://sandiegozoo.box.com/shared/static/8o59iqmvjfic9btuarijfk30oocr5xkf.yml"


def user_data_dir():
    """Return the user data directory for storing models.yml."""
    # macOS
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/MatchyPatchy"
    # Windows
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "MatchyPatchy"
    # Linux and other Unix-like systems
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "matchypatchy"


def _read_yml(path):
    """Parse a models.yml; return a dict, or None if missing or invalid."""
    if not path.exists():
        logger.debug("%s not found", path)
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Could not read %s: %s", path, e)
        return None
    return data if isinstance(data, dict) else None


def update_model_yml():
    """Download the latest models.yml from the remote URL and save it locally."""
    dest = user_data_dir() / "models.yml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        r = httpx.get(MODELS_YML_URL, timeout=10, follow_redirects=True)
        r.raise_for_status()
        if not isinstance(yaml.safe_load(r.content), dict):
            raise ValueError("downloaded file is not a YAML mapping")

        fd, tmp = tempfile.mkstemp(dir=dest.parent, suffix=".tmp")
        with os.fdopen(fd, "wb") as f:
            f.write(r.content)
        os.replace(tmp, dest)
        tmp = None
        return True
    except Exception as e:
        logger.warning("models.yml update failed, using existing copy: %s", e)
        return False
    finally:
        if tmp:
            Path(tmp).unlink(missing_ok=True)

def load_yml():
    """Return the user's downloaded models.yml if valid, else the bundled one."""
    for path in (user_data_dir() / "models.yml", asset_path("models.yml")):
        data = _read_yml(path)
        if data:
            return data
    raise RuntimeError("No valid models.yml found (user or bundled)")


def load_model(key=None):
    """Return the full models config, or a specific key."""
    cfg = load_yml()
    return cfg[key] if key else cfg


def is_valid_reid_model(basename):
    """Checks if given basename is a valid reid model"""
    models = ('REID_MODELS')
    if basename in models:
        return True
    else:
        return False


def _as_list(value):
    """models.yml lists file names / urls, a single one may be a plain string"""
    return [value] if isinstance(value, str) else list(value)


def get_path(ML_DIR, key):
    """
    Path to the ML model's main (first) file in ML_DIR, None if not downloaded

    A model is only usable when all of its files are present (eg. a .onnx and
    its .onnx.data), so an interrupted download doesn't count as downloaded
    """
    if key is None:
        return None
    MODELS = load_model('MODELS')
    paths = [Path(ML_DIR) / name for name in _as_list(MODELS[key][0])]
    if paths and all(path.exists() for path in paths):
        return paths[0]
    return None


def delete(ML_DIR, key):
    """Deletes ML model from ML_DIR"""
    path = get_path(ML_DIR, key)
    if path:
        path.unlink()


# ==============================================================================
# VIEWPOINT
# ==============================================================================

# Compare view viewpoint toggle positions
VIEWPOINT_TOGGLE = {0: 'Left', 1: 'Any', 2: 'Right'}


def viewpoint_value(label):
    """
    Stored viewpoint value for a viewpoint label (eg. 'Left'), None if not a model class

    Stored values are viewpoint model classes, labelled in models.yml VIEWPOINTS
    (eg. '0': Left, '1': Right), so filtering by side must go through the labels
    """
    for value, name in load_model('VIEWPOINTS').items():
        if name == label and value.isdigit():
            return int(value)
    return None


def toggle_viewpoint_value(selected):
    """Stored viewpoint value for a compare view toggle position, None for Any"""
    return viewpoint_value(VIEWPOINT_TOGGLE.get(selected))

