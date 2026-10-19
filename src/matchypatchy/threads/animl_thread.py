"""
QThreads for building file manifests and verifying upload directories with ANIML

Detection runs in process_thread.ProcessThread
"""
import animl
import pandas as pd

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.database.media import get_sha256



class BuildManifestThread(QThread):
    """
    Thread for launching buildfilemanifest
    """
    manifest = pyqtSignal(pd.DataFrame)

    def __init__(self, directory, timezone):
        super().__init__()
        self.directory = directory
        self.timezone = timezone

    def run(self):
        self.data = animl.build_file_manifest(self.directory, exif=True, data_timezone=self.timezone)
        self.manifest.emit(self.data)


class VerifyNewBaseDirsThread(QThread):
    """
    Thread for launching buildfilemanifest
    """
    not_in_db = pyqtSignal(list)
    not_in_new_directory = pyqtSignal(list)
    finished = pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.mpDB = parent.mpDB
        self.base_dirs = parent.base_dirs
        self.updates = parent.updates
        self.not_found_in_db = []
        self.not_found_in_new_directory = []

    def run(self):
        for update in self.updates:
            if not self.isInterruptionRequested():
                base_dir_id = update[0]
                directory = update[1]
                # Flatten the list of media hashes for easier comparison
                media = self.mpDB.select("media", columns="relative_path, sha256", row_cond=f"base_dir_id = {base_dir_id}")
                media_hashes = set([h[1] for h in media])

                # Build the file manifest for the new directory
                new_data = animl.build_file_manifest(directory, exif=False)
                new_hashes = [get_sha256(filepath) for filepath in new_data['filepath']]
                new_data = list(zip(new_data['filepath'], new_hashes))

                hash_not_found_in_db = [h[0] for h in new_data if h[1] not in set(media_hashes)]
                self.not_found_in_db.append(hash_not_found_in_db)

                hash_not_found_in_new_directory = [h[0] for h in media if h[1] not in set(new_hashes)]
                self.not_found_in_new_directory.append(hash_not_found_in_new_directory)

        # Emit signals if the thread was not interrupted
        if not self.isInterruptionRequested():
            self.not_in_db.emit(self.not_found_in_db)
            self.not_in_new_directory.emit(self.not_found_in_new_directory)
            self.finished.emit()
