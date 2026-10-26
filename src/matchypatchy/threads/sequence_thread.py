"""
QThread Class for Processing Sequence

Pair_ID should be given in advance since there is likely
some mismatch between camera timestamps and they won't be exactly the same

"""
import pandas as pd
from datetime import timedelta

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.database.media import fetch_media


class SequenceThread(QThread):
    """Thread for processing media sequences based on station, camera, and timestamp."""
    prompt_update = pyqtSignal(str)  # Signal to update the alert prompt
    done = pyqtSignal()

    def __init__(self, mpDB, cfg, flag):
        super().__init__()
        self.mpDB = mpDB
        self.flag = flag
        self.max_time = timedelta(seconds=int(cfg.SEQUENCE_DURATION))
        self.media = None  # loaded in run(), off the GUI thread

    def run(self):
        self.prompt_update.emit("Loading media...")
        self._load_media()
        # if process sequence option is checked, will rewrite sequence_id
        if self.flag:
            self.prompt_update.emit("Processing sequences...")

            sequences = []
            current_sequence = []
            for _, image in self.media.iterrows():
                # cancelled: leave the existing sequences untouched
                if self.isInterruptionRequested():
                    return
                if current_sequence:
                    # station and camera are the same, timestamp under threshold
                    # images without a camera each get their own sequence
                    if (image['station_id'] == current_sequence[0]['station_id']) and \
                       (image['timestamp'] - current_sequence[0]['timestamp'] <= self.max_time):
                        current_sequence.append(image)
                    else:
                        # bank the current sequence and start a new group
                        sequences.append(current_sequence)
                        current_sequence = [image]
                else:
                    current_sequence = [image]

            # Append the last group
            if current_sequence:
                sequences.append(current_sequence)

            # update media entries
            for group in sequences:
                if self.isInterruptionRequested():
                    return
                # create a sequence id
                sequence_id = self.mpDB.add_sequence()
                for image in group:
                    self.mpDB.edit_row('media', image['id'], {"sequence_id": sequence_id})

        # if not calculating sequence, each media entry gets own sequence_id
        else:
            # only add sequence_id where blank
            self.media = self.media[self.media['sequence_id'].isna()]
            for _, image in self.media.iterrows():
                if self.isInterruptionRequested():
                    return
                sequence_id = self.mpDB.add_sequence()
                self.mpDB.edit_row('media', image['id'], {"sequence_id": sequence_id})

        if not self.isInterruptionRequested():
            self.done.emit()

    def _load_media(self):
        """
        Fetch all media sorted by station, camera and time

        Called at the start of run() rather than in __init__: the thread is built on the
        GUI thread, where fetching and parsing every timestamp froze the progress popup
        on large databases.
        """
        self.media = fetch_media(self.mpDB)
        self.media['timestamp'] = pd.to_datetime(self.media['timestamp'], format='mixed')
        self.media = self.media.sort_values(by=['station_id', 'camera_id', 'timestamp'])
