"""
Shared base for the compare view's query containers (default, QC and manual)
"""
import pandas as pd
from PyQt6.QtCore import QObject

import matchypatchy.database.media as db_roi
from matchypatchy.database.location import fetch_station_names_from_id
from matchypatchy.threads.match_object import toggle_viewpoint_value


class BaseQueryContainer(QObject):
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
    def new_iid(self, individual_id):
        """Update records for roi after confirming a match (batched)"""
        roi_updates = {roi: {"individual_id": individual_id, "reviewed": 1}
                       for roi in self.current_query_rois}
        roi_updates[self.current_match_rid] = {"individual_id": individual_id, "reviewed": 1}

        # Update local index
        self._update_roi_index(roi_updates)

        # Then batch update the database
        self.mpDB.batch_edit('roi', roi_updates, quiet=True)

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
            self.logger.warning("merge: no ROIs to update")
            return

        roi_updates = {int(r): {"individual_id": keep_id, "reviewed": 1}
                       for r in rois}
        self.mpDB.batch_edit('roi', roi_updates, quiet=True)

        # Update local index
        self._update_roi_index(roi_updates)

    def unmatch(self):
        """Unmatch the current query ROI from the matched ROI"""
        # Update local index
        self._update_roi_index({self.current_query_rid: {'individual_id': None, "reviewed": 0}})

        # update database
        self.mpDB.edit_row('roi', self.current_query_rid,
                           {'individual_id': None, "reviewed": 0},
                           allow_none=True, quiet=True)

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
