"""

"""

import pandas as pd

from PyQt6.QtCore import QThread, pyqtSignal


class MatchEmbeddingThread(QThread):
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    neighbor_dict_return = pyqtSignal(dict)
    nearest_dict_return = pyqtSignal(dict)


    def __init__(self, mpDB, sequences, k=3, threshold=100):
        super().__init__()
        self.mpDB = mpDB
        self.sequences = sequences
        self.k = k
        self.threshold = threshold

        info = "roi.id, media_id, reviewed, species_id, individual_id, emb_id, timestamp, site_id, sequence_id"
        # need sequence and capture ids from media to restrict comparisons shown to 
        rois, columns = mpDB.select_join("roi", "media", 'roi.media_id = media.id', columns=info)
        self.rois = pd.DataFrame(rois,columns=columns)
        

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
            for roi_id in self.sequences[s]:
                emb_id = self.rois.loc[self.rois['id'] == roi_id, "emb_id"].item()
                neighbors = self.roi_knn(emb_id)
                filtered_neighbors = self.filter(roi_id, neighbors)
                if filtered_neighbors: 
                    neighbor_dict.setdefault(s, []).extend(filtered_neighbors)
            # sort after matching full sequence
            if s in neighbor_dict.keys():
                # save closest neighbor
                ranked = sorted(neighbor_dict[s], key=lambda x: x[1])
                nearest_dict[s] = ranked[0][1]
                neighbor_dict[s] = self.remove_duplicate_matches(ranked)
            self.progress_update.emit(i+1)
        
        self.neighbor_dict_return.emit(neighbor_dict)
        self.nearest_dict_return.emit(nearest_dict)        

    def roi_knn(self, emb_id):
        """
        Calcualtes knn for single roi embedding
        """
        query = self.mpDB.select("roi_emb", columns="embedding", row_cond= f'rowid={emb_id}')[0][0]
        neighbors = self.mpDB.knn(query, k=self.k)
        return neighbors

    def filter(self, roi_id, neighbors):
        """
        Returns list of valid neighbors by roi_emb.id
        """
        filtered = []
        query = self.rois[self.rois['id'] == roi_id].squeeze()
        for i in range(len(neighbors)):  # skip first one, self match
            match = self.rois[self.rois['emb_id'] == neighbors[i][0]].squeeze()
            # if not same individual or unlabeled individual:
            if (query['individual_id'] is None) or (match['individual_id'] != query['individual_id']):
                # if not in same sequence
                if (query['sequence_id'] is None) or (match['sequence_id'] != query['sequence_id']):
                    # distance check (do first or last?)
                    if neighbors[i][1] < self.threshold and neighbors[i][1] > 0:
                        # replace emb_id with roi_id
                        match_roi_id = int(match['id'])
                        filtered.append((match_roi_id, neighbors[i][1]))
        return filtered

    def remove_duplicate_matches(self, matches):
        """
        If a sequence is matched to the same roi multiple times, 
        remove duplicate entries
        """
        filtered = []
        seen = set()
        for item in matches:
            if item[0] not in seen:
                filtered.append(item)
                seen.add(item[0])
        return filtered
