"""
Class Definition for Query Object
"""
import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal

import matchypatchy.database.media as db_roi
from matchypatchy.database.location import fetch_station_names_from_id
from matchypatchy.threads.model_download_thread import load_model


class ManualQueryContainer(QObject):
    """
    Alternate Query Container for QC Only
    """
    loaded_data = pyqtSignal(pd.DataFrame)

    def __init__(self, parent, selected_ids):
        super().__init__()
        self.mpDB = parent.mpDB
        self.parent = parent
        self.selected_ids = selected_ids
        self.data_raw = pd.DataFrame()
        self.data = pd.DataFrame()
        self.pair_table = pd.DataFrame()
        self.filters = {}

        self.VIEWPOINT_DICT = load_model('VIEWPOINTS')

        self.current_query_rois = []
        self.current_match_rois = []
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
            self.current_match_rois = rois
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
                distance = 1 - self.mpDB.calculate_similarity(id1, id2)

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
        self.current_query_rois = self.ranked_sequences[self.current_query]
        # set view to first in sequence
        self.set_within_query_sequence(0)
        # update matches
        # self.update_matches()  not necessary

    def set_within_query_sequence(self, n):
        """
        If the query sequence contains more than one image,
        set the display to the nth element in the sequence
        """
        # wrap around
        if n < 0:
            n = len(self.current_query_rois) - 1
        if n > len(self.current_query_rois) - 1:
            n = 0

        if self.current_query_rois:
            self.current_query_sn = n  # number within sequence
            self.current_query_rid = self.current_query_rois[self.current_query_sn]

    # refresh match list
    def set_match(self, n):
        """
        Set the curent match index and id
        """
        # wrap around
        if n < 0:
            n = len(self.current_match_rois) - 1
        if n > len(self.current_match_rois) - 1:
            n = 0

        self.current_match = n
        self.current_match_rid = self.current_match_rois[self.current_match]

    # VIEWPOINT ----------------------------------------------------------------

    def toggle_viewpoint(self, selected_viewpoint):
        """Set the selected viewpoint filter and update rois"""
        data = self.data.loc[self.current_query_rois]
        query_viewpoint_map = dict(zip(data.index, data['viewpoint']))

        self.selected_viewpoint = selected_viewpoint
        # if selected_viewpoint is all, show all rois
        if self.selected_viewpoint == 1:
            return True
  
        # adjust numbering
        self.selected_viewpoint = 1 if self.selected_viewpoint == 2 else selected_viewpoint
        self.current_query_rois = [rid for rid in self.current_query_rois if query_viewpoint_map[rid] == self.selected_viewpoint]
        self.current_match_rois = [rid for rid in self.current_match_rois if query_viewpoint_map[rid] == self.selected_viewpoint]
        if not self.current_query_rois or not self.current_match_rois:
            return False
        else:
            self.set_within_query_sequence(0)
            self.set_match(1)
            return True

    # RETURN INFO --------------------------------------------------------------
    def is_existing_match(self):
        """Return whether current query and match have same individual_id"""
        query_iid = self._get_roi_field(self.current_query_rid, 'individual_id')
        match_iid = self._get_roi_field(self.current_match_rid, 'individual_id')
        return query_iid == match_iid and query_iid is not None

    def both_unnamed(self):
        """Return whether both current query and match are unnamed"""
        return (self._get_roi_field(self.current_query_rid, 'individual_id') is None and
                self._get_roi_field(self.current_match_rid, 'individual_id') is None)

    def current_distance(self):
        """Return distance between current sequence and matchs"""
        lower = min(self.current_query_rid, self.current_match_rid)
        upper = max(self.current_query_rid, self.current_match_rid)
        distance = self.pair_table.loc[(self.pair_table['id1'] == lower) & (self.pair_table['id2'] == upper), 'distance']
        return distance.values[0] if not distance.empty else 0

    def _get_roi_field(self, roi_id, field):
        """Get ROI field from DataFrame (always fresh)"""
        if roi_id in self.data.index:
            return self.data.loc[roi_id, field]
        return None

    def _get_roi_full_record(self, roi_id):
        """Get full ROI record from index"""
        if roi_id in self.data.index:
            return self.data.loc[roi_id].to_dict()
        return None

    def _update_roi_index(self, updates_dict):
        """Update local index with batch changes"""
        for roi_id, changes in updates_dict.items():
            # Update DataFrame
            for key, value in changes.items():
                self.data.loc[roi_id, key] = value

    def get_info(self, rid, column=None):
        """Get info from data table for given rid and column"""
        if column is None:  # return whole row
            return self.data.loc[rid]
        elif column == 'bbox':
            # Return the bbox coordinates for current query
            return db_roi.get_roi_bbox(self.data.loc[[rid]])
        elif column == 'metadata':
            return self.roi_metadata(self.data.loc[rid])
        else:
            return self.data.loc[rid, column]

    def roi_metadata(self, roi):
        """
        Display relevant metadata in comparison label box
        """
        location = fetch_station_names_from_id(self.mpDB, roi['station_id'])

        roi = roi.rename(index={"name": "Name",
                                "sex": "Sex",
                                "age": "Age",
                                "filepath": "Filepath",
                                "comment": "Comment",
                                "timestamp": "Timestamp",
                                "station_id": "Station",
                                "sequence_id": "Sequence ID",
                                "viewpoint": "Viewpoint"})

        info_dict = roi[['Name', 'Sex', 'Age', 'Filepath', 'Timestamp', 'Station',
                         'Sequence ID', 'Viewpoint', 'Comment']].to_dict()

        info_dict['Station'] = location['station_name']
        info_dict['Survey'] = location['survey_name']
        info_dict['Region'] = location['region_name']

        # Convert viewpoint to human-readable
        viewpoint_val = info_dict['Viewpoint']
        if viewpoint_val is None or pd.isna(viewpoint_val):
            info_dict['Viewpoint'] = 'None'
        else:
            try:
                info_dict['Viewpoint'] = self.VIEWPOINT_DICT[str(int(viewpoint_val))]
            except (KeyError, ValueError, TypeError):
                info_dict['Viewpoint'] = 'Unknown'

        return info_dict

    # MATCH FUNCTIONS ----------------------------------------------------------
    def new_iid(self, individual_id):
        """
        Update records for roi after confirming a match
        """
        roi_updates = {roi: {"individual_id": individual_id, "reviewed": 1} 
                       for roi in self.current_query_rois}
        roi_updates[self.current_match_rid] = {"individual_id": individual_id, "reviewed": 1}

        # Update local index
        self._update_roi_index(roi_updates)

        # Then batch update the database
        self.mpDB.batch_edit('roi', roi_updates, quiet=True)

    def merge(self):
        """Merge two individuals after match"""
        query_data = self._get_roi_full_record(self.current_query_rid)
        match_data = self._get_roi_full_record(self.current_match_rid)

        if query_data is None or match_data is None:
            return

        query_iid = query_data.get('individual_id')
        match_iid = match_data.get('individual_id')

        # Determine which ID to keep
        if query_iid is not None:
            # keep the older one (inputted into the db first)
            keep_id = query_iid if (match_iid is None or match_iid < query_iid) else match_iid
        else:
            keep_id = match_iid

        self.mpDB.edit_row('roi', self.current_query_rid, {'individual_id': int(keep_id), "reviewed": 1}, quiet=False)
        self.mpDB.edit_row('roi', self.current_match_rid, {'individual_id': int(keep_id), "reviewed": 1}, quiet=False)

        # Update local index
        roi_updates = {
            self.current_query_rid: {'individual_id': int(keep_id), "reviewed": 1},
            self.current_match_rid: {'individual_id': int(keep_id), "reviewed": 1}
        }
        self._update_roi_index(roi_updates)

        
    def unmatch(self):
        """Unmatch the current query and match"""
        # Update local index
        self._update_roi_index({self.current_query_rid: {'individual_id': None, "reviewed": 0}})

        # Set current match id to none
        self.mpDB.edit_row('roi', self.current_query_rid,
                           {'individual_id': None, "reviewed": 0}, 
                           allow_none=True, 
                           quiet=False)
