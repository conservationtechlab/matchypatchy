"""
Class definition for MatchObject and FavoriteMatchObject
"""
import pandas as pd

class MatchObject():
    """
    Class definition for MatchObject, contains all matches for a given query sequence
    """
    def __init__(self, sequence_id, filtered_neighbors, query_data, match_data):
        self.sequence_id = sequence_id
        self.neighbors = filtered_neighbors
        self.query_data = query_data
        self.match_data = match_data

        # Cache viewpoint maps to avoid re-zipping
        self._viewpoint_cache_valid = False
        self.query_viewpoint_map = {}
        self.match_viewpoint_map = {}
        self._invalidate_cache()

        self.ranked_query_rids = []  # ranked query ROI IDs after ordering by viewpoint
        self.ranked_matches = []  # ranked match tuples (roi_id, distance) after ordering by viewpoint

        self.og_ranked_query_rids = []  # original ranked query ROI IDs
        self.og_ranked_matches = []  # original ranked match tuples (roi_id, distance)

    def _invalidate_cache(self):
        """Invalidate cache and rebuild viewpoint maps with None handling"""
        self.query_viewpoint_map = self._build_safe_viewpoint_map(self.query_data['id'], self.query_data['viewpoint'])
        self.match_viewpoint_map = self._build_safe_viewpoint_map(self.match_data.index, self.match_data['viewpoint'])
        self._viewpoint_cache_valid = True

    def _build_safe_viewpoint_map(self, ids, viewpoints):
        """
        Build viewpoint map with None values converted to a sort-safe high value.
        This centralizes None handling instead of spreading it through sort keys.
        """
        return {roi_id: (vp if vp is not None else float('inf')) for roi_id, vp in zip(ids, viewpoints)} 

    def get_ranked_query_rids(self):
        """Get the ranked query ROI IDs"""
        return self.ranked_query_rids

    def get_ranked_matches(self):
        """Get the ranked match tuples (roi_id, distance)"""
        return self.ranked_matches

    def rank_neighbors_by_distance(self):
        """Rank by distance"""
        self.neighbors = sorted(self.neighbors, key=lambda x: x[1])

    def rank_neighbors_by_favorites(self, favorite_rois):
        """Rank by favorites"""
        favorite_set = set(favorite_rois)  # Convert to set for O(1) lookup
        self.neighbors = sorted(self.neighbors, key=lambda x: x[0] not in favorite_set)

    def rank_neighbors_by_ided(self, ided_rois):
        """Rank by IDed status"""
        ided_set = set(ided_rois)  # Convert to set for O(1) lookup
        self.neighbors = sorted(self.neighbors, key=lambda x: x[0] not in ided_set)

    def pad_sequences(self, rois, sequences):
        """
        For each remaining match, add the rest of the sequence to the match stack
        and move existing sequence matches to the appropriate position
        """
        matched_rois = [item[0] for item in self.neighbors]
        matched_rois_set = set(matched_rois)
        
        # Vectorized lookup for sequence IDs
        match_sequence_ids = rois.loc[rois['id'].isin(matched_rois), ['id', 'sequence_id']].set_index('id')
        
        new_stack = []  # match stack after padding
        to_remove = set()
        
        for i, match in enumerate(matched_rois):
            match_sequence_id = match_sequence_ids.loc[match, 'sequence_id']
            match_sequence_rois = sequences[match_sequence_id]
            distance = self.neighbors[i][1]
            
            # Check for duplicates in remaining matches
            for roi in match_sequence_rois:
                if roi in matched_rois_set and matched_rois.index(roi) > i:
                    to_remove.add(roi)
                if roi not in to_remove:
                    new_stack.append((roi, distance))

        self.neighbors = new_stack
        self._invalidate_cache()

    def order_matches(self):
        """
        Optimized matching with set operations instead of loops
        """
        if not self._viewpoint_cache_valid:
            self._invalidate_cache()

        # determine viewpoint matches between query sequence and matched sequence
        # Filter out the float('inf') sentinel values that represent None
        query_viewpoints = set(vp for vp in self.query_viewpoint_map.values() if vp != float('inf'))
        match_viewpoints = set(self.match_viewpoint_map[x[0]] for x in self.neighbors 
                               if x[0] in self.match_viewpoint_map and self.match_viewpoint_map[x[0]] != float('inf'))
        viewpoint_matches = query_viewpoints & match_viewpoints

        # reorder query sequence by viewpoint
        self.og_ranked_query_rids = sorted(self.query_data['id'].values.astype(int).tolist(),
                                           key=lambda x: (
                                               self.query_viewpoint_map[x] not in viewpoint_matches,
                                               self.query_viewpoint_map[x]  # Now safe - no None values
                                            ))

        # reorder matches by viewpoint
        self.og_ranked_matches = sorted(self.neighbors,
                                        key=lambda x: (
                                            self.match_viewpoint_map.get(x[0], float('inf')) not in viewpoint_matches,
                                            self.match_viewpoint_map.get(x[0], float('inf')),  # Now safe - no None values
                                            x[1]  # distance tiebreaker
                                        ))

        self.ranked_matches = self.og_ranked_matches
        self.ranked_query_rids = self.og_ranked_query_rids

    def show_viewpoint(self, selected_viewpoint):
        """
        Toggle between viewpoints in match stack
        """
        if not self._viewpoint_cache_valid:
            self._invalidate_cache()

        if selected_viewpoint == 1:
            self.ranked_matches = self.og_ranked_matches
            self.ranked_query_rids = self.og_ranked_query_rids
            return True
        
        selected_viewpoint = 1 if selected_viewpoint == 2 else selected_viewpoint

        # Filter: only include if viewpoint matches and isn't the None sentinel
        available_queries = [rid for rid in self.og_ranked_query_rids
                             if self.query_viewpoint_map[rid] == selected_viewpoint]
        
        available_matches = [match for match in self.og_ranked_matches 
                             if self.match_viewpoint_map.get(match[0], float('inf')) == selected_viewpoint]

        if not available_matches or not available_queries:
            self.ranked_matches = self.og_ranked_matches
            self.ranked_query_rids = self.og_ranked_query_rids
            return False

        self.ranked_query_rids = available_queries
        self.ranked_matches = available_matches
        return True


class FavoriteMatchObject():
    """
    Optimized FavoriteMatchObject for handling favorited ROIs.
    Features caching, vectorized operations, and lazy evaluation.
    """
    def __init__(self, sequence_id, filtered_neighbors, query_data, match_data):
        self.sequence_id = sequence_id
        self.query_data = query_data
        self.match_data = match_data
        self.neighbors = filtered_neighbors  # [(roi_id, distance), ...]

        # Cache viewpoint maps
        self._build_viewpoint_maps()
        
        # Lazy evaluation - only compute when accessed
        self._ranked_cache_valid = False
        self.ranked_query_rids = []
        self.ranked_matches = []
        self.og_ranked_query_rids = []
        self.og_ranked_matches = []
        
        # Cache for viewpoint filtering
        self._viewpoint_matches_cache = None

    def _build_viewpoint_maps(self):
        """Build viewpoint maps with None-safe conversion"""
        self.query_viewpoint_map = self._build_safe_viewpoint_map(self.query_data['id'],
                                                                  self.query_data['viewpoint'])
        if isinstance(self.match_data, pd.DataFrame):
            self.match_viewpoint_map = self._build_safe_viewpoint_map(self.match_data.index,
                                                                      self.match_data['viewpoint'])
        else:
            self.match_viewpoint_map = {}

    def _build_safe_viewpoint_map(self, ids, viewpoints):
        """Build viewpoint map with None values converted to float('inf')"""
        return {roi_id: (vp if vp is not None else float('inf')) for roi_id, vp in zip(ids, viewpoints)}

    def update(self, new_data):
        """Update with new data and invalidate cache"""
        self.neighbors = new_data[new_data['favorite'] == 1].values.tolist()
        self._invalidate_cache()

    def _invalidate_cache(self):
        """Invalidate ranked cache when data changes"""
        self._ranked_cache_valid = False
        self._viewpoint_matches_cache = None
        self.ranked_query_rids = []
        self.ranked_matches = []

    def _get_viewpoint_matches(self):
        """
        Compute viewpoint matches once and cache.
        Avoids recomputing on every order_matches() call.
        """
        if self._viewpoint_matches_cache is not None:
            return self._viewpoint_matches_cache
        
        # Set intersection for matching viewpoints
        query_viewpoints = set(self.query_data['viewpoint'].dropna().values)
        match_viewpoints = set(self.match_viewpoint_map.values())
        self._viewpoint_matches_cache = query_viewpoints & match_viewpoints
        
        return self._viewpoint_matches_cache

    def get_ranked_query_rids(self):
        """Compute only when requested"""
        if not self._ranked_cache_valid:
            self.order_matches()
        return self.ranked_query_rids

    def get_ranked_matches(self):
        """Compute only when requested"""
        if not self._ranked_cache_valid:
            self.order_matches()
        return self.ranked_matches

    def order_matches(self):
        """
        Order neighbors by viewpoint with optimized sorting.
        Single pass with combined sort keys.
        """
        viewpoint_matches = self._get_viewpoint_matches()

        # reorder query sequence by viewpoint
        query_ids = self.query_data['id'].values.astype(int).tolist()
        self.og_ranked_query_rids = sorted(query_ids,
                                           key=lambda x: (self.query_viewpoint_map.get(x) not in viewpoint_matches,
                                                          self.query_viewpoint_map.get(x)))
        # reorder matches by viewpoint
        self.og_ranked_matches = sorted(self.neighbors,
                                        key=lambda x: (self.match_viewpoint_map.get(x[0], 
                                                                                    float('inf')) not in viewpoint_matches,
                                                                                    self.match_viewpoint_map.get(x[0], float('inf')),
                                                                                    x[1]))  # distance as tiebreaker
        self.ranked_matches = self.og_ranked_matches
        self.ranked_query_rids = self.og_ranked_query_rids
        self._ranked_cache_valid = True

    def show_viewpoint(self, selected_viewpoint):
        """
        Toggle between viewpoints in match stack
        """
        if not self._ranked_cache_valid:
            self.order_matches()

        # Reset to original if "Any" viewpoint selected
        if selected_viewpoint == 1:
            self.ranked_matches = self.og_ranked_matches
            self.ranked_query_rids = self.og_ranked_query_rids
            return True

        # Normalize viewpoint index
        selected_viewpoint = 1 if selected_viewpoint == 2 else selected_viewpoint

        # Use set for O(1) lookups instead of repeated checks
        available_queries = [
            rid for rid in self.og_ranked_query_rids 
            if self.query_viewpoint_map.get(rid) == selected_viewpoint
        ]
        available_matches = [
            match for match in self.og_ranked_matches 
            if self.match_viewpoint_map.get(match[0]) == selected_viewpoint
        ]

        # Check if viewpoint has data
        if not available_matches or not available_queries:
            self.ranked_matches = self.og_ranked_matches
            self.ranked_query_rids = self.og_ranked_query_rids
            return False

        # Filter to selected viewpoint
        self.ranked_query_rids = available_queries
        self.ranked_matches = available_matches
        return True

    def rank_neighbors_by_distance(self):
        """Sort neighbors by distance (lowest first), not necessary but added for completeness"""
        self.neighbors = sorted(self.neighbors, key=lambda x: x[1])
        self._invalidate_cache()

    def rank_neighbors_by_favorites(self, favorite_rois):
        """Sort to prioritize favorites, not necessary but added for completeness"""
        favorite_set = set(favorite_rois)
        self.neighbors = sorted(self.neighbors, key=lambda x: x[0] not in favorite_set)
        self._invalidate_cache()

    def rank_neighbors_by_ided(self, ided_rois):
        """Sort to prioritize identified ROIs, not necessary but added for completeness"""
        ided_set = set(ided_rois)
        self.neighbors = sorted(self.neighbors, key=lambda x: x[0] not in ided_set)
        self._invalidate_cache()