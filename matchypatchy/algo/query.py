"""
Class Definition for Query Object
"""

import pandas as pd

import matchypatchy.database.media as db_roi

from matchypatchy.algo.match_thread import MatchEmbeddingThread
from matchypatchy.gui.popup_alert import ProgressPopup


class QueryContainer():
    def __init__(self, parent):
        self.mpDB = parent.mpDB
        self.parent = parent
        self.filters = dict()
        self.neighbor_dict = dict()
        self.nearest_dict = dict()
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
        self.selected_viewpoint = 'all'
        self.empty_query = 0
        self.empty_match = 0

    def load_data(self):
        """
        Calculates knn for all unvalidated images, ranks by smallest distance to NN
        """
        self.data_raw = db_roi.fetch_roi_media(self.mpDB)
        # no data
        if self.data_raw.empty:
            self.parent.home(warn=True)
            return False

        self.sequences = db_roi.sequence_roi_dict(self.data_raw)

        # must have embeddings to continue
        if not (self.data_raw["emb_id"] == 0).all():
            # need sequence and capture ids from media to restrict comparisons shown to
            info = "roi.id, media_id, reviewed, species_id, individual_id, emb_id, timestamp, station_id, sequence_id"
            rois, columns = self.mpDB.select_join("roi", "media", 'roi.media_id = media.id', columns=info)
            self.rois = pd.DataFrame(rois, columns=columns)
            return True
        # no embeddings
        else:
            self.parent.home(warn=True)
            return False

    # RUN ON ENTRY IF LOAD_DATA
    def calculate_neighbors(self):
        dialog = ProgressPopup(self.parent, "Matching embeddings...")
        dialog.set_max(len(self.sequences))
        dialog.show()

        self.match_thread = MatchEmbeddingThread(self.mpDB, self.rois, self.sequences,
                                                 k=self.parent.k, threshold=self.parent.threshold)
        self.match_thread.progress_update.connect(dialog.set_counter)
        self.match_thread.neighbor_dict_return.connect(self.capture_neighbor_dict)
        self.match_thread.nearest_dict_return.connect(self.capture_nearest_dict)
        self.match_thread.finished.connect(self.filter)  # do not continue until finished
        self.match_thread.start()

    def capture_neighbor_dict(self, neighbor_dict):
        # capture neighbor_dict from MatchEmbeddingThread
        self.neighbor_dict_raw = neighbor_dict

    def capture_nearest_dict(self, nearest_dict):
        # capture neighbor_dict from MatchEmbeddingThread
        self.nearest_dict_raw = nearest_dict

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
                # no valid stations, empty dataframe
            else:
                self.parent.warn("No data to compare within filter.")

        # filter neighbor dict and nearest dict
        self.neighbor_dict = {k: self.neighbor_dict_raw[k] for k in self.data.index if k in self.neighbor_dict_raw}
        self.nearest_dict = {k: self.nearest_dict_raw[k] for k in self.data.index if k in self.nearest_dict_raw}

        # compute viewpoints
        self.compute_viewpoints()
        self.compute_match_viewpoints()

        # Sort by Distance
        # must have valid matches to continue
        if self.neighbor_dict:
            self.rank()
            if reset:
                self.parent.change_query(0)
        else:
            self.parent.warn(prompt="No data to compare, all available data from same sequence/capture.")
            return False
        
    # TODO
    def rank(self):
        """
        Ranking Function
            Prioritizes previously IDd individuals and number of matches,
            then ranks matchs by distances
        """
        self.ranked_sequences = sorted(self.nearest_dict.items(), key=lambda x: x[1])
        # set number of queries to validate
        self.n_queries = len(self.ranked_sequences)
        # filtered neighbor dict returns empty, all existing data must be from same individual


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
        self.current_sequence_id = self.ranked_sequences[self.current_query][0]
        self.current_query_rois = self.sequences[self.current_sequence_id]

        # get viewpoints
        self.current_query_viewpoints = self.data.loc[self.current_query_rois, 'viewpoint']

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
        self.viewpoints = {
            'all': {},  # {sequence_id: list of ROIs}
            'left': {},
            'right': {}
        }

        for sequence_id, rois in self.sequences.items():
            all_rois = rois
            left_rois = [rid for rid in rois if self.data.loc[rid, 'viewpoint'] == 0]
            right_rois = [rid for rid in rois if self.data.loc[rid, 'viewpoint'] == 1]

            self.viewpoints['all'][sequence_id] = all_rois
            self.viewpoints['left'][sequence_id] = left_rois
            self.viewpoints['right'][sequence_id] = right_rois

    def compute_match_viewpoints(self):
        self.match_viewpoints = {
            'all': {},  # {sequence_id: list of matching ROIs}
            'left': {},
            'right': {}
        }
        for sequence_id, matches in self.neighbor_dict.items():
            all_matches = [x[0] for x in matches]
            left_matches = [rid for rid in all_matches if self.data.loc[rid, 'viewpoint'] == 0]
            right_matches = [rid for rid in all_matches if self.data.loc[rid, 'viewpoint'] == 1]

            self.match_viewpoints['all'][sequence_id] = all_matches
            self.match_viewpoints['left'][sequence_id] = left_matches
            self.match_viewpoints['right'][sequence_id] = right_matches

    def show_all_query_image(self):
        sequence_id = self.data.loc[self.current_query_rid, 'sequence_id']
        self.current_query_rois = self.viewpoints['all'].get(sequence_id, [])
        self.set_within_query_sequence(0)

    def toggle_viewpoint(self, selected_viewpoint):
        """
        Flip between viewpoints in paired images within a sequence
        """
        self.selected_viewpoint = selected_viewpoint
        self.update_viewpoint_current_query()
        self.update_viewpoint_matching_images()

    def update_viewpoint_current_query(self):
        self.empty_query = 0
        sequence_id = self.data.loc[self.current_query_rid, 'sequence_id']
        if self.selected_viewpoint == 'all':
            self.current_query_rois = self.viewpoints['all'].get(sequence_id, [])
        else:
            self.current_query_rois = self.viewpoints[self.selected_viewpoint].get(sequence_id, [])

        if self.current_query_rois:
            self.set_within_query_sequence(0)
        else:
            self.parent.warn(f'No query image with {self.selected_viewpoint} viewpoint in the current sequence. Show all viewpoints.')
            self.empty_query = 1
            # show all viewpoints
            self.current_query_rois = self.viewpoints['all'].get(sequence_id, [])
            self.set_within_query_sequence(0)

    def update_viewpoint_matching_images(self):
        self.empty_match = 0
        sequence_id = self.current_sequence_id

        if self.selected_viewpoint == 'all':
            self.current_match_rois = self.match_viewpoints['all'].get(sequence_id, [])
        else:
            self.current_match_rois = self.match_viewpoints[self.selected_viewpoint].get(sequence_id, [])

        if self.current_match_rois and self.empty_query == 0:
            self.parent.match_n.setText('/' + str(len(self.current_match_rois)))
            self.set_match(0)
        elif not self.current_match_rois and self.empty_query == 0:  # need to update query image to all viewpoints
            self.empty_match = 1
            self.parent.warn(f'No match images with {self.selected_viewpoint} viewpoint. Show all viewpoints.')
            self.current_match_rois = self.match_viewpoints['all'].get(sequence_id, [])
            self.set_match(0)
            self.parent.match_n.setText('/' + str(len(self.current_match_rois)))
            self.show_all_query_image()
        else:  # empty query
            # show all viewpoints
            self.current_match_rois = self.match_viewpoints['all'].get(sequence_id, [])
            self.set_match(0)
            self.parent.match_n.setText('/' + str(len(self.current_match_rois)))

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
    def get_query_info(self, column=None):
        if column is None:  # return whole row
            return self.data.loc[self.current_query_rid]
        elif column == 'bbox':
            # Return the bbox coordinates for current query
            return db_roi.get_bbox(self.data.loc[self.current_query_rid])
        elif column == 'metadata':
            return db_roi.roi_metadata(self.data.loc[self.current_query_rid])
        else:
            return self.data.loc[self.current_query_rid, column]

    def get_match_info(self, column=None):
        if column is None:  # return whole row
            return self.data.loc[self.current_match_rid]
        elif column == 'bbox':
            # Return the bbox coordinates for current match
            return db_roi.get_bbox(self.data.loc[self.current_match_rid])
        elif column == 'metadata':
            return db_roi.roi_metadata(self.data.loc[self.current_match_rid])
        else:
            return self.data.loc[self.current_match_rid, column]

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

        print("Merging", query_iid, match_iid)

        # query is unknown, give match name
        if query_iid is None:
            sequence = self.current_sequence_id
            keep_id = match_iid
            drop_id = None
        # match is older, update query
        elif match_iid is not None and query_iid > match_iid:
            sequence = self.current_sequence_id
            keep_id = match_iid
            drop_id = query_iid
        # query is older or match is None update match
        else:
            sequence = match['sequence_id']
            keep_id = query_iid
            drop_id = match_iid

        # find all rois with newer name
        to_merge = self.data[self.data["sequence_id"] == sequence]

        for i in to_merge.index:
            self.mpDB.edit_row('roi', i, {'individual_id': int(keep_id)}, quiet=False)
