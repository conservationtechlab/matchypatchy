"""
Class Definition for Query Object
"""

import pandas as pd

import matchypatchy.database.roi as db_roi
from matchypatchy.database.individual import merge


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
            info = "roi.id, media_id, reviewed, species_id, individual_id, emb_id, timestamp, site_id, sequence_id"
            # need sequence and capture ids from media to restrict comparisons shown to
            rois, columns = self.mpDB.select_join("roi", "media", 'roi.media_id = media.id', columns=info)
            self.rois = pd.DataFrame(rois, columns=columns)
            return True
        # no embeddings
        else:
            self.parent.home(warn=True)
            return False
        
    def calculate_neighbors(self):
        print("start")
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
    def filter(self, filter_dict=None, valid_sites=None):
        """
        Filter media based on active survey selected in dropdown of DisplayMedia
        Triggered by calculate neighbors and change in filters

        if filter > 0 : use id
        if filter == 0: do not filter
        """
        # create backups for filtering
        self.data = self.data_raw.copy()

        if filter_dict is not None and valid_sites is not None:
            # Region Filter (depends on prefilterd sites from MediaDisplay)
            if filter_dict['active_region'][0] > 0 and valid_sites:
                self.data = self.data[self.data['site_id'].isin(list(valid_sites.keys()))]
        
            # Survey Filter (depends on prefilterd sites from MediaDisplay)
            if filter_dict['active_survey'][0] > 0 and valid_sites:
                self.data = self.data[self.data['site_id'].isin(list(valid_sites.keys()))]

            # Single Site Filter
            if filter_dict['active_site'][0] > 0 and valid_sites:
                self.data = self.data[self.data['site_id'] == filter_dict['active_site'][0]]
            elif filter_dict['active_site'][0] == 0 and valid_sites:
                self.data = self.data[self.data['site_id'].isin(list(valid_sites.keys()))]
                # no valid sites, empty dataframe
            else:
                self.parent.warn("No data to compare within filter.")
        
        # filter neighbor dict and nearest dict
        self.neighbor_dict = {k: self.neighbor_dict_raw[k] for k in self.data.index if k in self.neighbor_dict_raw}
        self.nearest_dict = {k: self.nearest_dict_raw[k] for k in self.data.index if k in self.nearest_dict_raw}

        # Sort by Distance
        # must have valid matches to continue
        if self.neighbor_dict:
            self.ranked_sequences = sorted(self.nearest_dict.items(), key=lambda x: x[1])
            # set number of queries to validate
            self.n_queries = len(self.neighbor_dict)
            self.reset_query()
        # filtered neighbor dict returns empty, all existing data must be from same individual
        else:
            self.parent.warn(prompt="No data to compare, all available data from same sequence/capture.")
            return False
        
    def reset_query(self):
        # Run on entry
        self.parent.change_query(0)

    def set_query(self, n):
        """
        Set the Query side to a particular (n) image in the list
        """
        # wrap around
        if n < 0: n = self.n_queries - 1
        if n > self.n_queries - 1: n = 0

        # set current query
        self.current_query = n

        # get corresponding sequence_id and rois
        self.current_sequence_id = self.ranked_sequences[self.current_query][0]
        self.current_query_rois = self.sequences[self.current_sequence_id]
        print("query rois:", self.current_query_rois)

        # get viewpoints
        self.current_query_viewpoints = self.data.loc[self.current_query_rois, 'viewpoint']
        print(self.current_query_viewpoints)
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
        if n < 0: n = len(self.current_query_rois) - 1
        if n > len(self.current_query_rois) - 1: n = 0
        
        self.current_query_sn = n  # number within sequence
        self.current_query_rid = self.current_query_rois[self.current_query_sn]

    # refresh match list
    def update_matches(self):
        """
        Update match list if current_query changes
        """
        # get all matches for query
        full_match_set = self.neighbor_dict[self.current_sequence_id]
        print(full_match_set)
        self.current_match_rois = [x[0] for x in full_match_set]

        print("match rois:", self.current_match_rois)
        # set to top of matches
        self.set_match(0)

    def set_match(self, n):
        """
        Set the curent match index and id 
        """
        # wrap around
        if n < 0: n = len(self.current_match_rois) - 1
        if n > len(self.current_match_rois) - 1: n = 0

        self.current_match = n
        self.current_match_rid = self.current_match_rois[self.current_match]

    # VIEWPOINT TOGGLE
    def toggle_viewpoint(self):
        """
        Flip between viewpoints in paired images within a sequence
        """
        pass

    def is_match(self):
        return self.data.loc[self.current_query_rid, "individual_id"] == self.data.loc[self.current_match_rid, "individual_id"] and \
            self.data.loc[self.current_query_rid, "individual_id"] is not None

    def new_match(self):
        """
        Match button was clicked, merge query sequence and current match
        """
        # Both individual_ids are None
        if self.data.loc[self.current_query_rid, "individual_id"] == self.data.loc[self.current_match_rid, "individual_id"] and \
           self.data.loc[self.current_query_rid, "individual_id"] is None:
            # make new individual
            dialog = IndividualFillPopup(self)
            if dialog.exec():
                individual_id = self.mpDB.add_individual(dialog.get_species_id(), dialog.get_name(), dialog.get_sex())
                # update query and match
                self.mpDB.edit_row('roi', self.current_query_rid, {"individual_id": individual_id})
                self.mpDB.edit_row('roi', self.current_match_rid, {"individual_id": individual_id})
            del dialog
            # update data  
            self.data = db_roi.fetch_roi_media(self.mpDB)
            self.load_query()
            self.load_match()

        # Match has a name
        else:
            merge(self.mpDB, self.data, self.current_query_rois, self.current_match_rid)
            # update data  
            self.data = db_roi.fetch_roi_media(self.mpDB)
            self.load_query()
            self.load_match()

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
            return self.data.loc[self.current_query_rid, column]
