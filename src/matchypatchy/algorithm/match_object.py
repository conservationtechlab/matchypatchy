"""
Class definition for MatchObject and FavoriteMatchObject
"""
import pandas as pd

from matchypatchy.models import toggle_viewpoint_value


class MatchObject():
    """
    Class definition for MatchObject, contains all matches for a given query sequence
    """
    def __init__(self, query_sequence_id, filtered_neighbors, query_data, match_data):
        self.query_sequence_id = query_sequence_id
        self.neighbors = filtered_neighbors
        # truncated roi data for the query sequence and matched sequences
        self.query_data = query_data
        self.match_data = match_data

        self.query_viewpoint_map = {}
        self.match_viewpoint_map = {}

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

    def rank_sequences(self, rois, sequences, favorite_rids, ided_rids):
        """
        Pad matches to whole sequences and rank the sequences: IDed first, then
        favorited, then nearest. Rois within a sequence keep their sequence order.

        Called by MatchEmbeddingThread.rank before order_matches_by_viewpoint.
        Ranks whole sequences rather than single rois so the sequence distance is
        its nearest roi and a favorite/IDed roi anywhere in the sequence lifts it.
        """
        seq_of = rois.set_index('id')['sequence_id']
        # candidate key -> (member rois in sequence order, nearest distance)
        candidates = {}
        for rid, distance in self.neighbors.items():
            # get the sequence ID for the current ROI
            seq = seq_of.get(rid)
            # a roi without a sequence (null sequence_id) stands alone
            key, members = (('roi', rid), [rid]) if pd.isna(seq) else (seq, sequences.get(seq) or [rid])
            # update the candidate with the current ROI and distance if it's lower than the existing candidate
            if key not in candidates or distance < candidates[key][1]:
                candidates[key] = (members, distance)

        # sort neighbors by IDed status, then by favorite status, then by distance
        ranked = sorted(candidates.values(),
                        key=lambda c: (not any(r in ided_rids for r in c[0]),
                                       not any(r in favorite_rids for r in c[0]),
                                       c[1])) # distance
        self.neighbors = [(rid, distance) for members, distance in ranked for rid in members]
        self.query_data = rois[rois['id'].isin(self.query_data['id'])][['id', 'viewpoint']]
        self.match_data = rois[rois['id'].isin([x[0] for x in self.neighbors])][['id', 'viewpoint']]

    def order_matches_by_viewpoint(self):
        """
        Order query rois by viewpoint overlap; matches keep their ranked sequence order
        """
        self.zip_viewpoint()
        viewpoint_matches = {x for x in self.query_data['viewpoint'].values if x in self.match_data['viewpoint'].values}
        viewpoint_matches.discard(None)  # remove unknown viewpoint category

        self.og_ranked_query_rids = sorted(self.query_data['id'].values.astype(int).tolist(),
                                           key=lambda x: self.query_viewpoint_map[x] in viewpoint_matches,
                                           reverse=True)
        # whole sequences in rank order; show_viewpoint filters this without reordering
        self.og_ranked_matches = list(self.neighbors)
        self.ranked_matches = self.og_ranked_matches
        self.ranked_query_rids = self.og_ranked_query_rids

    def zip_viewpoint(self):
        """Create dictionaries mapping ROI IDs to viewpoints for query and match data"""
        self.query_viewpoint_map = dict(zip(self.query_data['id'], self.query_data['viewpoint']))
        self.match_viewpoint_map = dict(zip(self.match_data['id'], self.match_data['viewpoint']))

    def show_viewpoint(self, selected_viewpoint):
        """
        Show only rois of the selected side (toggle 0 Left, 1 Any, 2 Right), in
        ranked sequence order. Returns False and leaves the shown rois unchanged
        when the query or the match stack has no rois of that side.
        """
        self.zip_viewpoint()
        # set back to all viewpoints
        if selected_viewpoint == 1:
            self.ranked_matches = self.og_ranked_matches
            self.ranked_query_rids = self.og_ranked_query_rids
            return True

        # get viewpoint selected value
        value = toggle_viewpoint_value(selected_viewpoint)
        available_queries = [rid for rid in self.og_ranked_query_rids if self.query_viewpoint_map.get(rid) == value]
        available_matches = [match for match in self.og_ranked_matches if self.match_viewpoint_map.get(match[0]) == value]
        if value is None or not available_queries or not available_matches:
            return False

        self.ranked_query_rids = available_queries
        self.ranked_matches = available_matches
        return True

class FavoriteMatchObject():
    """
    Class definition for FavoriteMatchObject, contains all favorited ROIS
    """
    def __init__(self, query_sequence_id, filtered_neighbors, query_data, match_data):
        self.query_sequence_id = query_sequence_id
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
            self.order_matches_by_viewpoint()

        return self.ranked_query_rids

    def get_ranked_matches(self):
        if not self.ranked_matches:
            self.order_matches_by_viewpoint()

        return self.ranked_matches

    def order_matches_by_viewpoint(self):
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
            selected_viewpoint = toggle_viewpoint_value(selected_viewpoint)
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