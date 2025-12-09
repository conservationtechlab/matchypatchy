"""
QThread for Matching

"""
import time
import logging
from datetime import timedelta
import pandas as pd
import warnings
warnings.filterwarnings("ignore", category=pd.errors.SettingWithCopyWarning)

from PyQt6.QtCore import QThread, pyqtSignal


class MatchEmbeddingThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    prompt_update = pyqtSignal(str)  # Signal to update the alert prompt
    neighbor_dict_return = pyqtSignal(dict)
    ranked_sequences_return = pyqtSignal(list)
    done = pyqtSignal()

    def __init__(self, mpDB, rois, sequences, k=3, metric='cosine', threshold=70,
                 filter_dict=None, valid_stations=None):
        super().__init__()
        self.mpDB = mpDB
        self.rois = rois.drop(['frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 
                               'comment', 'name', 'sex', 'age'], axis=1).reset_index()
        self.sequences = sequences
        self.n = len(sequences)
        self.k = k
        self.metric = metric
        if self.metric == 'cosine':
            self.threshold = threshold/100
        else:
            self.threshold = threshold
        self.filter_dict = filter_dict
        self.valid_stations = valid_stations

        self.neighbor_dict = {}
        self.ranked_sequences = []

    def run(self):
        """
        # 1. Get sequences of ROIS
        # 2. Get KNN for each ROI in sequence
        # 3. filter out matches from same sequence
        # 4. rank ROIs by match scores
        """
        for i, s in enumerate(self.sequences):
            if not self.isInterruptionRequested():
                sequence_rois = self.sequences[s]

                # get all neighbors for sequence
                all_neighbors = []
                for roi_id in sequence_rois:
                    all_neighbors.extend(self.roi_knn(roi_id))

                all_neighbors = self.remove_duplicate_matches(all_neighbors)
                #print("All Neighbors after removing duplicates:", all_neighbors)
                filtered_neighbors = self.filter_valid(sequence_rois, all_neighbors)

                if filtered_neighbors:
                   filtered_neighbors = self.remove_duplicate_matches(filtered_neighbors)
                   self.neighbor_dict[s] = filtered_neighbors

                completed_percentage = round((100 * (i + 1) / self.n) - 1)

                self.progress_update.emit(completed_percentage)

       # print("Neighbor Dict before ranking:", self.neighbor_dict)
        # rank sequences if matches found
        if self.neighbor_dict:
            self.ranked_sequences = self.rank()
            #print("Ranked Sequences:", self.ranked_sequences)
            # pad sequences
            self.pad_sequences()

        self.progress_update.emit(100)
        self.neighbor_dict_return.emit(self.neighbor_dict)
        self.ranked_sequences_return.emit(self.ranked_sequences)

    # STEP 1
    def roi_knn(self, emb_id):
        """
        Calcualtes knn for single roi embedding
        """
        neighbors = self.mpDB.knn(emb_id, k=self.k)
        nns = list(zip([int(x) for x in neighbors['ids'][0]], neighbors['distances'][0]))
        return nns[1:]  # skip self-match

    # STEP 2
    def filter_valid(self, sequence_rois, neighbors):
        """
        Returns list of valid neighbors by roi_emb.id
        """
        filtered = []
        query_rois = self.rois.loc[self.rois['id'].isin(sequence_rois)]
        neighbors = pd.DataFrame(neighbors, columns=['id', 'distance'])
        neighbors_df = pd.merge(self.rois, neighbors, on='id')

        # Perform a cross-join using a Cartesian product
        query_rois["key"] = 1  # Temporary key for cross-join
        neighbors_df["key"] = 1
        merged = query_rois.merge(neighbors_df, on="key", suffixes=("_query", "_neighbor")).drop("key", axis=1)

        # Apply filtering conditions
        filtered = merged[
            (merged["individual_id_query"].isna() | (merged["individual_id_query"] != merged["individual_id_neighbor"])) &
            (merged["sequence_id_query"].isna() | (merged["sequence_id_query"] != merged["sequence_id_neighbor"])) &
            (merged["viewpoint_query"].isna() | (merged["viewpoint_query"] == merged["viewpoint_neighbor"])) &
            (merged["distance"] < self.threshold) & (merged["distance"] > 0)
        ]
        # Return filtered neighbors as tuples of (ROI ID, distance)
        return list(zip(filtered["id_neighbor"], filtered["distance"]))

    # STEP 3
    def rank(self):
        """
        Ranking Function
            Prioritizes previously IDd individuals and number of matches,
            then ranks matchs by distances
        """
        # remove query sequences with IDed individuals
        ided_sequences = self.rois[~self.rois["individual_id"].isna()]["sequence_id"].unique().tolist()
        self.neighbor_dict = {k: v for k, v in self.neighbor_dict.items() if k not in ided_sequences}

        ided_rois = self.rois[~self.rois["individual_id"].isna()]["id"].unique().tolist()
        favorite_rois = self.rois[self.rois["favorite"] == 1]["id"].tolist()
        #print("Favorite Sequences:", favorite_rois)
        #print("IDed Sequences:", ided_rois)

        # prioritize sequences with IDed individuals
        if len(ided_rois) > 0:
            # remove named individuals from list of queries
            for seq in self.neighbor_dict:
                # rank by distance first
                self.neighbor_dict[seq] = sorted(self.neighbor_dict[seq], key=lambda x: x[1])

                if len(favorite_rois) > 0:
                    self.neighbor_dict[seq] = sorted(self.neighbor_dict[seq], key=lambda x: (x[0] not in favorite_rois))
                self.neighbor_dict[seq] = sorted(self.neighbor_dict[seq], key=lambda x: (x[0] not in ided_rois))
           
            # prioritize by number of matches and ided status
            ranked_sequences = sorted(self.neighbor_dict.items(), key=lambda x: len(x[1]), reverse=True)
            ranked_sequences = sorted(ranked_sequences, key=lambda x: any(item[0] in ided_rois for item in x[1]), reverse=True) 
            ranked_sequences = [x[0] for x in ranked_sequences]

        # if no ids, rank by distance
        else:
            for seq in self.neighbor_dict:
                self.neighbor_dict[seq] = sorted(self.neighbor_dict[seq], key=lambda x: x[1])

            # prioritize by number of matches
            ranked_sequences = sorted(self.neighbor_dict.items(), key=lambda x: len(x[1]), reverse=True)
            ranked_sequences = [x[0] for x in ranked_sequences]

        return ranked_sequences
    
    def pad_sequences(self):
        """
        For each remaining match, add the rest of the sequence to the match stack 
        and move existing sequence matches to the appropriate position
        """
        for query in self.neighbor_dict.keys():
            matched_rois = [item[0] for item in self.neighbor_dict[query]]
            new_stack = []  # match stack after padding
            to_remove = []
            match_sequence_rois ={}
            distances = {}
            for i, match in enumerate(matched_rois):
                match_sequence_id = self.rois.loc[self.rois['id'] == match, 'sequence_id'].values[0]
                match_sequence_rois[match] = self.sequences[match_sequence_id]
                distances[match] = self.neighbor_dict[query][i][1]
                for roi in match_sequence_rois[match]:
                    # check if match sequence appears later in match stack
                    if roi in matched_rois[i+1:]:
                        to_remove.append(roi)
        
            # rebuild match stack with padded sequences, using lowest distance match as anchor
            for match in matched_rois:
                if match not in to_remove:
                    for roi in match_sequence_rois[match]:
                        new_stack.append((roi, distances[match]))

            # replace neighbor dict entry with new padded stack
            self.neighbor_dict[query] = new_stack

    def remove_duplicate_matches(self, matches):
        """
        If a sequence is matched to the same roi multiple times,
        remove duplicate entries
        """
        filtered = []
        seen = set()
        for item in sorted(matches, key=lambda x: x[1]):
            if item[0] not in seen:
                filtered.append(item)
                seen.add(item[0])
        return filtered
