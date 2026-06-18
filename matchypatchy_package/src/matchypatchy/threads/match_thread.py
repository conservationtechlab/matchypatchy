"""
QThread for Matching Embeddings

"""
import pandas as pd

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.threads.match_object import MatchObject



class MatchEmbeddingThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    prompt_update = pyqtSignal(str)  # Signal to update the alert prompt
    ranked_queries_return = pyqtSignal(list)
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
            self.threshold = 1 - (threshold / 100)
        else:
            self.threshold = 100 - threshold
        self.filter_dict = filter_dict
        self.valid_stations = valid_stations

        self.pairs = []
        self.ranked_sequences = []
        self.ranked_sequences_without_query_order = []

    def run(self):
        """
        # Before running, get sequences of ROIS
        # 1. Get KNN for each ROI in sequence
        # 1b. Remove duplicates for each ROI
        # 2. Filter out matches from same sequence, same individual, different viewpoint, low confidence
        # 2b. Remove duplicates for each sequence
        # 3. Rank ROIs by match scores, prioritize previously IDd individuals
        # 4. Pad sequences to include all ROIs from matched sequences
        """
        for i, s in enumerate(self.sequences):
            if not self.isInterruptionRequested():
                sequence_rois = self.sequences[s]

                # get all neighbors for sequence
                all_neighbors = []
                for roi_id in sequence_rois:
                    all_neighbors.extend(self.roi_knn(roi_id))

                all_neighbors = self.remove_duplicate_matches(all_neighbors)
                # filter neighbors for valid matches
                filtered_neighbors = self.filter_valid(sequence_rois, all_neighbors)

                if filtered_neighbors:
                    filtered_neighbors = self.remove_duplicate_matches(filtered_neighbors)

                    # get viewpoints for query sequence and matched sequence
                    query_data = self.rois[self.rois['id'].isin(sequence_rois)][['id', 'viewpoint']]
                    matches = [x[0] for x in filtered_neighbors]
                    match_data = self.rois[self.rois['id'].isin(matches)][['id', 'viewpoint']]
                    # create match object to store matches and data for each sequence, to be used in ranking and padding
                    match_object = MatchObject(s, filtered_neighbors, query_data, match_data)
                    self.pairs.append(match_object)

                completed_percentage = round((100 * (i + 1) / self.n) - 1)
                self.progress_update.emit(completed_percentage)

        # rank sequences if matches found
        if len(self.pairs) > 0:
            # rank sequences by number of matches and ided status of matches
            self.rank()
            # pad sequences with remaining matches and order by viewpoint
            for match_object in self.pairs:
                match_object.pad_sequences(self.rois, self.sequences)
                match_object.order_matches()

        self.progress_update.emit(100)
        self.ranked_queries_return.emit(self.pairs)

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
        query_rois = self.rois.loc[self.rois['id'].isin(sequence_rois)].copy()
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
            Prioritizes sequences with matches that have previously IDd individuals and by total number of matches
        """
        # remove query sequences with IDed individuals
        ided_sequences = self.rois[~self.rois["individual_id"].isna()]["sequence_id"].unique().tolist()
        self.pairs = [m for m in self.pairs if m.sequence_id not in ided_sequences]

        # prioritize rois with known IDs and favorites
        ided_rois = self.rois[~self.rois["individual_id"].isna()]["id"].unique().tolist()
        favorite_rois = self.rois[self.rois["favorite"] == 1]["id"].tolist()

        # prioritize sequences with IDed individuals
        if len(ided_rois) > 0:
            for match_object in self.pairs:
                # prioritize matches by favorites 
                if len(favorite_rois) > 0:
                    match_object.rank_neighbors_by_distance()
                    match_object.rank_neighbors_by_favorites(favorite_rois)
                # then prioritize matches by IDed status
                match_object.rank_neighbors_by_ided(ided_rois)

            # prioritize by number of matches and ided status
            self.pairs = sorted(self.pairs, key=lambda x: len(x.neighbors), reverse=True)
            self.pairs = sorted(self.pairs, key=lambda x: any(item[0] in ided_rois for item in x.neighbors), reverse=True)

        # if no ids, rank by distance
        else:
            for match_object in self.pairs:
                match_object.rank_neighbors_by_distance()
            # prioritize by number of matches
            self.pairs = sorted(self.pairs, key=lambda x: len(x.neighbors), reverse=True)

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
