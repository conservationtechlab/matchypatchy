"""
Class Definition for Query Object
"""
import pandas as pd
from PyQt6.QtCore import pyqtSignal

import matchypatchy.database.media as db_roi
from matchypatchy.gui.query import BaseQueryContainer
from matchypatchy.threads.model_download_thread import load_model


class ManualQueryContainer(BaseQueryContainer):
    """
    Alternate Query Container for QC Only
    """
    loaded_data = pyqtSignal(pd.DataFrame)

    def __init__(self, parent, selected_ids):
        super().__init__()
        self.mpDB = parent.mpDB
        self.parent = parent
        self.logger = parent.logger
        self.selected_ids = selected_ids
        self.data_raw = pd.DataFrame()
        self.data = pd.DataFrame()
        self.pair_table = pd.DataFrame()
        self.filters = {}

        self.VIEWPOINT_DICT = load_model('VIEWPOINTS')

        self.current_query_rois = []
        self.current_match_rois = []
        # full lists for the query, before viewpoint filtering
        self._all_query_rois = []
        self._all_match_rois = []
        self.current_query = 0
        self.current_match = 1
        self.current_query_sn = 0
        self.n_queries = 0
        self.ranked_sequences = []

        # ROI REFERENCE
        self.current_query_rid = 0
        self.current_match_rid = 0

        self.viewpoints = {}
        self.match_viewpoints = {}
        self.selected_viewpoint = 'all'
        self.empty_query = 0
        self.empty_match = 0

    # STEP 1
    def load_data(self):
        """
        Load ROI Table
        """
        self.data_raw = db_roi.fetch_roi_media(self.mpDB, rids=self.selected_ids)
        self.loaded_data.emit(self.data_raw)
        # no data
        if self.data_raw.empty:
            return False

        # must have embeddings to continue
        return not (self.data_raw["emb"] == 0).all()

    # STEP 2
    def filter(self, filter_dict=None, valid_stations=None):
        """
        Filter media based on active survey selected in dropdown of DisplayMedia
        Triggered by calculate neighbors and change in filters

        if filter > 0 : use id
        if filter == 0: do not filter
        """
        # create backups for filtering
        self.data = self.data_raw.copy()

        if filter_dict is not None and valid_stations is not None:
            # Region Filter (depends on prefilterd stations from MediaDisplay)
            if filter_dict['active_region'][0] > 0 and valid_stations:
                self.data = self.data[self.data['station_id'].isin(list(valid_stations.keys()))]

            # Survey Filter (depends on prefilterd stations from MediaDisplay)
            if filter_dict['active_survey'][0] > 0 and valid_stations:
                self.data = self.data[self.data['station_id'].isin(list(valid_stations.keys()))]

            # Single station Filter
            if filter_dict['active_station'][0] > 0 and valid_stations:
                self.data = self.data[self.data['station_id'] == filter_dict['active_station'][0]]
            elif filter_dict['active_station'][0] == 0 and valid_stations:
                self.data = self.data[self.data['station_id'].isin(list(valid_stations.keys()))]
            else:  # no valid stations, empty dataframe
                return False

        rois = self.data.index.tolist()
        # set current query rois to all rois once
        self.ranked_sequences = [[r] for r in rois]
        # set number of queries to validate
        self.n_queries = len(rois)

        if rois:
            # set match to first entry
            self._all_match_rois = list(rois)
            self.current_match_rois = list(rois)
            self.set_match(self.current_match)  # current_match default to 1
            return True
        else:
            return False

    def calculate_neighbors(self):
        """Calculate pairwise distances between all media in the current dataset."""
        distances_list = []
        for i in range(len(self.data.index.tolist())):
            for j in range(i + 1, len(self.data.index.tolist())):  # Only j > i
                id1, id2 = self.data.index.tolist()[i], self.data.index.tolist()[j]
                similarity = self.mpDB.calculate_similarity(id1, id2)
                # None if either roi has no embedding
                distance = None if similarity is None else 1 - similarity

                distances_list.append({
                    'id1': id1,
                    'id2': id2,
                    'distance': distance
                })

        self.pair_table = pd.DataFrame(distances_list)

    def set_query(self, n):
        """
        Set the Query side to a particular (n) individual in the list
        """
        # wrap around
        if n < 0:
            n = self.n_queries - 1
        if n > self.n_queries - 1:
            n = 0

        # set current query
        self.current_query = n
        self._all_query_rois = list(self.ranked_sequences[self.current_query])
        self.current_query_rois = list(self._all_query_rois)
        # set view to first in sequence
        self.set_within_query_sequence(0)
        # update matches
        # self.update_matches()  not necessary

    # RETURN INFO --------------------------------------------------------------
    def current_distance(self):
        """Return distance between current sequence and matchs"""
        lower = min(self.current_query_rid, self.current_match_rid)
        upper = max(self.current_query_rid, self.current_match_rid)
        distance = self.pair_table.loc[(self.pair_table['id1'] == lower) & (self.pair_table['id2'] == upper), 'distance']
        # None if the pair has no stored distance, 0 would display as a perfect match
        return distance.values[0] if not distance.empty else None
