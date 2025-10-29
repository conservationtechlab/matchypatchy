"""
Thread Class for Processing Sequence

Pair_ID should be given in advance since there is likely
some mismatch between camera timestamps and they won't be exactly the same

"""
import pandas as pd
from datetime import timedelta

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.database.media import fetch_media
from matchypatchy.config import load


class SequenceThread(QThread):
    prompt_update = pyqtSignal(str)  # Signal to update the alert prompt
    done = pyqtSignal()

    def __init__(self, mpDB, flag):
        super().__init__()
        self.mpDB = mpDB
        self.flag = flag
        self.max_time = timedelta(seconds=int(load('SEQUENCE_DURATION')))
        self.max_n = int(load('SEQUENCE_N'))

        self.media = fetch_media(self.mpDB)
        self.media['timestamp'] = pd.to_datetime(self.media['timestamp'], format='mixed')
        self.media = self.media.sort_values(by=['station_id', 'camera_id', 'timestamp'])

    def run(self):
        # if process sequence option is checked, will rewrite sequence_id
        if self.flag:
            self.prompt_update.emit("Processing sequences...")

            sequences = []
            current_sequence = []
            for _, image in self.media.iterrows():
                if not self.isInterruptionRequested():
                    if current_sequence:
                        # station is the same, timestamp under threshold, n under threshold
                        if (image['station_id'] == current_sequence[0]['station_id']) and \
                            (image['camera_id'] == current_sequence[0]['camera_id']) and \
                            (image['timestamp'] - current_sequence[0]['timestamp'] <= self.max_time) and \
                            (len(current_sequence) < self.max_n):
                            current_sequence.append(image)
                        else:
                            # bank the current sequence and start a new group
                            sequences.append(current_sequence)
                            current_sequence = [image]
                    else:
                        current_sequence = [image]

            if not self.isInterruptionRequested():
                # Append the last group
                if current_sequence:
                    sequences.append(current_sequence)

                # update media entries
                for _, group in enumerate(sequences):
                    # create a sequence id
                    sequence_id = self.mpDB.add_sequence()
                    for image in group:
                        self.mpDB.edit_row('media', image['id'], {"sequence_id": sequence_id})

        # if not calculating sequence, each media entry gets own sequence_id
        else:
            # only add sequence_id where blank
            self.media = self.media[self.media['sequence_id'].isna()]
            for _, image in self.media.iterrows():
                sequence_id = self.mpDB.add_sequence()
                self.mpDB.edit_row('media', image['id'], {"sequence_id": sequence_id})

        if not self.isInterruptionRequested():
            self.done.emit()
