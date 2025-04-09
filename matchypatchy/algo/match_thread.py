"""
QThread for Matching

"""
import pandas as pd
import warnings
warnings.filterwarnings("ignore", category=pd.errors.SettingWithCopyWarning)

from PyQt6.QtCore import QThread, pyqtSignal


class MatchEmbeddingThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    neighbor_dict_return = pyqtSignal(dict)
    nearest_dict_return = pyqtSignal(dict)

    def __init__(self, mpDB, rois, sequences, k=3, metric='Cosine', threshold=100):
        super().__init__()
        self.mpDB = mpDB
        self.rois = rois
        self.sequences = sequences
        self.k = k
        self.metric = metric
        if self.metric == 'Cosine':
            self.threshold = threshold/100
        else:
            self.threshold = threshold

    def run(self):
        """
        # 1. Get sequences of ROIS
        # 2. Get KNN for each ROI in sequence
        # 3. filter out matches from same sequence
        # 4. rank ROIs by match scores
        """
        neighbor_dict = {}
        nearest_dict = {}

        for i, s in enumerate(self.sequences):
            if not self.isInterruptionRequested():
                sequence_rois = self.sequences[s]
                emb_ids = self.rois.loc[self.rois['id'].isin(sequence_rois), "emb_id"].tolist()

                # skip rois with no emb_ids
                emb_ids = [e for e in emb_ids if e > 0]

                # get all neighbors for sequence
                all_neighbors = []
                for emb_id in emb_ids:
                    all_neighbors.extend(self.roi_knn(emb_id))
                # remove impossible matches
                all_neighbors = self.remove_duplicate_matches(all_neighbors)
                filtered_neighbors = self.filter(sequence_rois, all_neighbors)

                # still have neighbors remaining after filtering, rank by difference
                if filtered_neighbors:
                    filtered_neighbors = self.remove_duplicate_matches(filtered_neighbors)
                    neighbor_dict[s] = filtered_neighbors
                    nearest_dict[s] = filtered_neighbors[0][1]
                self.progress_update.emit(i + 1)

            self.neighbor_dict_return.emit(neighbor_dict)
            self.nearest_dict_return.emit(nearest_dict)

    def roi_knn(self, emb_id):
        """
        Calcualtes knn for single roi embedding
        """
        query = self.mpDB.select("roi_emb", columns="embedding", row_cond=f'rowid={emb_id}')[0][0]
        # return self.mpDB.knn(query, k=self.k)
        return self.mpDB.knn(query, k=self.k, metric=self.metric)

    def filter(self, sequence_rois, neighbors):
        """
        Returns list of valid neighbors by roi_emb.id
        """
        filtered = []
        query_rois = self.rois.loc[self.rois['id'].isin(sequence_rois)]
        neighbors_df = self.rois[self.rois['emb_id'].isin([n[0] for n in neighbors])]
        neighbors_df["distance"] = [n[1] for n in neighbors]  # Add distances from KNN

        # Perform a cross-join using a Cartesian product
        query_rois["key"] = 1  # Temporary key for cross-join
        neighbors_df["key"] = 1
        merged = query_rois.merge(neighbors_df, on="key", suffixes=("_query", "_neighbor")).drop("key", axis=1)

        # Apply filtering conditions
        filtered = merged[
            (merged["individual_id_query"].isna() | (merged["individual_id_query"] != merged["individual_id_neighbor"])) &
            (merged["sequence_id_query"].isna() | (merged["sequence_id_query"] != merged["sequence_id_neighbor"])) &
            (merged["distance"] < self.threshold) & (merged["distance"] > 0)
        ]
        # Return filtered neighbors as tuples of (ROI ID, distance)
        return list(zip(filtered["id_neighbor"], filtered["distance"]))

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
