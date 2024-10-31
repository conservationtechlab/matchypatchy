"""
Thread Class for Processing Sequence

Pair_ID should be given in advance since there is likely 
some mismatch between camera timestamps and they won't be exactly the same

"""
import pandas as pd
from datetime import timedelta

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.database.media import fetch_media, IMAGE_EXT


# TODO: what to do if sequence_id already exists? 
# TODO: sequence ids for individual videos should be one number, validate

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
        seen_pairs = {}
        for _, image in self.media.iterrows():
            if current_sequence:
                # site is the same, timestamp under threshold, n under threshold
                if (image['site_id'] == current_sequence[0]['site_id']) and \
                    (image['timestamp'] - current_sequence[0]['timestamp'] <= self.max_time) and \
                    (len(current_sequence) < self.max_n):
                    current_sequence.append(image)
                else:
                    # bank the current sequence and start a new group
                    sequences.append(current_sequence)
                    current_sequence = [image]  
            else:
                current_sequence = [image]

            # get pair id, make note to group
            capture_id = image['capture_id']
            g = len(sequences)
            if capture_id in seen_pairs: 
                if g not in seen_pairs[capture_id]:
                    seen_pairs[capture_id].extend([g])  # Merge the current list with the existing one
            else:
                seen_pairs[capture_id] = [g]

        # Append the last group
        if current_sequence:
            sequences.append(current_sequence)

        # merge pairs into the same sequence
        paired_sequences = [value for value in seen_pairs.values() if len(value) > 1]
        sequences = self.merge_paired_sequences(sequences, paired_sequences)

        # update media entries
        for _, group in enumerate(sequences):
            # create a sequence id
            sequence_id = self.mpDB.add_sequence()
            for image in group:
                self.mpDB.edit_row('media', image['id'], {"sequence_id":sequence_id})

    def merge_paired_sequences(self, sequences, pairs):
        # save index of other element to remove later
        to_remove = []
        for pair in pairs:
            min_i = min(pair)
            remainder = [p for p in pair if p != min_i]
            if 0 <= min_i < len(sequences):
                for index in remainder:
                    sequences[min_i] += sequences[index]  # Concatenate the list at the given index
                to_remove.extend(remainder)
    
        # remove duplicate sequences
        to_remove.sort(reverse=True)
        for index in to_remove:
            sequences.pop(index)

        return sequences