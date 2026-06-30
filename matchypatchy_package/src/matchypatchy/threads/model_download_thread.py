"""
Functions for managing ML models

"""
import yaml
import logging
import urllib.request
from pathlib import Path
from queue import Queue, Empty

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.config import resource_path


def update_model_yml():
    """
    Downloads the most recent version of the models.yml file from SDZWA server and updates internal file
    """
    # download current version
    model_yml_path = resource_path("assets/models.yml")
    try:
        urllib.request.urlretrieve("https://sandiegozoo.box.com/shared/static/8o59iqmvjfic9btuarijfk30oocr5xkf.yml", model_yml_path)
        return True
    except urllib.error.URLError:
        logging.error("Unable to connect to server.")
        return False


def load_model(key=None):
    """Loads ML model configuration from models.yml, returns full dict or specific key"""
    model_yml_path = resource_path("assets/models.yml")

    with open(model_yml_path, 'r') as cfg_file:
        cfg = yaml.safe_load(cfg_file)
        if key:
            return cfg[key]
        else:
            return cfg


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
    names =  MODELS[key][0]
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
    finished_ok = pyqtSignal(bool, str)

    def __init__(self, ml_dir, parent=None):
        super().__init__(parent)
        self.ml_dir = Path(ml_dir)
        self.download_queue = Queue()  # thread-safe queue
        self._shutdown = False  # flag to signal thread to exit gracefully  
        
        model_yml_path = resource_path("assets/models.yml")
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
                        
                        self.download_one(url=url, final_path=final_path,
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