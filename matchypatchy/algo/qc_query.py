"""
Class Definition for Query Object
"""

import matchypatchy.database.media as db_roi
from matchypatchy.database.location import fetch_station_names_from_id
from matchypatchy.algo.models import load


class QC_QueryContainer():
    """
    Alternate Query Container for QC Only
    """
    def __init__(self, parent):
        self.mpDB = parent.mpDB
        self.parent = parent
        self.filters = dict()
        self.neighbor_dict = dict()
        self.nearest_dict = dict()
        self.ranked_sequences = []
        self.VIEWPOINT_DICT = load('VIEWPOINTS')

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

    def load_data(self):
        """
        Load ROI Table
        """
        self.data_raw = db_roi.fetch_roi_media(self.mpDB)
        # no data
        if self.data_raw.empty:
            self.parent.home(warn=True)
            return False

        self.individuals = db_roi.individual_roi_dict(self.data_raw)
        self.individuals.pop(None, None)

    # STEP 2
    def filter(self, filter_dict=None, valid_stations=None, reset=True):
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
                self.parent.warn("No data to compare within filter.")

        # compute viewpoints
        self.compute_viewpoints()

        # Sort by Distance
        # must have valid matches to continue
        if self.individuals:
            self.rank()
            if reset:
                self.parent.change_query(0)
        # filtered neighbor dict returns empty, all existing data must be from same individual
        else:
            self.parent.warn(prompt="No data to compare, all available data from same sequence/capture.")
            return False

    def rank(self):
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
        self.current_sequence_id = self.ranked_sequences[self.current_query][0]
        self.current_query_rois = self.individuals[self.current_sequence_id]

        # set view to first in sequence
        self.set_within_query_sequence(0)

        # update matches
        self.update_matches()

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
    def update_matches(self):
        """
        Update match list if current_query changes
        """
        # get all matches for query
        self.current_match_rois = self.individuals[self.current_sequence_id]

        # set to top of matches, skip the first one which will be on the query side
        self.set_match(1)

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
    def compute_viewpoints(self):
        self.viewpoints = {x: dict() for x in self.VIEWPOINT_DICT.values()}
        for iid, rois in self.individuals.items():
            for key, value in self.VIEWPOINT_DICT.items():
                if key == "Any":
                    self.viewpoints[value][iid] = rois
                else:
                    try:
                        self.viewpoints[value][iid] = [rid for rid in rois if str(self.data.loc[rid, 'viewpoint']) == key]
                    except KeyError:
                        self.viewpoints[value][iid] = []

    def toggle_viewpoint(self, selected_viewpoint):
        """
        Flip between viewpoints in paired images within a sequence
        """
        self.VIEWPOINT_DICT.values()
        self.selected_viewpoint = selected_viewpoint

        self.update_viewpoint()

    def update_viewpoint(self):
        self.empty_query = False
        if self.selected_viewpoint == 'Any':
            self.current_query_rois = self.viewpoints['Any'].get(self.current_sequence_id, [])
            self.current_match_rois = self.viewpoints['Any'].get(self.current_sequence_id, [])
        else:
            self.current_query_rois = self.viewpoints[self.selected_viewpoint].get(self.current_sequence_id, [])
            self.current_match_rois = self.viewpoints[self.selected_viewpoint].get(self.current_sequence_id, [])

        if self.current_query_rois:
            self.set_within_query_sequence(0)
        else:
            self.empty_query = True
            # show all viewpoints
            self.current_query_rois = self.viewpoints['Any'].get(self.current_sequence_id, [])
            self.current_match_rois = self.viewpoints['Any'].get(self.current_sequence_id, [])
            self.set_within_query_sequence(0)

    # RETURN INFO --------------------------------------------------------------
    def is_existing_match(self):
        return self.data.loc[self.current_query_rid, "individual_id"] == self.data.loc[self.current_match_rid, "individual_id"] and \
            self.data.loc[self.current_query_rid, "individual_id"] is not None

    def get_info(self, rid, column=None):
        if column is None:  # return whole row
            return self.data.loc[rid]
        elif column == 'bbox':
            # Return the bbox coordinates for current query
            return db_roi.get_bbox(self.data.loc[rid])
        elif column == 'metadata':
            return self.roi_metadata(self.data.loc[rid])
        else:
            return self.data.loc[rid, column]

    def current_distance(self):
        return 0

    def roi_metadata(self, roi):
        """
        Display relevant metadata in comparison label box
        """
        location = fetch_station_names_from_id(self.mpDB, roi['station_id'])
        if roi['species_id'] is not None:
            binomen, common = self.mpDB.select("station", "binomen, common", row_cond=f"id={roi['species_id']}")[0]
        else:
            common = 'Not Specified'

        roi = roi.rename(index={"name": "Name",
                                "species_id": "Species",
                                "sex": "Sex",
                                "age": "Age",
                                "filepath": "File Path",
                                "comment": "Comment",
                                "timestamp": "Timestamp",
                                "station_id": "Station",
                                "sequence_id": "Sequence ID",
                                "viewpoint": "Viewpoint"})

        info_dict = roi[['Name', 'Species', 'Sex', 'Age', 'File Path', 'Timestamp', 'Station',
                        'Sequence ID', 'Viewpoint', 'Comment']].to_dict()
                
        info_dict['Station'] = location['station_name']
        info_dict['Survey'] = location['survey_name']
        info_dict['Region'] = location['region_name']
        info_dict['Species'] = common

        # convert viewpoint to human-readable (0=Left, 1=Right)
        VIEWPOINT = load('VIEWPOINTS')
        if info_dict['Viewpoint'] is None:
            info_dict['Viewpoint'] = 'None'
        else:  # BUG: Typecasting issue, why is viewpoint returning a float?
            info_dict['Viewpoint'] = VIEWPOINT[str(int(info_dict['Viewpoint']))]

        return info_dict

    # MATCH FUNCTIONS ----------------------------------------------------------
    def new_iid(self, individual_id):
        """
        Update records for roi after confirming a match
        """
        for roi in self.current_query_rois:
            self.mpDB.edit_row('roi', roi, {"individual_id": individual_id, "reviewed": 1})

        self.mpDB.edit_row('roi', self.current_match_rid, {"individual_id": individual_id, "reviewed": 1})

    def unmatch(self):
        # Set current match id to none
        self.mpDB.edit_row('roi', self.current_match_rid, {'individual_id': None}, quiet=False)
