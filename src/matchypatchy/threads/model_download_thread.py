"""
Functions for managing ML models

"""
import os
import sys
import tempfile
import httpx
import yaml
import logging
logger = logging.getLogger(__name__)
import urllib.request
from pathlib import Path
from queue import Queue, Empty

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.config import asset_path


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


class DownloadMLThread(QThread):
    """Thread for downloading ML models, keeps running to take queued downloads"""
    # model key, success, message; emitted once per queued model
    finished_ok = pyqtSignal(str, bool, str)

    def __init__(self, ml_dir, parent=None):
        super().__init__(parent)
        self.ml_dir = Path(ml_dir)
        self.download_queue = Queue()  # thread-safe queue
        # the same models.yml the dialogs read (the downloaded copy if there is one)
        self.models = load_model('MODELS')

    def queue_download(self, model_key: str):
        """Call from UI thread to queue a model for download"""
        self.download_queue.put(model_key)

    def run(self):
        while not self.isInterruptionRequested():
            try:
                key = self.download_queue.get(timeout=0.5)
            except Empty:
                continue
            # report each model; a failed download must not end the thread
            try:
                self.download_model(key)
            except InterruptedError:
                self.finished_ok.emit(key, False, "Download cancelled")
            except urllib.error.URLError:
                logging.exception("Unable to connect to server.")
                self.finished_ok.emit(key, False, "Network error")
            except Exception:
                logging.exception("Download failed.")
                self.finished_ok.emit(key, False, "Download failed")
            else:
                self.finished_ok.emit(key, True, "Download Complete")

    def download_model(self, key):
        """Download every file of a model that isn't there yet"""
        names = _as_list(self.models[key][0])
        urls = _as_list(self.models[key][1])
        for name, url in zip(names, urls):
            final_path = self.ml_dir / name
            if final_path.exists():
                continue
            self.download_one(url=url,
                              final_path=final_path,
                              should_cancel=self.isInterruptionRequested)

    def download_one(self, url: str, final_path: Path, should_cancel) -> None:
        """
        Download url -> final_path with cancel + cleanup.
        Writes to final_path.part, renames on success.
        should_cancel: callable returning True when cancel requested.
        """
        final_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = final_path.with_suffix(final_path.suffix + ".part")

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp, open(tmp_path, "wb") as f:
                while True:
                    if should_cancel():
                        raise InterruptedError("Cancelled")

                    chunk = resp.read(1024 * 1024)  # 1 MiB
                    if not chunk:
                        break
                    f.write(chunk)

            # success: atomic replace
            tmp_path.replace(final_path)

        except Exception:
            # always delete partial
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass
            raise
