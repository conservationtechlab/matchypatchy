"""
Class Definition for Query Object
"""
from PyQt6.QtCore import QObject, pyqtSignal

import matchypatchy.database.media as db_roi
from matchypatchy.database.location import fetch_station_names_from_id

from matchypatchy.algo.models import load
from matchypatchy.algo.match_thread import MatchEmbeddingThread


# TODO: sequences for videos 
class QueryContainer(QObject):
    thread_signal = pyqtSignal(bool)

    def __init__(self, parent):
        super().__init__()
        self.mpDB = parent.mpDB
        self.parent = parent
        self.metric = parent.distance_metric
        self.k = parent.k
        self.threshold = parent.threshold
        self.filter_dict = dict()
        self.VIEWPOINT_DICT = load('VIEWPOINTS')

        self.neighbor_dict = dict()
        self.ranked_sequences = []

        self.current_query = 0
        self.current_match = 0
        self.current_query_sn = 0
        self.n_queries = 0

        # ROI REFERENCE
        self.current_query_rid = 0
        self.current_match_rid = 0

        self.viewpoints = {}
        self.match_viewpoints = {}
        self.selected_viewpoint = 'Any'
        self.empty_query = 0
        self.empty_match = 0

    # STEP 0
    def load_data(self):
        """
        Calculates knn for all unvalidated images, ranks by smallest distance to NN
        """
        self.data_raw = db_roi.fetch_roi_media(self.mpDB)
        # no data
        if self.data_raw.empty:
            return False

        # must have embeddings to continue
        if not (self.data_raw["emb"] == 0).all():
            # need sequence and capture ids from media to restrict comparisons shown to
            return True
        # no embeddings
        else:
            return False
        
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
                # no valid stations, empty dataframe
            else:
                self.parent.show_progress("No data to compare within filter.")

        self.sequences = db_roi.sequence_roi_dict(self.data)


    # RUN ON ENTRY IF LOAD_DATA
    def calculate_neighbors(self):
        self.match_thread = MatchEmbeddingThread(self.mpDB, self.data, self.sequences,
                                                 k=self.k, metric=self.metric, threshold=self.threshold)
        self.match_thread.progress_update.connect(self.parent.progress.set_counter)
        self.match_thread.prompt_update.connect(self.parent.progress.update_prompt)
        self.match_thread.neighbor_dict_return.connect(self.capture_neighbor_dict)
        self.match_thread.ranked_sequences_return.connect(self.capture_ranked_sequences)
        self.match_thread.finished.connect(self.finish_calculating)  # do not continue until finished
        self.match_thread.start()

    def capture_neighbor_dict(self, neighbor_dict):
        # capture neighbor_dict from MatchEmbeddingThread
        self.neighbor_dict = neighbor_dict

    def capture_ranked_sequences(self, ranked_sequences):
        # capture ranked_sequences from MatchEmbeddingThread
        self.ranked_sequences = ranked_sequences
        # set number of queries to validate
        self.n_queries = len(self.ranked_sequences)

    def finish_calculating(self):
        if self.neighbor_dict:
            # compute viewpoints
            self.compute_viewpoints()
            self.compute_match_viewpoints()
            self.thread_signal.emit(True)
        else:
            # interrupt occurred, dicts are empty
            self.thread_signal.emit(False)

    def set_query(self, n):
        """
        Set the Query side to a particular (n) image in the list
        """
        # wrap around
        if n < 0:
            n = self.n_queries - 1
        if n > self.n_queries - 1:
            n = 0

        # set current query
        self.current_query = n

        # get corresponding sequence_id and rois
        self.current_sequence_id = self.ranked_sequences[self.current_query]
        self.current_query_rois = self.sequences[self.current_sequence_id]

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

        self.current_query_sn = n  # number within sequence
        self.current_query_rid = self.current_query_rois[self.current_query_sn]

    # refresh match list
    def update_matches(self):
        """
        Update match list if current_query changes
        """
        # get all matches for query
        full_match_set = self.neighbor_dict[self.current_sequence_id]
        self.current_match_rois = [x[0] for x in full_match_set]

        # set to top of matches
        self.set_match(0)

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

        for sequence_id, rois in self.sequences.items():
            for key, value in self.VIEWPOINT_DICT.items():
                if key == "Any":
                    self.viewpoints[value][sequence_id] = rois
                else:
                    try:
                        self.viewpoints[value][sequence_id] = [rid for rid in rois if str(self.data.loc[rid, 'viewpoint']) == key]
                    except KeyError:
                        self.viewpoints[value][sequence_id] = []

    def compute_match_viewpoints(self):
        self.match_viewpoints = {x: dict() for x in self.VIEWPOINT_DICT.values()}

        for sequence_id, matches in self.neighbor_dict.items():
            all_matches = [x[0] for x in matches]
            for key, value in self.VIEWPOINT_DICT.items():
                if key == "Any":
                    self.match_viewpoints[value][sequence_id] = all_matches
                else:
                    try:
                        self.match_viewpoints[value][sequence_id] = [rid for rid in all_matches if str(self.data.loc[rid, 'viewpoint']) == key]
                    except KeyError:
                        self.match_viewpoints[value][sequence_id] = []

    def show_all_query_image(self):
        """
        Show All Viewpoints for Query
        """
        self.current_query_rois = self.viewpoints['Any'].get(self.current_sequence_id, [])
        self.set_within_query_sequence(0)

    def toggle_viewpoint(self, selected_viewpoint):
        """
        Flip between viewpoints in paired images within a sequence
        """
        self.selected_viewpoint = selected_viewpoint
        self.update_viewpoint_current_query()
        self.update_viewpoint_matching_images()

    def update_viewpoint_current_query(self):
        # Sets Query to Display Only Selected Viewpoint
        self.empty_query = False
        if self.selected_viewpoint == 'Any':
            self.current_query_rois = self.viewpoints['Any'].get(self.current_sequence_id, [])
        else:
            self.current_query_rois = self.viewpoints[self.selected_viewpoint].get(self.current_sequence_id, [])

        if self.current_query_rois:
            self.set_within_query_sequence(0)
        else:
            self.empty_query = True
            # show all viewpoints
            self.current_query_rois = self.viewpoints['Any'].get(self.current_sequence_id, [])
            self.set_within_query_sequence(0)

    def update_viewpoint_matching_images(self):
        # Sets Match to Display Only Selected Viewpoint
        self.empty_match = False
        if self.selected_viewpoint == 'Any':
            self.current_match_rois = self.match_viewpoints['Any'].get(self.current_sequence_id, [])
        else:
            self.current_match_rois = self.match_viewpoints[self.selected_viewpoint].get(self.current_sequence_id, [])

        if self.current_match_rois and self.empty_query is False:
            self.set_match(0)
        elif not self.current_match_rois and self.empty_query is False:  # need to update query image to all viewpoints
            self.empty_match = True
            self.current_match_rois = self.match_viewpoints['Any'].get(self.current_sequence_id, [])
            self.set_match(0)
            self.show_all_query_image()
        else:  # empty query
            # show all viewpoints
            self.current_match_rois = self.match_viewpoints['Any'].get(self.current_sequence_id, [])
            self.set_match(0)

    # RETURN INFO --------------------------------------------------------------------
    def is_existing_match(self):
        return self.data.loc[self.current_query_rid, "individual_id"] == self.data.loc[self.current_match_rid, "individual_id"] and \
            self.data.loc[self.current_query_rid, "individual_id"] is not None

    def both_unnamed(self):
        """
        Both are unnamed
        """
        return self.data.loc[self.current_match_rid, "individual_id"] is None and \
            self.data.loc[self.current_query_rid, "individual_id"] is None

    def current_distance(self):
        # return distance between current sequence and matchs
        return self.neighbor_dict[self.current_sequence_id][self.current_match][1]

    # Accessing Info
    def get_info(self, rid, column=None):
        if column is None:  # return whole row
            return self.data.loc[rid]
        elif column == 'bbox':
            # Return the bbox coordinates for current query
            return db_roi.get_bbox(self.data.loc[[rid]])
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
                                "filepath": "File Path",
                                "comment": "Comment",
                                "timestamp": "Timestamp",
                                "station_id": "Station",
                                "sequence_id": "Sequence ID",
                                "viewpoint": "Viewpoint"})

        info_dict = roi[['Name', 'Sex', 'Age', 'File Path', 'Timestamp', 'Station',
                        'Sequence ID', 'Viewpoint', 'Comment']].to_dict()
                
        info_dict['Station'] = location['station_name']
        info_dict['Survey'] = location['survey_name']
        info_dict['Region'] = location['region_name']

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

    def merge(self):
        """
        Merge two individuals after match
        """
        query = self.data.loc[self.current_query_rid]
        match = self.data.loc[self.current_match_rid]

        query_iid = query['individual_id']
        match_iid = match['individual_id']


        # both are named
        if query_iid is not None:
            # query is older, keep query name
            if match_iid is None or match_iid < query_iid:
                sequence = [match['sequence_id']]
                keep_id = query_iid

            # match is older, keep match name
            else:
                sequence = [self.current_sequence_id]
                keep_id = match_iid

        # query is None, give match name
        else:
            sequence = [self.current_sequence_id]
            keep_id = match_iid

        # find all rois with newer name
        to_merge = self.data[self.data["sequence_id"].isin(sequence)]

        for i in to_merge.index:
            self.mpDB.edit_row('roi', i, {'individual_id': int(keep_id)}, quiet=False)

    def unmatch(self):
        """
        Unmatch the current query ROI from the matched ROI

        TODO: HOW TO HANDLE?
        """
        self.mpDB.edit_row('roi', self.current_match_rid, {'individual_id': None}, quiet=False)
