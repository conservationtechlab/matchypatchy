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
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/MatchyPatchy"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "MatchyPatchy"
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

def update_model_yml() -> bool:
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


def get_path(ML_DIR, key):
    """Gets path to ML model in ML_DIR"""
    MODELS = load_model('MODELS')
    if key is None:
        return None
    names = MODELS[key][0]
    if len(names) > 0:
        path = Path(ML_DIR) / names[0]
    else:
        path = Path(ML_DIR) / names
    if path.exists():
        return path
    else:
        return None


def delete(ML_DIR, key):
    """Deletes ML model from ML_DIR"""
    path = get_path(ML_DIR, key)
    if path:
        path.unlink()


class DownloadMLThread(QThread):
    """Thread for downloading ML models"""
    finished_ok = pyqtSignal(bool, str)

    def __init__(self, ml_dir, parent=None):
        super().__init__(parent)
        self.ml_dir = Path(ml_dir)
        self.download_queue = Queue()  # thread-safe queue
        self._shutdown = False  # flag to signal thread to exit gracefully

        model_yml_path = asset_path("models.yml")
        with open(model_yml_path, 'r') as cfg_file:
            ml_cfg = yaml.safe_load(cfg_file)
            self.models = ml_cfg['MODELS']

    def queue_download(self, model_key: str):
        """Call from UI thread to queue a model for download"""
        self.download_queue.put(model_key)

    def shutdown(self):
        """Signal thread to exit gracefully"""
        self._shutdown = True

    def run(self):
        try:
            while not self.isInterruptionRequested():
                try:
                    # Non-blocking: raises Empty if queue is empty
                    key = self.download_queue.get(timeout=0.5)

                    names = self.models[key][0]
                    urls = self.models[key][1]

                    for i, url in enumerate(urls):
                        name = names[i]
                        final_path = self.ml_dir / name

                        if final_path.exists():
                            continue

                        self.download_one(url=url,
                                          final_path=final_path,
                                          should_cancel=self.isInterruptionRequested)
                except Empty:
                    self.finished_ok.emit(True, "Download Complete")

        except InterruptedError:
            self.finished_ok.emit(False, "Download cancelled")
        except urllib.error.URLError:
            logging.exception("Unable to connect to server.")
            self.finished_ok.emit(False, "Network error")
        except Exception:
            logging.exception("Download failed.")
            self.finished_ok.emit(False, "Download failed")

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
