"""
Class definition for MatchObject and FavoriteMatchObject
"""


class MatchObject():
    """
    Class definition for MatchObject, contains all matches for a given query sequence
    """
    def __init__(self, sequence_id, filtered_neighbors, query_data, match_data):
        self.sequence_id = sequence_id  # ID of the query sequence
        self.neighbors = filtered_neighbors  # valid matches, will padded with full sequences
        self.query_data = query_data  # query ROI rows
        self.match_data = match_data  # match ROI rois

        self.zip_viewpoint()  # create dict of id:viewpoints for both sides

        self.ranked_query_rids = []  # ranked query ROI IDs after ordering by viewpoint
        self.ranked_matches = []  # ranked match tuples (roi_id, distance) after ordering by viewpoint

        self.og_ranked_query_rids = []  # original ranked query ROI IDs
        self.og_ranked_matches = []  # original ranked match tuples (roi_id, distance)

    def get_ranked_query_rids(self):
        """Get the ranked query ROI IDs"""
        return self.ranked_query_rids

    def get_ranked_matches(self):
        """Get the ranked match tuples (roi_id, distance)"""
        return self.ranked_matches

    def rank_neighbors_by_distance(self):
        """Rank matches by distance"""
        self.neighbors = sorted(self.neighbors, key=lambda x: x[1])

    def rank_neighbors_by_favorites(self, favorite_rois):
        """Rank matches by favorites"""
        self.neighbors = sorted(self.neighbors, key=lambda x: (x[0] not in favorite_rois))

    def rank_neighbors_by_ided(self, ided_rois):
        """Rank matches by IDed status"""
        self.neighbors = sorted(self.neighbors, key=lambda x: (x[0] not in ided_rois))

    def pad_sequences(self, rois, sequences):
        """
        For each remaining match, add the rest of the sequence to the match stack
        and move existing sequence matches to the appropriate position
        """
        matched_rois = [item[0] for item in self.neighbors]
        new_stack = []  # match stack after padding
        to_remove = []
        match_sequence_rois = {}
        distances = {}
        for i, match in enumerate(matched_rois):
            match_sequence_id = rois.loc[rois['id'] == match, 'sequence_id'].values[0]
            match_sequence_rois[match] = sequences[match_sequence_id]
            distances[match] = self.neighbors[i][1]
            for roi in match_sequence_rois[match]:
                # check if match sequence appears later in match stack
                if roi in matched_rois[i + 1:]:
                    to_remove.append(roi)

        # rebuild match stack with padded sequences, using lowest distance match as anchor
        for match in matched_rois:
            if match not in to_remove:
                for roi in match_sequence_rois[match]:
                    new_stack.append((roi, distances[match]))

        # replace info with new padded stack
        self.neighbors = new_stack
        self.query_data = rois[rois['id'].isin(self.query_data['id'])][['id', 'viewpoint']]
        self.match_data = rois[rois['id'].isin([x[0] for x in self.neighbors])][['id', 'viewpoint']]

    def zip_viewpoint(self):
        """Create dictionaries mapping ROI IDs to viewpoints for query and match data"""
        self.query_viewpoint_map = dict(zip(self.query_data['id'], self.query_data['viewpoint']))
        self.match_viewpoint_map = dict(zip(self.match_data['id'], self.match_data['viewpoint']))

    def order_matches(self):
        """
        Order neighbors by viewpoint for both query and match data
        """
        # rezip in case data has changed
        self.zip_viewpoint()

        # determine viewpoint matches between query sequence and matched sequence
        viewpoint_matches = {x for x in self.query_data['viewpoint'].values if x in self.match_data['viewpoint'].values}
        viewpoint_matches.discard(None)  # remove unknown viewpoint category

        # reorder query sequence by viewpoint
        self.og_ranked_query_rids = sorted(self.query_data['id'].values.astype(int).tolist(),
                                           key=lambda x: self.query_viewpoint_map[x] in viewpoint_matches,
                                           reverse=True)
        # reorder matches by viewpoint
        self.og_ranked_matches = sorted(self.neighbors,
                                        key=lambda x: (self.match_viewpoint_map[x[0]] if self.match_viewpoint_map[x[0]] in viewpoint_matches
                                                       else float('inf')))
        self.ranked_matches = self.og_ranked_matches
        self.ranked_query_rids = self.og_ranked_query_rids

    def show_viewpoint(self, selected_viewpoint):
        """
        Toggle between viewpoints in match stack
        """
        # rezip in case data has changed
        self.zip_viewpoint()
        # reset to og order
        if selected_viewpoint == 1:
            self.ranked_matches = self.og_ranked_matches
            self.ranked_query_rids = self.og_ranked_query_rids
            return True
        else:
            selected_viewpoint = 1 if selected_viewpoint == 2 else selected_viewpoint  # adjust for 1:any indexing in GUI
            available_queries = [rid for rid in self.og_ranked_query_rids if self.query_viewpoint_map[rid] == selected_viewpoint]
            available_matches = [match for match in self.og_ranked_matches if self.match_viewpoint_map[match[0]] == selected_viewpoint]

            # if no matches or query rois for selected viewpoint, show all matches and query rois
            if len(available_matches) == 0 or len(available_queries) == 0:
                self.ranked_matches = self.og_ranked_matches
                self.ranked_query_rids = self.og_ranked_query_rids
                return False
            else:
                self.ranked_query_rids = available_queries
                self.ranked_matches = available_matches
                return True


class FavoriteMatchObject():
    """
    Class definition for FavoriteMatchObject, contains all favorited ROIS
    """
    def __init__(self, sequence_id, filtered_neighbors, query_data, match_data):
        self.sequence_id = sequence_id
        self.query_data = query_data
        self.match_data = match_data
        self.neighbors = filtered_neighbors  # favorited rois and precalced distances

        # rank by distance first
        self.zip_viewpoint()

        self.ranked_query_rids = []
        self.ranked_matches = []

        self.og_ranked_query_rids = []
        self.og_ranked_matches = []

    def update(self, new_data):
        self.neighbors = new_data[new_data['favorite'] == 1]

    def zip_viewpoint(self):
        self.query_viewpoint_map = dict(zip(self.query_data['id'], self.query_data['viewpoint']))
        self.match_viewpoint_map = dict(zip(self.match_data.index, self.match_data['viewpoint']))

    def get_ranked_query_rids(self):
        if not self.ranked_query_rids:
            self.order_matches()

        return self.ranked_query_rids

    def get_ranked_matches(self):
        if not self.ranked_matches:
            self.order_matches()

        return self.ranked_matches

    def order_matches(self):
        """
        Order neighbors by viewpoint
        """
        # rezip in case data has changed
        self.zip_viewpoint()

        # determine viewpoint matches between query sequence and matched sequence
        viewpoint_matches = {x for x in self.query_data['viewpoint'].values if x in self.match_data['viewpoint'].values}
        viewpoint_matches.discard(None)  # remove unknown viewpoint category

        # reorder query sequence by viewpoint
        self.og_ranked_query_rids = sorted(self.query_data['id'].values.astype(int).tolist(),
                                           key=lambda x: self.query_viewpoint_map[x] in viewpoint_matches,
                                           reverse=True)
        # reorder matches by viewpoint
        self.og_ranked_matches = sorted(self.neighbors,
                                        key=lambda x: (self.match_viewpoint_map[x[0]] if self.match_viewpoint_map[x[0]] in viewpoint_matches
                                                       else float('inf')))
        self.ranked_matches = self.og_ranked_matches
        self.ranked_query_rids = self.og_ranked_query_rids

    def show_viewpoint(self, selected_viewpoint):
        """
        Toggle between viewpoints in match stack
        """
        # rezip in case data has changed
        self.zip_viewpoint()
        # reset to og order
        if selected_viewpoint == 1:
            self.ranked_matches = self.og_ranked_matches
            self.ranked_query_rids = self.og_ranked_query_rids
            return True
        else:
            selected_viewpoint = 1 if selected_viewpoint == 2 else selected_viewpoint  # adjust for 1:any indexing in GUI
            available_queries = [rid for rid in self.og_ranked_query_rids if self.query_viewpoint_map[rid] == selected_viewpoint]
            available_matches = [match for match in self.og_ranked_matches if self.match_viewpoint_map[match[0]] == selected_viewpoint]

            # if no matches or query rois for selected viewpoint, show all matches and query rois
            if len(available_matches) == 0 or len(available_queries) == 0:
                self.ranked_matches = self.og_ranked_matches
                self.ranked_query_rids = self.og_ranked_query_rids
                return False
            else:
                self.ranked_query_rids = available_queries
                self.ranked_matches = available_matches
                return True
