"""
Thread Class for Processing Sequence

Pair_ID should be given in advance since there is likely 
some mismatch between camera timestamps and they won't be exactly the same

"""
import os
import pandas as pd
from datetime import datetime, timedelta

from PyQt6.QtCore import QThread, pyqtSignal

from ..database.media import fetch_media


# TODO: what to do if sequence_id already exists? 

class SequenceThread(QThread):

    progress_update = pyqtSignal(str)  # Signal to update the progress bar

    def __init__(self, mpDB, max_time = 60, max_n = 3):
        super().__init__()
        self.mpDB = mpDB
        self.max_time = timedelta(seconds=max_time)
        self.max_n = max_n

        self.media = fetch_media(self.mpDB)
        self.media['timestamp'] = pd.to_datetime(self.media['timestamp'], format='mixed')
        self.media = self.media.sort_values(by=['site_id','timestamp'])

    def run(self):
        self.progress_update.emit("Processing sequences...")

        sequences = []
        current_sequence = []
        for i, image in self.media.iterrows():
            if current_sequence:
                if (image['site_id'] == current_sequence[0]['site_id']) and \
                    (image['timestamp'] - current_sequence[0]['timestamp'] <= self.max_time) and \
                    (len(current_sequence) < self.max_n):
                    current_sequence.append(image)
                else:
                    sequences.append(current_sequence)
                    current_sequence = [image]  # Start a new group
            else:
                current_sequence = [image]

        # Append the last group
        if current_sequence:
            sequences.append(current_sequence)

        # update media entries
        for _, group in enumerate(sequences):
            sequence_id = self.mpDB.add_sequence()
            for image in group:
                self.mpDB.edit_row('media', image['id'], {"sequence_id":sequence_id})
                

