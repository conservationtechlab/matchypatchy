"""
Query container for QC mode (review the rois of each individual)
"""
import pandas as pd
from PyQt6.QtCore import pyqtSignal

import matchypatchy.database.media as db_roi
from matchypatchy.algorithm.query_base import BaseQueryContainer
from matchypatchy.threads.model_download_thread import load_model


class QC_QueryContainer(BaseQueryContainer):
    """
    Alternate Query Container for QC Only
    """
    loaded_data = pyqtSignal(pd.DataFrame)

    def __init__(self, parent):
        super().__init__()
        self.project = parent.project
        self.parent = parent
        self.data_raw = pd.DataFrame()
        self.data = pd.DataFrame()
        self.individuals_raw = {}
        self.individuals = {}
        self.filters = {}
        self.ranked_sequences = []
        self.VIEWPOINT_DICT = load_model('VIEWPOINTS')

        self.current_query_rois = []
        self.current_match_rois = []
        # full lists for the query, before viewpoint filtering
        self._all_query_rois = []
        self._all_match_rois = []
        self.current_query = 0
        self.current_match = 0
        self.current_query_sn = 0
        self.n_queries = 0

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
        self.data_raw = db_roi.fetch_roi_media(self.mpDB)
        self.loaded_data.emit(self.data_raw)
        # no data
        if self.data_raw.empty:
            return False

        self.individuals_raw = db_roi.individual_roi_dict(self.data_raw)
        self.individuals_raw.pop(None, None)
        return True

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
        self.individuals = self.individuals_raw.copy()

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

            # Individual Filter
            if filter_dict['active_individual'][0] > 0:
                active_iid = filter_dict['active_individual'][0]
                self.data = self.data[self.data['individual_id'] == int(active_iid)]

        # create new dict of filtered individuals
        self.individuals = db_roi.individual_roi_dict(self.data)
        self.individuals.pop(None, None)

        # Sort by Distance
        # must have valid matches to continue
        if self.individuals:
            self.rank()
            return True
        # filtered neighbor dict returns empty, all existing data must be from same individual
        else:
            return False

    def rank(self):
        """
        Rank the individuals by the number of ROIs they have.
        The ranked list is stored in self.ranked_sequences.
        Also sets the number of queries to validate.
        """
        # Rank by number of rois for each iid
        self.ranked_sequences = sorted(self.individuals.items(), key=lambda x: len(x[1]), reverse=True)
        # set number of queries to validate
        self.n_queries = len(self.ranked_sequences)

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
        # get corresponding sequence_id and rois
        current_sequence_id = self.ranked_sequences[self.current_query][0]
        self._all_query_rois = list(self.individuals[current_sequence_id])
        self.current_query_rois = list(self._all_query_rois)
        # set view to first in sequence
        self.set_within_query_sequence(0)
        # update matches
        self.update_matches()

    # refresh match list
    def update_matches(self):
        """
        Update match list if current_query changes
        """
        # get all matches for query
        self._all_match_rois = list(self._all_query_rois)
        self.current_match_rois = list(self.current_query_rois)

        # set to top of matches, skip the first one which will be on the query side
        self.set_match(1)

    # RETURN INFO --------------------------------------------------------------
    def current_distance(self):
        """Distance between the query and match roi, None without embeddings"""
        similarity = self.mpDB.calculate_similarity(self.current_query_rid, self.current_match_rid)
        return None if similarity is None else 1 - similarity
