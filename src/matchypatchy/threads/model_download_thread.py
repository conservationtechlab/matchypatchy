"""
Functions for managing ML models

"""
import logging
import urllib.request
from pathlib import Path
from queue import Queue, Empty

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.models import load_model, _as_list


logger = logging.getLogger(__name__)


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
