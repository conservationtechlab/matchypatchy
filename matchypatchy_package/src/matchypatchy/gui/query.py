"""
Class Definition for Query Object
"""
import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal

import matchypatchy.database.media as db_roi
from matchypatchy.database.location import fetch_station_names_from_id
from matchypatchy.threads.model_download_thread import load_model
from matchypatchy.threads.match_thread import MatchEmbeddingThread
from matchypatchy.threads.match_object import FavoriteMatchObject


class QueryContainer(QObject):
    """Container class for managing query and match data within the MatchyPatchy GUI."""
    thread_signal = pyqtSignal(bool)
    loaded_data = pyqtSignal(pd.DataFrame)

    def __init__(self, parent):
        super().__init__()
        self.mpDB = parent.mpDB
        self.parent = parent
        self.metric = parent.distance_metric
        self.k = parent.k
        self.threshold = parent.threshold
        self.filter_dict = {}
        self.VIEWPOINT_DICT = load_model('VIEWPOINTS')

        self.match_thread = None

        self.data_raw = pd.DataFrame()
        self.data = pd.DataFrame()

        # Inde data by ROI for quck lookup
        self._roi_index = {}  # {roi_id: row_data_dict}
        self._seq_index = {}  # {sequence_id: [roi_ids]}

        self.neighbor_dict = {}
        self.ranked_sequences = []
        self.sequences = {}

        self.current_match_object = None
        self.current_query_rois = []
        self.current_match_rois = []
        self.current_sequence = 0
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

        # FAVORITE Toggle
        self.favorite_match_object = None
        self.knn_match_object = None
        # Cache for favorite and similarity computations
        self._favorites_cache = None
        self._similarities_cache = {}

    # STEP 0: Load data and build indices for fast lookups
    def load_data(self):
        """
        Load ROI media and build fast lookup indices.
        """
        self.data_raw = db_roi.fetch_roi_media(self.mpDB)
        self.loaded_data.emit(self.data_raw)
        # no data
        if self.data_raw.empty:
            return False

        # Build lookup dicts
        self._build_indices()
        
        # Must have embeddings to continue
        return not (self.data_raw["emb"] == 0).all()

    def _build_indices(self):
        """Build ROI and sequence indices for fast lookups"""
        self._roi_index = self.data_raw.to_dict('index')
        self._seq_index = self.data_raw.reset_index().groupby('sequence_id')['id'].apply(list).to_dict()

    # STEP 2: Filter data
    def filter(self, filter_dict=None, valid_stations=None):
        """
        Filter media efficiently using vectorized operations.
        Avoid full DataFrame copy and multiple redundant filters.
        """
        if filter_dict is None or valid_stations is None:
            self.data = self.data_raw.copy()
        else:
            # Single filter pass instead of multiple identical checks
            station_ids = self._get_valid_stations(filter_dict, valid_stations)
            
            if station_ids is None:
                self.parent.show_progress("No data to compare within filter.")
                self.data = pd.DataFrame()
            else:
                # Single vectorized filter
                self.data = self.data_raw[self.data_raw['station_id'].isin(station_ids)]
        
        # Rebuild index with filtered data
        self._build_indices()
        self.sequences = db_roi.sequence_roi_dict(self.data)

    def _get_valid_stations_from_current(self):
        """
        Extract valid stations from current filter state.
        Used for partial updates to maintain filter consistency.
        """
        if not hasattr(self, '_current_valid_stations'):
            return None
        return self._current_valid_stations

    def _get_valid_stations(self, filter_dict, valid_stations):
        """
        Determine which stations to include based on filters.
        Returns set of station IDs or None if no valid data.
        """
        self._current_valid_stations = valid_stations
        valid_set = set(valid_stations.keys()) if valid_stations else set()
        
        if not valid_set:
            return None
        
        # Priority: single station > survey > region
        if filter_dict['active_station'][0] > 0:
            return {filter_dict['active_station'][0]}
        
        # Survey and region filters use the same pre-filtered valid_stations
        if filter_dict['active_survey'][0] > 0 or filter_dict['active_region'][0] > 0:
            return valid_set
        
        return valid_set

    # RUN ON ENTRY IF LOAD_DATA
    def calculate_neighbors(self):
        """Start MatchEmbeddingThread to calculate neighbors"""
        if self.match_thread and self.match_thread.isRunning():
            self.match_thread.requestInterruption()
            self.match_thread.wait()
        
        self.match_thread = MatchEmbeddingThread(self.mpDB, self.data, self.sequences,
                                                 k=self.k, metric=self.metric, threshold=self.threshold)
        self.match_thread.progress_update.connect(self.parent.progress.set_counter)
        self.match_thread.prompt_update.connect(self.parent.progress.update_prompt)
        self.match_thread.ranked_queries_return.connect(self.capture_ranked_sequences)
        self.match_thread.finished.connect(self.finish_calculating)  # do not continue until finished
        self.match_thread.start()

    def capture_ranked_sequences(self, ranked_sequences):
        """Capture ranked_sequences from MatchEmbeddingThread"""
        self.ranked_sequences = ranked_sequences
        # set number of queries to validate
        self.n_queries = len(self.ranked_sequences)

    def finish_calculating(self):
        """Finish calculating neighbors, signal to DisplayCompare to update with gui"""
        self.thread_signal.emit(bool(self.ranked_sequences))

    def set_threshold(self, threshold):
        """Set the similarity threshold for the query container"""
        self.threshold = threshold

    # QUERY NAVIGATION ---------------------------------------------------------
    def set_query(self, n):
        """Set the Query side to a particular (n) image in the list"""
        # Wrap around
        n = n % self.n_queries if self.n_queries > 0 else 0

        # set current query
        self.current_query = n
        # get corresponding sequence_id and rois
        self.current_match_object = self.ranked_sequences[self.current_query]
        self.current_query_rois = self.current_match_object.get_ranked_query_rids()
        # set view to first in sequence
        self.set_within_query_sequence(0)
        # update matches
        self.update_matches()

    def set_within_query_sequence(self, n):
        """Set the display to the nth element in the sequence"""
        if not self.current_query_rois:
            return
        
        n = n % len(self.current_query_rois)
        self.current_query_sn = n  # number within sequence
        self.current_query_rid = self.current_query_rois[self.current_query_sn]

    # refresh match list
    def update_matches(self):
        """
        Update match list if current_query changes
        """
        # get all matches for query
        full_match_set = self.current_match_object.get_ranked_matches()
        self.current_match_rois = [x[0] for x in full_match_set]

        # set to top of matches
        self.set_match(0)

    def set_match(self, n):
        """Set the current match index and id"""
        if not self.current_match_rois:
            return
        
        n = n % len(self.current_match_rois)
        self.current_match = n
        self.current_match_rid = self.current_match_rois[self.current_match]

    def get_query_sequence_id(self):
        """Get current query sequence ID"""
        if self.current_match_object:
            return self.current_match_object.sequence_id
        return None

    def get_match_sequence_id(self):
        """Get current match sequence ID"""
        if self.current_match_object and self.current_match_rois:
            # Get sequence ID of current match ROI
            return self._get_roi_field(self.current_match_rid, 'sequence_id')
        return None

    def update_sequences_in_place(self, query_seq_id, match_seq_id):
        """
        Update only the two affected sequences in local cache 
        instead of reloading everything from DB.
        Much faster than full load_data() + filter().
        """
        if query_seq_id is None or match_seq_id is None:
            # Fallback to full reload if sequence IDs not available
            self.load_data()
            self.filter(self.filter_dict, self._get_valid_stations_from_current())
            return

        # Reload only the two sequences that changed
        query_df = db_roi.fetch_roi_media(self.mpDB, sequence_id=query_seq_id)
        match_df = db_roi.fetch_roi_media(self.mpDB, sequence_id=match_seq_id)

        if query_df.empty or match_df.empty:
            # Fallback if fetch fails
            self.load_data()
            self.filter(self.filter_dict, self._get_valid_stations_from_current())
            return

        # Remove old sequence data and insert updated data
        # Using index-based filtering since 'id' is the index
        self.data = self.data[~self.data['sequence_id'].isin([query_seq_id, match_seq_id])]
        
        # Concatenate new data and preserve index
        self.data = pd.concat([self.data, query_df, match_df])
        
        # Rebuild indices with updated data
        self._build_indices()


    def update_partial_sequences(self, sequence_ids):
        """
        Update specific sequences by reloading from DB.
        Useful for targeted updates without full reload.
        """
        if not sequence_ids:
            return
        
        # Remove old data for these sequences
        self.data = self.data[~self.data['sequence_id'].isin(sequence_ids)]
        
        # Fetch fresh data for each sequence
        updated_dfs = []
        for seq_id in sequence_ids:
            seq_df = db_roi.fetch_roi_media(self.mpDB, sequence_id=seq_id)
            if not seq_df.empty:
                updated_dfs.append(seq_df)
        
        if updated_dfs:
            self.data = pd.concat([self.data] + updated_dfs)
            self._build_indices()

    # VIEWPOINT ----------------------------------------------------------------
    def toggle_viewpoint(self, selected_viewpoint):
        """Flip between viewpoints in paired images within a sequence"""
        self.selected_viewpoint = selected_viewpoint

        # filter query and matches by selected viewpoint
        viewpoint_available = self.current_match_object.show_viewpoint(self.selected_viewpoint)

        # update matches and query rois based on new viewpoint selection
        self.current_query_rois = self.current_match_object.get_ranked_query_rids()
        self.set_within_query_sequence(0)
        self.update_matches()

        return viewpoint_available

    # FAVORITES ----------------------------------------------------------------
    def set_match_favorites(self, active):
        """Set the match favorites active state"""
        if active:
            # store the current match object before switching to favorites
            self.knn_match_object = self.current_match_object
            
            # Use cached favorites if available, otherwise fetch once
            if self._favorites_cache is None:
                self._favorites_cache = self.data_raw[self.data_raw['favorite'] == 1].copy()
            
            if self._favorites_cache.empty:
                return

            query_roi_id = self.knn_match_object.query_data.iloc[0]['id']
            filtered_neighbors = self._calculate_favorites_similarities(query_roi_id)

            # Create favorite match object
            self.favorite_match_object = FavoriteMatchObject(
                self.knn_match_object.sequence_id,
                filtered_neighbors,
                query_data=self.knn_match_object.query_data,
                match_data=self._favorites_cache
            )
            self.current_match_object = self.favorite_match_object
        else:
            # restore the original match object when deactivating favorites
            self.current_match_object = self.knn_match_object
            self.knn_match_object = None
            self.favorite_match_object = None
            self._similarities_cache.clear()

        self.update_matches()

    # RETURN INFO --------------------------------------------------------------
    def _calculate_favorites_similarities(self, query_roi_id):
        """
        Vectorized similarity calculation for favorites.
        Batch query all similarities at once instead of loop.
        """
        favorite_ids = self._favorites_cache.index.tolist()
        # Check cache first
        uncached = [fid for fid in favorite_ids if fid not in self._similarities_cache]

        if uncached:
            # Batch calculate similarities for uncached favorites
            batch_similarities = self.mpDB.batch_calculate_similarity(query_roi_id, uncached)
            self._similarities_cache.update(batch_similarities)
        
        # Return cached similarities
        filtered_neighbors = [(fid, 1 - self._similarities_cache[fid]) for fid in favorite_ids]
        return filtered_neighbors

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
        """Return distance between current sequence and match"""
        matches = self.current_match_object.get_ranked_matches()
        return matches[self.current_match][1] if self.current_match < len(matches) else float('inf')

    def _get_roi_field(self, roi_id, field):
        """
        Get ROI field efficiently using index.
        Falls back to DataFrame if index out of sync.
        """
        if roi_id in self._roi_index:
            return self._roi_index[roi_id].get(field)
        # Fallback to DataFrame lookup
        if roi_id in self.data.index:
            return self.data.loc[roi_id, field]
        return None

    def _get_roi_full_record(self, roi_id):
        """Get full ROI record from index"""
        if roi_id in self._roi_index:
            return self._roi_index[roi_id]
        if roi_id in self.data.index:
            return self.data.loc[roi_id].to_dict()
        return None

    def _update_roi_index(self, updates_dict):
        """Update local index with batch changes"""
        for roi_id, changes in updates_dict.items():
            if roi_id in self._roi_index:
                self._roi_index[roi_id].update(changes)

    def get_info(self, rid, column=None):
        """Get info from data table for given rid and column"""
        if column is None:
            # Return whole row from index or DataFrame
            if rid in self._roi_index:
                return pd.Series(self._roi_index[rid])
            return self.data.loc[rid]
        elif column == 'bbox':
            return db_roi.get_roi_bbox(self.data.loc[[rid]])
        elif column == 'metadata':
            return self.roi_metadata(self.data.loc[rid])
        else:
            return self._get_roi_field(rid, column)

    def roi_metadata(self, roi):
        """Display relevant metadata in comparison label box"""
        location = fetch_station_names_from_id(self.mpDB, roi['station_id'])

        roi_renamed = roi.rename(index={"name": "Name",
                                        "sex": "Sex",
                                        "age": "Age",
                                        "filepath": "Filepath",
            "comment": "Comment",
            "timestamp": "Timestamp",
            "station_id": "Station",
            "sequence_id": "Sequence ID",
            "viewpoint": "Viewpoint"
        })

        info_dict = roi_renamed[['Name', 'Sex', 'Age', 'Filepath', 'Timestamp', 'Station',
                                 'Sequence ID', 'Viewpoint', 'Comment']].to_dict()

        info_dict['id'] = roi.name
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
    # Batch database updates
    def new_iid(self, individual_id):
        """Update records for roi after confirming a match (batched)"""
        roi_updates = {roi: {"individual_id": individual_id, "reviewed": 1} 
                      for roi in self.current_query_rois}
        roi_updates[self.current_match_rid] = {"individual_id": individual_id, "reviewed": 1}
        
        # Batch update instead of N individual queries
        self.mpDB.batch_edit('roi', roi_updates, quiet=True)
        
        # Update local index
        self._update_roi_index(roi_updates)

    def merge(self):
        """Merge two individuals after match (optimized)"""
        query_data = self._get_roi_full_record(self.current_query_rid)
        match_data = self._get_roi_full_record(self.current_match_rid)

        if query_data is None or match_data is None:
            return

        query_iid = query_data.get('individual_id')
        match_iid = match_data.get('individual_id')

        # Determine which ID to keep
        if query_iid is not None:
            keep_id = query_iid if (match_iid is None or match_iid < query_iid) else match_iid
        else:
            keep_id = match_iid

        # Find all ROIs in affected sequence
        to_merge_seq = self.current_match_object.sequence_id
        merge_rois = self._seq_index.get(to_merge_seq, [])

        # Batch update all ROIs
        roi_updates = {roi: {"individual_id": int(keep_id), "reviewed": 1} 
                      for roi in merge_rois}
        self.mpDB.batch_edit('roi', roi_updates, quiet=False)
        
        # Update local index
        self._update_roi_index(roi_updates)

    def unmatch(self):
        """Unmatch the current query ROI from the matched ROI"""
        self.mpDB.edit('roi', self.current_query_rid,
            {'individual_id': None, "reviewed": 0},
            allow_none=True,
            quiet=False
        )
        
        # Update local index
        self._update_roi_index({self.current_query_rid: {'individual_id': None, "reviewed": 0}})