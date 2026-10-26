"""
Query containers for the compare view

BaseQueryContainer holds what every mode shares; QueryContainer is the
default (KNN) mode. QC and manual mode live in query_qc.py and query_manual.py.
"""
import logging
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

import matchypatchy.database.media as db_roi
from matchypatchy.database.media import assign_individual, clear_individual
from matchypatchy.database.location import fetch_station_names_from_id
from matchypatchy.algorithm.match_object import MatchObject, FavoriteMatchObject
from matchypatchy.threads.match_thread import MatchEmbeddingThread
from matchypatchy.project import UsesProject
from matchypatchy.models import load_model, toggle_viewpoint_value


logger = logging.getLogger(__name__)


class BaseQueryContainer(UsesProject, QObject):
    """
    ROI lookups, metadata and match actions shared by every query container.

    Subclasses load self.data_raw, filter it into self.data (both indexed by roi id)
    and manage navigation (current_query_rid, current_match_rid, ...).
    """

    # LOOKUPS ------------------------------------------------------------------
    @staticmethod
    def _clean_iid(v):
        """None/NaN -> None, otherwise int"""
        return None if v is None or pd.isna(v) else int(v)

    def _frame_for(self, rid):
        """Frame holding rid, falling back to the unfiltered data (eg. favorites outside the filter)"""
        return self.data if rid in self.data.index else self.data_raw

    def _row(self, rid):
        """Row for rid"""
        return self._frame_for(rid).loc[rid]

    def _get_roi_field(self, roi_id, field):
        """Get ROI field, None if the roi is not loaded"""
        for df in (self.data, self.data_raw):
            if roi_id in df.index:
                return df.loc[roi_id, field]
        return None

    def _get_roi_full_record(self, roi_id):
        """Get full ROI record, None if the roi is not loaded"""
        for df in (self.data, self.data_raw):
            if roi_id in df.index:
                return df.loc[roi_id].to_dict()
        return None

    def _update_roi_index(self, updates_dict):
        """Apply changes to both the filtered and raw frames (existing ids only)"""
        for df in (self.data, self.data_raw):
            for roi_id, changes in updates_dict.items():
                if roi_id in df.index:
                    for key, value in changes.items():
                        df.loc[roi_id, key] = value

    def get_info(self, rid, column=None):
        """Get info from data table for given rid and column"""
        if column is None:
            return self._row(rid)
        elif column == 'bbox':
            return db_roi.get_roi_bbox(self._frame_for(rid).loc[[rid]])
        elif column == 'metadata':
            return self.roi_metadata(self._row(rid))
        else:
            return self._get_roi_field(rid, column)

    def roi_metadata(self, roi):
        """Display relevant metadata in comparison label box"""
        location = fetch_station_names_from_id(self.mpDB, roi['station_id'], roi['camera_id'])

        roi_renamed = roi.rename(index={"name": "Name",
                                        "sex": "Sex",
                                        "filepath": "Filepath",
                                        "comment": "Comment",
                                        "timestamp": "Timestamp",
                                        "station_id": "Station",
                                        "camera_id": "Camera",
                                        "sequence_id": "Sequence ID",
                                        "external_id": "External ID",
                                        "viewpoint": "Viewpoint"})

        info_dict = roi_renamed[['Name', 'Sex', 'Filepath', 'Timestamp', 'Station', 'Camera',
                                 'External ID', 'Sequence ID', 'Viewpoint', 'Comment']].to_dict()

        info_dict['Station'] = location['station_name']
        info_dict['Survey'] = location['survey_name']
        info_dict['Region'] = location['region_name']
        info_dict['Camera'] = location['camera_name']

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

    # NAVIGATION (QC and manual; the default container has its own) -------------
    def set_within_query_sequence(self, n):
        """Set the query side to the nth roi of the current query"""
        if not self.current_query_rois:
            return
        n = n % len(self.current_query_rois)
        self.current_query_sn = n  # number within sequence
        self.current_query_rid = self.current_query_rois[self.current_query_sn]
        # the match list can contain the query roi; don't show it on both sides
        if self.current_match_rois and self.current_match_rid == self.current_query_rid:
            self.set_match(self.current_match + 1)

    def set_match(self, n):
        """Set the current match index and id, skipping the query roi itself"""
        if not self.current_match_rois:
            return
        size = len(self.current_match_rois)
        step = -1 if n < self.current_match else 1
        n = n % size
        if self.current_match_rois[n] == self.current_query_rid and size > 1:
            n = (n + step) % size
        self.current_match = n
        self.current_match_rid = self.current_match_rois[self.current_match]

    # VIEWPOINT ----------------------------------------------------------------
    def toggle_viewpoint(self, selected_viewpoint):
        """
        Show only rois of the selected viewpoint (toggle 0 Left, 1 Any, 2 Right)

        Filters from the full query/match lists each time, so switching back to Any
        restores them. Returns False and shows all rois if the viewpoint has none.
        Subclasses set _all_query_rois and _all_match_rois when the query changes.
        """
        self.selected_viewpoint = selected_viewpoint
        query_rois, match_rois = list(self._all_query_rois), list(self._all_match_rois)
        available = True
        if selected_viewpoint != 1:
            value = toggle_viewpoint_value(selected_viewpoint)
            query_vp = [r for r in query_rois if value is not None and self._get_roi_field(r, 'viewpoint') == value]
            match_vp = [r for r in match_rois if value is not None and self._get_roi_field(r, 'viewpoint') == value]
            if query_vp and match_vp:
                query_rois, match_rois = query_vp, match_vp
            else:
                available = False
        self.current_query_rois = query_rois
        self.current_match_rois = match_rois
        self.set_within_query_sequence(0)
        # first match is shown on the query side
        self.set_match(1)
        return available

    # MATCH STATE --------------------------------------------------------------
    def is_existing_match(self):
        """Return whether current query and match have same individual_id"""
        query_iid = self._clean_iid(self._get_roi_field(self.current_query_rid, 'individual_id'))
        match_iid = self._clean_iid(self._get_roi_field(self.current_match_rid, 'individual_id'))
        return query_iid is not None and query_iid == match_iid

    def both_unnamed(self):
        """Return whether both current query and match are unnamed"""
        query_iid = self._clean_iid(self._get_roi_field(self.current_query_rid, 'individual_id'))
        match_iid = self._clean_iid(self._get_roi_field(self.current_match_rid, 'individual_id'))
        return query_iid is None and match_iid is None

    def get_query_sequence_id(self):
        """Get current query sequence ID"""
        return self._get_roi_field(self.current_query_rid, 'sequence_id')

    def get_match_sequence_id(self):
        """Get current match sequence ID"""
        return self._get_roi_field(self.current_match_rid, 'sequence_id')

    # MATCH FUNCTIONS ----------------------------------------------------------
    def _new_iid_rois(self):
        """ROIs to name when matching two unnamed rois"""
        return set(self.current_query_rois) | {self.current_match_rid}

    def new_iid(self, individual_id):
        """Update records for roi after confirming a match (batched)"""
        roi_updates = {int(roi): {"individual_id": individual_id, "reviewed": 1}
                       for roi in self._new_iid_rois()}

        # Update local index
        self._update_roi_index(roi_updates)

        # Then batch update the database
        assign_individual(self.mpDB, roi_updates, individual_id)

    def _merge_rois(self):
        """ROIs to assign to the kept individual when merging, besides the dropped individual's"""
        return {self.current_query_rid, self.current_match_rid}

    def merge(self):
        """Merge two individuals after a match, keeping the older (lower) id"""
        query_iid = self._clean_iid(self._get_roi_field(self.current_query_rid, 'individual_id'))
        match_iid = self._clean_iid(self._get_roi_field(self.current_match_rid, 'individual_id'))

        ids = [i for i in (query_iid, match_iid) if i is not None]
        if not ids:
            return
        keep_id = min(ids)

        # the shown rois plus every roi of the individual being merged away
        rois = set(self._merge_rois())
        for iid in set(ids) - {keep_id}:
            rois.update(self.data_raw.index[self.data_raw['individual_id'] == iid])

        if not rois:
            logger.warning("merge: no ROIs to update")
            return

        roi_updates = {int(r): {"individual_id": keep_id, "reviewed": 1}
                       for r in rois}
        assign_individual(self.mpDB, roi_updates, keep_id)

        # Update local index
        self._update_roi_index(roi_updates)

    def _unmatch_rois(self):
        """ROIs to clear when unmatching"""
        return {self.current_query_rid}

    def unmatch(self):
        """Unmatch the current query ROI from the matched ROI"""
        roi_updates = {int(r): {'individual_id': None, "reviewed": 0}
                       for r in self._unmatch_rois()}
        # Update local index
        self._update_roi_index(roi_updates)

        # update database
        clear_individual(self.mpDB, roi_updates)

    # REFRESH ------------------------------------------------------------------
    def refresh_data(self):
        """
        Reload the rows currently shown from the database, keeping the filter
        and navigation as they are (no re-filtering or re-ranking)
        """
        shown = self.data.index
        self.load_data()
        self.data = self.data_raw[self.data_raw.index.isin(shown)].copy()

    def update_sequences_in_place(self, query_seq_id, match_seq_id):
        """Refresh after a match"""
        self.refresh_data()

    def update_partial_sequences(self, sequence_ids):
        """Refresh after an unmatch"""
        self.refresh_data()


# Neighbors fetched per query = k * KNN_OVERFETCH, so filters can remove some
# candidates without dropping below k.
KNN_OVERFETCH = 3

# ROI columns the cached KNN results depend on besides the id: filter_valid drops
# neighbors of the same individual/sequence or another viewpoint, rank drops ID'd
# query sequences and puts ID'd/favorite rois first, emb marks rois with an embedding
KNN_CACHE_COLUMNS = ['individual_id', 'sequence_id', 'viewpoint', 'favorite', 'emb']


class QueryContainer(BaseQueryContainer):
    """Container class for managing query and match data within the MatchyPatchy GUI."""
    thread_signal = pyqtSignal(bool)
    progress_update = pyqtSignal(int)
    loaded_data = pyqtSignal(pd.DataFrame)

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.project = parent.project
        self.CACHE_PATH = Path(self.cfg.DB_DIR) / "knn_cache.json"
        self.metric = parent.distance_metric
        self.k = parent.k
        self.k_cache = self.k * KNN_OVERFETCH
        self.threshold = parent.threshold
        self.filter_dict = {}
        self.valid_stations = None
        self.VIEWPOINT_DICT = load_model('VIEWPOINTS')

        self.match_thread = None

        self.data_raw = pd.DataFrame()
        self.data = pd.DataFrame()

        # Index data by seq for quick lookup
        self._seq_index = {}  # {sequence_id: [roi_ids]}

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

        # KNN Cache
        self.cache_timeout = 3600  # Cache valid for 1 hour (seconds)
        self._raw_ranked = None    # serialized UNFILTERED results (from compute or cache)
        self._from_cache = False   # True if _raw_ranked came from disk
        self._stop_requested = False
        self.filter_matched = True

    # STEP 1: Load data
    def load_data(self):
        """
        Load ROI media. Filtering happens later, in finalize().
        """
        self._stop_requested = False
        self.data_raw = db_roi.fetch_roi_media(self.mpDB)
        # favorites may have changed
        self._favorites_cache = None
        self.loaded_data.emit(self.data_raw)
        if self.data_raw.empty:
            logger.warning("No ROI media found in the database.")
            return False
        # Must have embeddings to continue
        return not (self.data_raw["emb"] == 0).all()

    # STEP 2: Store filter state (applied later in finalize)
    def set_filter(self, filter_dict, valid_stations):
        """Remember the filter; it is applied after cache load / neighbor calculation."""
        self.filter_dict = filter_dict
        self.valid_stations = valid_stations

    # STEP 3: Compute neighbors on UNFILTERED data
    def calculate_neighbors(self):
        """Start MatchEmbeddingThread over the unfiltered data with extra headroom."""
        self._from_cache = False
        sequences_raw = db_roi.sequence_roi_dict(self.data_raw)
        self.match_thread = MatchEmbeddingThread(self.mpDB, self.data_raw, sequences_raw,
                                                 k=self.k_cache, metric=self.metric,
                                                 threshold=self.threshold)
        # Connect signals for progress updates and results capture
        self.match_thread.progress_update.connect(self.update_progress)
        self.match_thread.ranked_queries_return.connect(self.capture_ranked_sequences)
        self.match_thread.finished.connect(self.finish_calculating)  # do not continue until finished
        # start the match thread after a short delay to allow the GUI to update
        QTimer.singleShot(100, self.start_thread)

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

    def start_thread(self):
        """Start the match thread after a short delay"""
        if self._stop_requested:
            return
        if self.match_thread is not None:
            self.match_thread.start()

    def stop_calculation(self):
        """Request the match thread to stop calculation"""
        self._stop_requested = True
        logger.info("Stop requested for query container %s", id(self))
        if self.match_thread is not None:
            self.match_thread.requestInterruption()

    def capture_ranked_sequences(self, ranked_sequences):
        """Capture ranked_sequences from MatchEmbeddingThread"""
        self.ranked_sequences = ranked_sequences
        self.n_queries = len(ranked_sequences)

    # Finalize the results after calculation or cache load
    def finish_calculating(self):
        """Thread done: cache the raw results, then filter and narrow them."""
        if self._stop_requested:  # cancelled: no cache write, no signal
            return
        self._raw_ranked = self._serialize_ranked_sequences(self.ranked_sequences)
        if self._raw_ranked:
            self.save_knn_cache(self._raw_ranked)
        self.finalize()

    # STEP 4: Finalize results (called after calculation or cache load)
    def finalize(self):
        """
        Filter, then narrow raw KNN results to the filtered data.
        Runs after BOTH cache load and fresh compute.
        """
        if self._stop_requested:
            return

        if self._raw_ranked is None:
            self.ranked_sequences, self.n_queries = [], 0
            self.thread_signal.emit(False)
            return

        self.filter_matched = self.filter(self.filter_dict, self.valid_stations)
        if not self.filter_matched:
            self.ranked_sequences, self.n_queries = [], 0
            self.thread_signal.emit(False)
            return

        # strict only for cache: if headroom ran out, recompute instead of showing < k
        ranked = self._restrict_to_data(self._raw_ranked, strict=self._from_cache)
        if ranked is None:
            logger.info("Cache lacks headroom for this filter, recalculating")
            self.calculate_neighbors()
            return

        self.ranked_sequences = ranked
        self.n_queries = len(ranked)
        self.filter_matched = bool(ranked)
        self.thread_signal.emit(bool(ranked))

    def update_progress(self, value):
        """Update the progress in the parent progress popup"""
        if hasattr(self.parent, 'update_progress'):
            self.progress_update.emit(value)

    def set_threshold(self, threshold):
        """Set the similarity threshold for the query container"""
        self.threshold = threshold

    # STEP 5: Filter data (called from finalize)
    def filter(self, filter_dict=None, valid_stations=None):
        """
        Filter media efficiently using vectorized operations.
        Avoid full DataFrame copy and multiple redundant filters.
        """
        if filter_dict is None or valid_stations is None:
            # return full data
            self.data = self.data_raw.copy()
        else:
            station_ids = self._get_valid_stations(filter_dict, valid_stations)

            if station_ids is None:
                self.data = pd.DataFrame()
                logger.info("No valid stations found, resulting in empty data.")
                return False
            else:
                # Single vectorized filter; copy so later .loc writes don't hit a view
                self.data = self.data_raw[self.data_raw['station_id'].isin(station_ids)].copy()

        if self.data.empty:
            logger.info("Filter removed all data.")
            return False

        # Rebuild index with filtered data
        self._build_seq_indices()
        self.sequences = db_roi.sequence_roi_dict(self.data)
        logger.info(f"Filtered data contains {len(self.data)} entries.")
        return True

    def refresh_data(self):
        """Reload the shown rows, keeping the filter, then rebuild sequence lookups"""
        super().refresh_data()
        self._build_seq_indices()
        self.sequences = db_roi.sequence_roi_dict(self.data)

    def _build_seq_indices(self):
        """Build sequence indices for fast lookups"""
        self._seq_index = self.data_raw.reset_index().groupby('sequence_id')['id'].apply(list).to_dict()

    # QUERY NAVIGATION ---------------------------------------------------------
    def set_query(self, n):
        """Set the Query side to a particular (n) image in the list"""
        # Wrap around
        n = n % self.n_queries if self.n_queries > 0 else 0

        # set current query
        self.current_query = n
        # previous query's knn / favorites match objects no longer apply
        self.knn_match_object = None
        self.favorite_match_object = None
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
        """Get current query sequence ID from its match object"""
        if self.current_match_object:
            return self.current_match_object.query_sequence_id
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
        query_df = db_roi.fetch_roi_media(self.mpDB, sequence_ids=[query_seq_id])
        match_df = db_roi.fetch_roi_media(self.mpDB, sequence_ids=[match_seq_id])

        if query_df.empty or match_df.empty:
            # Fallback if fetch fails
            self.load_data()
            self.filter(self.filter_dict, self._get_valid_stations_from_current())
            return

        # Combine the newly fetched rows for the query and match sequences
        new_rows = pd.concat([query_df, match_df])
        new_rows = new_rows[~new_rows.index.duplicated()]
        seq_ids = [query_seq_id, match_seq_id]
        # Remove old sequence data and insert updated data
        # Using index-based filtering since 'id' is the index
        self.data = pd.concat([self.data[~self.data['sequence_id'].isin(seq_ids)], new_rows])
        self.data_raw = pd.concat([self.data_raw[~self.data_raw['sequence_id'].isin(seq_ids)], new_rows])

        # a merge also moved other rois of the dropped individual, refresh their name/sex
        iids = new_rows['individual_id'].dropna().unique()
        others = self.data_raw.index[self.data_raw['individual_id'].isin(iids)
                                     & ~self.data_raw['sequence_id'].isin(seq_ids)]
        if len(others):
            others_df = db_roi.fetch_roi_media(self.mpDB, rids=others.tolist())
            self._update_roi_index(others_df[['name', 'sex']].to_dict('index'))

        # Rebuild indices with updated data
        self._build_seq_indices()

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
        seq_df = db_roi.fetch_roi_media(self.mpDB, sequence_ids=sequence_ids)
        if not seq_df.empty:
            updated_dfs.append(seq_df)

        if updated_dfs:
            self.data = pd.concat([self.data] + updated_dfs)
            self._build_seq_indices()

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
            # store the knn match object before switching to favorites (once, so
            # re-applying favorites doesn't store the favorites object instead)
            if self.knn_match_object is None:
                self.knn_match_object = self.current_match_object
            
            # Use cached favorites if available, otherwise fetch once
            if self._favorites_cache is None:
                self._favorites_cache = self.data_raw[self.data_raw['favorite'] == 1].copy()
            
            if self._favorites_cache.empty:
                return

            # similarity to the query roi on screen
            filtered_neighbors = self._calculate_favorites_similarities(self.current_query_rid)

            # Create favorite match object
            self.favorite_match_object = FavoriteMatchObject(
                self.knn_match_object.query_sequence_id,
                filtered_neighbors,
                query_data=self.knn_match_object.query_data,
                match_data=self._favorites_cache
            )
            self.current_match_object = self.favorite_match_object
        else:
            # restore the original match object when deactivating favorites
            if self.knn_match_object is not None:
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
        # Check cache first, keyed by (query, favorite) since the query changes
        uncached = [fid for fid in favorite_ids if (query_roi_id, fid) not in self._similarities_cache]

        if uncached:
            # Batch calculate similarities for uncached favorites
            batch_similarities = self.mpDB.batch_calculate_similarity(query_roi_id, uncached)
            self._similarities_cache.update({(query_roi_id, fid): sim for fid, sim in batch_similarities.items()})

        # Return cached similarities, skipping favorites without an embedding (None)
        similarities = [(fid, self._similarities_cache[(query_roi_id, fid)]) for fid in favorite_ids]
        filtered_neighbors = [(fid, 1 - sim) for fid, sim in similarities if sim is not None]
        return filtered_neighbors

    def current_distance(self):
        """Return distance between current sequence and match"""
        matches = self.current_match_object.get_ranked_matches()
        return matches[self.current_match][1] if self.current_match < len(matches) else float('inf')

    # MATCH FUNCTIONS ----------------------------------------------------------
    def _merge_rois(self):
        """All ROIs of the query and match sequences"""
        query_seq = self.current_match_object.query_sequence_id
        match_seq = self._get_roi_field(self.current_match_rid, 'sequence_id')
        # the shown rois too, a match roi without a sequence is not in _seq_index
        return ({self.current_query_rid, self.current_match_rid}
                | set(self._seq_index.get(query_seq, [])) | set(self._seq_index.get(match_seq, [])))

    def _new_iid_rois(self):
        """Name both whole sequences, like merge"""
        return self._merge_rois()

    def _unmatch_rois(self):
        """The whole query sequence, so Unmatch undoes Match"""
        query_seq = self.current_match_object.query_sequence_id
        return {self.current_query_rid} | set(self._seq_index.get(query_seq, []))

    # ==========================================================================
    # KNN CACHE MANAGEMENT
    # ==========================================================================
    def clear_knn_cache(self):
        """Clear the KNN cache"""
        # delete the file
        self.CACHE_PATH.unlink(missing_ok=True)
        logger.info("KNN cache cleared")

    @staticmethod
    def _json_default(o):
        """JSON fallback for numpy types"""
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(f"{type(o)} not JSON serializable")

    def _serialize_ranked_sequences(self, ranked_sequences):
        """
        Convert MatchObject list to serializable dicts.
        Stores IDs and distances only; DataFrames are rebuilt from self.data.
        """
        seq_ids = self.data_raw['sequence_id'].to_dict() if 'sequence_id' in self.data_raw else {}
        return [{
            'sequence_id': m.query_sequence_id,
            'neighbors': [(rid, d) for rid, d in m.neighbors],  # [(roi_id, distance), ...]
            # counted in candidate sequences, like the cut in _restrict_to_data
            'truncated': len(self._nearest_candidates(m.neighbors, seq_ids)) >= self.k_cache,
            'og_ranked_query_rids': list(m.og_ranked_query_rids),
            'og_ranked_matches': [tuple(x) for x in m.og_ranked_matches],  # (rid, dist)
        } for m in ranked_sequences]

    def _cache_key(self):
        """
        Hash of the roi state the cached results depend on, so matching, favorites
        or a redrawn bbox (embedding dropped) invalidate the cache
        """
        state = self.data_raw[KNN_CACHE_COLUMNS].apply(pd.to_numeric, errors='coerce')
        state = state.astype('float64').sort_index()  # None and NaN hash the same
        hashed = pd.util.hash_pandas_object(state, index=True).values
        return hashlib.sha1(hashed.tobytes()).hexdigest()

    def save_knn_cache(self, serialized):
        """Save UNFILTERED results as JSON (atomic write)."""
        payload = {
            'timestamp': time.time(),
            'n_raw': len(self.data_raw),
            'state': self._cache_key(),
            'k_cache': self.k_cache,
            'metric': str(self.metric),
            'threshold': self.threshold,
            'ranked_sequences': serialized,
        }
        tmp = self.CACHE_PATH.with_suffix('.tmp')
        try:
            with open(tmp, 'w') as f:
                json.dump(payload, f, default=self._json_default)
            tmp.replace(self.CACHE_PATH)  # atomic, never a half-written file
            logger.info(f"KNN cache saved to {self.CACHE_PATH}")
        except Exception as e:
            logger.error(f"Failed to save JSON cache: {e}")
            tmp.unlink(missing_ok=True)

    def load_knn_cache(self):
        """Load RAW cached results only. Filtering happens in finalize()."""
        if not self.CACHE_PATH.exists():
            return False
        try:
            with open(self.CACHE_PATH, 'r') as f:
                cache = json.load(f)
            if (time.time() - cache['timestamp'] > self.cache_timeout
                    or cache.get('n_raw') != len(self.data_raw)
                    or cache.get('state') != self._cache_key()
                    or cache.get('metric') != str(self.metric)
                    or cache.get('threshold') != self.threshold
                    or cache.get('k_cache', 0) < self.k):
                return False
            self._raw_ranked = cache['ranked_sequences']
            self._from_cache = True
            return True
        except Exception as e:
            logger.error(f"Failed to load JSON cache: {e}")
            return False

    @staticmethod
    def _candidate_key(rid, seq_ids):
        """Candidate a matched roi belongs to: its sequence, or itself without one"""
        seq = seq_ids.get(rid)
        return ('roi', rid) if seq is None or pd.isna(seq) else seq

    @classmethod
    def _nearest_candidates(cls, neighbors, seq_ids):
        """
        Candidate sequences in neighbors, nearest first. pad_sequences gives every
        roi of a matched sequence the distance of its nearest roi.
        """
        distances = {}
        for rid, d in neighbors:
            key = cls._candidate_key(rid, seq_ids)
            distances[key] = min(d, distances.get(key, d))
        return sorted(distances, key=distances.get)

    def _restrict_to_data(self, serialized, strict):
        """
        Narrow raw KNN results to the currently filtered self.data.
        Returns list of MatchObjects, or None if strict and the cache ran out of headroom.
        """
        keep = set(self.data.index)  # roi ids are the index
        seq_ids = self.data['sequence_id'].to_dict()
        out = []
        for s in serialized:
            q_rids = [r for r in s['og_ranked_query_rids'] if r in keep]
            if not q_rids:
                continue  # whole sequence filtered out

            neighbors = [(rid, d) for rid, d in s['neighbors'] if rid in keep]
            candidates = self._nearest_candidates(neighbors, seq_ids)
            if strict and s['truncated'] and len(candidates) < self.k:
                return None  # cache was cut off, recompute
            # neighbors are in rank order (ID'd/favorites first), not distance order, and
            # padded to whole sequences: keep the k nearest candidate sequences, whole
            nearest = set(candidates[:self.k])
            neighbors = [(rid, d) for rid, d in neighbors
                         if self._candidate_key(rid, seq_ids) in nearest]
            if not neighbors:
                continue

            # og_ranked_matches is the same rois in viewpoint order; keep exactly the
            # rois chosen above so every ranked match is in match_data
            neighbor_ids = {rid for rid, _ in neighbors}
            ranked_matches = [tuple(m) for m in s['og_ranked_matches'] if m[0] in neighbor_ids]

            mo = MatchObject(query_sequence_id=s['sequence_id'],
                             filtered_neighbors=neighbors,
                             query_data=self.data.loc[q_rids].reset_index(),
                             match_data=self.data.loc[[rid for rid, _ in neighbors]].reset_index())
            mo.og_ranked_query_rids = q_rids
            mo.og_ranked_matches = ranked_matches
            mo.ranked_query_rids = list(q_rids)
            mo.ranked_matches = list(ranked_matches)
            out.append(mo)
        return out
