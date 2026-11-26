"""
QThread for Matching Embeddings

"""
from PyQt6.QtCore import QThread, pyqtSignal
from matchypatchy.algorithm.match_object import MatchObject


class MatchEmbeddingThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    ranked_queries_return = pyqtSignal(list)
    done = pyqtSignal()

    def __init__(self, mpDB, rois, sequences, k=3, metric='cosine', threshold=70,
                 filter_dict=None, valid_stations=None):
        super().__init__()
        self.mpDB = mpDB
        # drop unnecessary columns from the ROIs dataframe
        self.rois = rois.drop(['frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h',
                               'comment', 'name', 'sex'], axis=1).reset_index()
        # dict of sequence_id: roi_ids
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
        self.ided_sequences = set(self.rois[~self.rois["individual_id"].isna()]["sequence_id"].unique())
        
        
        self.match_object_list = []  # list of match objects
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
                # rois without a sequence group under a null key with no ids
                if not sequence_rois:
                    continue

                # skip sequences that have already been IDed
                if s in self.ided_sequences:
                    continue

                # get all neighbors for given sequence, dict rid:distance
                all_neighbors = self.batch_roi_knn(sequence_rois)
                # filter neighbors for valid matches
                filtered_neighbors = self.filter_valid(sequence_rois, all_neighbors)

                if filtered_neighbors:
                    # get data for query sequence and matched sequences
                    query_data = self.rois[self.rois['id'].isin(sequence_rois)]
                    match_data = self.rois[self.rois['id'].isin(filtered_neighbors.keys())]

                    # create match object to store matches and data for each sequence, to be used in ranking and padding
                    match_object = MatchObject(s, filtered_neighbors, query_data, match_data)
                    self.match_object_list.append(match_object)

                completed_percentage = round((100 * (i + 1) / self.n) - 1)
                self.progress_update.emit(completed_percentage)

        # rank sequences if matches found
        if len(self.match_object_list) > 0:
            # rank sequences by number of matches and ided status of matches
            self.rank()

        self.progress_update.emit(100)
        self.ranked_queries_return.emit(self.match_object_list)

    # STEP 1: Batch KNN queries
    def batch_roi_knn(self, sequence_rois):
        """
        Query KNN for all ROIs in a sequence at once.
        """
        roi_ids_list = list(sequence_rois)
        neighbors = self.mpDB.batch_knn(roi_ids_list, k=self.k)
        
        all_neighbors = {}
        for roi_id, (neighbor_ids, distances) in neighbors.items():
            # Skip self-match (first result)
            for neighbor_id, distance in zip(neighbor_ids[1:], distances[1:]):
                if neighbor_id not in all_neighbors:
                    all_neighbors[neighbor_id] = distance
                else:
                    # Keep the minimum distance for each neighbor
                    all_neighbors[neighbor_id] = min(all_neighbors[neighbor_id], distance)

        return all_neighbors

    # STEP 2
    def filter_valid(self, sequence_rois, neighbors):
        """
        Filters neighbors by distance threshold and ensures they are not the same individual or sequence already

        """
        roi_info = ['id', 'individual_id', 'sequence_id', 'viewpoint']

        # Get the DataFrame of neighbors with their distances
        neighbors_df = self.rois[self.rois['id'].isin(neighbors.keys())].copy()
        neighbors_df['distance'] = neighbors_df['id'].map(neighbors)

        # Vectorized lookup for query ROI data
        sequence_rois_set = set(sequence_rois)
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
        
        # Apply filters
        filtered = merged[
            (merged["query_individual_id"].isna() | (merged["query_individual_id"] != merged["individual_id"])) &
            (merged["query_sequence_id"].isna() | (merged["query_sequence_id"] != merged["sequence_id"])) &
            (merged["query_viewpoint"].isna() | (merged["query_viewpoint"] == merged["viewpoint"])) &
            (merged["distance"] < self.threshold) & 
            (merged["distance"] > 0)
        ]
        # Return filtered neighbors as a dictionary of (ROI ID: distance)
        neighbors = dict(zip(filtered["id"], filtered["distance"]))
        return neighbors

    # STEP 3: Batch ranking with single sort
    def rank(self):
        """
        Rank match objects based on multiple criteria:  IDed status, favorites, and distance
        """
        # Get the set of favorite ROIs and IDed ROIs
        favorite_rids_set = set(self.rois[self.rois["favorite"] == 1]["id"].tolist())
        ided_rids_set = set(self.rois[~self.rois["individual_id"].isna()]["id"].tolist())

    
        # Apply ranking to all matches at once
        for match_object in self.match_object_list:
            match_object.rank_sequences(self.rois, self.sequences, favorite_rids_set, ided_rids_set)
            match_object.order_matches_by_viewpoint()

        # prioritize by number of matches and ided status
        self.match_object_list = sorted(self.match_object_list, key=lambda x: len(x.neighbors), reverse=True)
        if len(ided_rids_set) > 0:
            self.match_object_list = sorted(self.match_object_list, key=lambda x: any(item[0] in ided_rids_set for item in x.neighbors), reverse=True)
