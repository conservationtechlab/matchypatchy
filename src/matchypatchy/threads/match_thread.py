"""
QThread for Matching Embeddings

"""
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal
from matchypatchy.threads.match_object import MatchObject


class MatchEmbeddingThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
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

        # Pre-compute lookup dictionaries for fast filtering
        self.roi_id_map = self.rois.set_index('id').to_dict('index')
        self.sequence_id_to_rois = {s: rois_list for s, rois_list in sequences.items()}
        
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
                all_neighbors = self.batch_roi_knn(sequence_rois)
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

    # STEP 1: Batch KNN queries
    def batch_roi_knn(self, roi_ids):
        """
        Query KNN for all ROIs in a sequence at once.
        """
        roi_ids_list = list(roi_ids)
        neighbors = self.mpDB.batch_knn(roi_ids_list, k=self.k)
        
        all_neighbors = []
        for roi_id, (neighbor_ids, distances) in neighbors.items():
            # Skip self-match (first result)
            for neighbor_id, distance in zip(neighbor_ids[1:], distances[1:]):
                all_neighbors.append((int(neighbor_id), distance))
        
        return all_neighbors

    # STEP 2
    def filter_valid(self, sequence_rois, neighbors):
        """
        Vectorized filtering using set operations and DataFrame lookups.
        Avoids cross-join cartesian product.
        """
        roi_info = ['id', 'individual_id', 'sequence_id', 'viewpoint']

        sequence_rois_set = set(sequence_rois)
        neighbors_df = pd.DataFrame(neighbors, columns=['id', 'distance'])
        
        # merge neighbor distance with ROI metadata
        neighbors_df = neighbors_df.merge(self.rois[roi_info], on='id', how='left')
        
        # Vectorized lookup for query ROI data
        query_rois_data = self.rois[self.rois['id'].isin(sequence_rois_set)][roi_info].rename(columns={
            'id': 'query_id',
            'individual_id': 'query_individual_id',
            'sequence_id': 'query_sequence_id',
            'viewpoint': 'query_viewpoint'
        })
        
        # Cross join only once, then filter
        neighbors_df['key'] = 1
        query_rois_data['key'] = 1
        merged = neighbors_df.merge(query_rois_data, on='key', how='inner').drop('key', axis=1)
        
        # Apply all filters vectorized
        filtered = merged[
            (merged["query_individual_id"].isna() | (merged["query_individual_id"] != merged["individual_id"])) &
            (merged["query_sequence_id"].isna() | (merged["query_sequence_id"] != merged["sequence_id"])) &
            (merged["query_viewpoint"].isna() | (merged["query_viewpoint"] == merged["viewpoint"])) &
            (merged["distance"] < self.threshold) & 
            (merged["distance"] > 0)
        ]
        # Return filtered neighbors as tuples of (ROI ID, distance)
        return list(zip(filtered["id"], filtered["distance"]))

    # STEP 3: Batch ranking with single sort
    def rank(self):
        """
        Optimized ranking - combine multiple criteria into single sort key.
        Avoids repeated sorting passes.
        """
        ided_sequences = set(self.rois[~self.rois["individual_id"].isna()]["sequence_id"].unique())
        self.pairs = [m for m in self.pairs if m.sequence_id not in ided_sequences]

        ided_rois_set = set(self.rois[~self.rois["individual_id"].isna()]["id"].unique())
        favorite_rois_set = set(self.rois[self.rois["favorite"] == 1]["id"].tolist())

        if len(ided_rois_set) > 0:
            # Apply ranking to all matches at once
            for match_object in self.pairs:
                # Combine all ranking criteria into single sort
                if len(favorite_rois_set) > 0:
                    match_object.rank_neighbors_by_distance()
                    match_object.rank_neighbors_by_favorites(favorite_rois_set)
                # then prioritize matches by IDed status
                match_object.rank_neighbors_by_ided(ided_rois_set)

           # prioritize by number of matches and ided status
            self.pairs = sorted(self.pairs, key=lambda x: len(x.neighbors), reverse=True)
            self.pairs = sorted(self.pairs, key=lambda x: any(item[0] in ided_rois_set for item in x.neighbors), reverse=True)
        else:
            # No IDs - just sort by distance and count
            for match_object in self.pairs:
                match_object.neighbors = sorted(match_object.neighbors, key=lambda x: x[1])
            # prioritize by number of matches
            self.pairs = sorted(self.pairs, key=lambda x: len(x.neighbors), reverse=True)

    def remove_duplicate_matches(self, matches):
        """
        Remove duplicates in single pass using dict (maintains first/lowest).
        """
        seen_dict = {}
        for roi_id, distance in sorted(matches, key=lambda x: x[1]):
            if roi_id not in seen_dict:
                seen_dict[roi_id] = distance
        return list(seen_dict.items())