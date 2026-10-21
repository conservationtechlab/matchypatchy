"""
Functions for Manipulating and Processing ROIs
"""
import hashlib
import os
from pathlib import Path
from dataclasses import dataclass
import pandas as pd


IMAGE_EXT = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']
VIDEO_EXT = ['.mp4', '.avi', '.mov', '.mkv', '.wmv']

# Column names returned by fetch_roi_media (roi joined with media and individual)
COLUMNS = [
    'id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
    'reviewed', 'favorite', 'media_id', 'individual_id', 'emb',
    'filepath', 'sha256', 'ext', 'timestamp', 'station_id', 'camera_id',
    'sequence_id', 'external_id', 'comment', 'name', 'sex', ]


@dataclass
class EditObject:
    """Class to represent an edit made to a media/ROI"""
    rid: int
    mid: int
    reference: str
    previous_value: any
    new_value: any


def get_sha256(path: str | Path,
               chunk_size: int = 1024 * 1024) -> str:
    """
    Calculate the SHA256 hash of a file in chunks and return the hexadecimal to avoid adding duplicate files
    """
    if not Path(path).exists():
        return None
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def fetch_media(mpDB, ids=None, counts=False, quiet=True):
    """
    Fetches all media info with full paths, converts to dataframe
    """
    # select ids, an empty list selects nothing (not everything)
    if ids is not None:
        ids_str = ', '.join(map(str, ids))
        row_cond = f"WHERE m.id IN ({ids_str})"
    else:
        row_cond = None

    # fetch counts for media table data_type=0
    if counts:
        query = f"""
            SELECT
                m.id, m.base_dir_id, m.relative_path, m.sha256, m.ext,
                m.timestamp, m.station_id, m.camera_id, m.sequence_id,
                m.external_id, m.comment,
                COUNT(roi.id) AS roi_count,
                u.base_dir || '{os.sep}' || m.relative_path AS filepath
            FROM media m
            LEFT JOIN uploads u ON m.base_dir_id = u.id
            LEFT JOIN roi ON roi.media_id = m.id
            {row_cond if row_cond else ''}
            GROUP BY m.id
        """

        columns = ["id", "base_dir_id", "relative_path", "sha256", "ext",
                   "timestamp", 'station_id', "camera_id", 'sequence_id',
                   "external_id", 'comment', 'roi_count', 'filepath']

        media = mpDB._command(query, quiet=quiet)

    # Query media with joined full paths no counts
    else:
        query = f"""
            SELECT
                m.id, m.base_dir_id, m.relative_path, m.sha256, m.ext,
                m.timestamp, m.station_id, m.camera_id, m.sequence_id,
                m.external_id, m.comment,
                u.base_dir || '{os.sep}' || m.relative_path AS filepath
            FROM media m
            LEFT JOIN uploads u ON m.base_dir_id = u.id
            {row_cond if row_cond else ''}
        """

        columns = ["id", "base_dir_id", "relative_path", "sha256", "ext",
                   "timestamp", 'station_id', "camera_id", 'sequence_id',
                   "external_id", 'comment', 'filepath']

        media = mpDB._command(query, quiet=quiet)

    # convert to dataframe and return
    if media:
        media = pd.DataFrame(media, columns=columns)
        media = media.replace({float('nan'): None})
        return media
    # return empty dataframe if no media found
    return pd.DataFrame()


def fetch_roi(mpDB, media_id=None):
    """
    Fetches roi table with media filepaths, converts to dataframe
    """
    query = f"""
        SELECT
            r.id, r.media_id, r.frame, r.bbox_x, r.bbox_y, r.bbox_w, r.bbox_h,
            r.viewpoint, r.reviewed, r.favorite, r.individual_id, r.emb,
            u.base_dir || '{os.sep}' || m.relative_path AS filepath
        FROM roi r
        JOIN media m ON r.media_id = m.id
        LEFT JOIN uploads u ON m.base_dir_id = u.id
    """

    if media_id:
        query += f" WHERE r.media_id = {media_id}"

    manifest = mpDB._command(query)

    if manifest:
        rois = pd.DataFrame(manifest, columns=["roi_id", "media_id", "frame", "bbox_x", "bbox_y", "bbox_w", "bbox_h",
                                               "viewpoint", "reviewed", "favorite", "individual_id", "emb", "filepath"])
        rois['viewpoint'] = pd.to_numeric(rois['viewpoint'], errors='coerce').astype('Int64')
        rois = rois.replace({float('nan'): None})
        return rois

    # return empty dataframe if no roi found
    return pd.DataFrame()


def fetch_roi_media(mpDB, rids=None, sequence_ids=None, reset_index=True):
    """
    Fetch Combined Roi and Media Info for Media Table
    columns = ['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
                'reviewed', 'favorite', 'media_id', 'individual_id', 'emb',
                'filepath', 'sha256', 'ext', 'timestamp', 'station_id', 'camera_id', 'sequence_id', 'external_id',
                'comment', 'name', 'sex']
    """
    # an empty list selects nothing (not everything)
    if rids is not None:
        ids_str = ', '.join(map(str, rids))
        media, column_names = mpDB.all_media(row_cond=f"roi.id IN ({ids_str})")
    elif sequence_ids is not None:
        sequence_ids_str = ', '.join(map(str, sequence_ids))
        media, column_names = mpDB.all_media(row_cond=f"media.sequence_id IN ({sequence_ids_str})")
    else:
        media, column_names = mpDB.all_media()
    rois = pd.DataFrame(media, columns=column_names)
    rois['viewpoint'] = pd.to_numeric(rois['viewpoint'], errors='coerce').astype('Int64')
    rois = rois.replace({float('nan'): None})

    if reset_index:
        rois = rois.set_index("id")
    return rois


def fetch_individual(mpDB):
    """Fetches Individual Table, Converts to DataFrame"""
    individual = mpDB.select("individual")
    if individual:
        return pd.DataFrame(individual, columns=["id", "name", "sex"]).set_index("id")
    # return empty dataframe if no individual found
    return pd.DataFrame(columns=["id", "name", "sex"]).set_index("id")


def get_roi_bbox(roi):
    """Return the bbox coordinates for a given roi row"""
    columns = ["bbox_x", "bbox_y", "bbox_w", "bbox_h"]

    if set(columns).issubset(roi.columns) and roi[columns].notnull().all(axis=None):
        return roi[columns]
    # return None if bbox coordinates are not available
    return None


def get_sequence(rid, roi_media):
    """
    Return two lists of roi.ids

    Group by capture, order by frame number
    """
    sequence_id = roi_media.loc[rid, "sequence_id"]
    sequence = roi_media[roi_media['sequence_id'] == sequence_id]
    sequence = sequence.sort_values(by=['timestamp'])
    return sequence.index.to_list()


def _group_roi_ids(roi_media, column):
    """
    Map each value of column to the list of roi.ids (index) with that value

    Keys keep first-appearance order. Null values map to an empty list.
    Uses one groupby instead of filtering the whole frame once per row.
    """
    groups = roi_media.groupby(column, sort=False).indices
    ids = roi_media.index
    roi_dict = {}
    for key in dict.fromkeys(roi_media[column].to_list()):
        positions = groups.get(key)
        roi_dict[key] = ids[positions].to_list() if positions is not None else []
    return roi_dict


def sequence_roi_dict(roi_media):
    """Return dict of sequence_id: [roi.ids]"""
    return _group_roi_ids(roi_media, "sequence_id")


def individual_roi_dict(roi_media):
    """Return dict of individual_id: [roi.ids]"""
    return _group_roi_ids(roi_media, "individual_id")


def media_count(mpDB, survey_id):
    """
    Get number of media files associated with a given survey_id
    """
    media = mpDB.query("""SELECT media.id FROM media
                         JOIN station ON station.id = media.station_id
                         WHERE station.survey_id=?;""", (survey_id,)) or []
    return media, len(media)


# EDITS AND DELETES ============================================================
def _in_ids(ids):
    """ids as ints, with the placeholders for an IN (...) of them"""
    ids = [int(i) for i in ids]
    return ids, ", ".join("?" * len(ids))


def delete_rois(mpDB, roi_ids):
    """Delete rois with their thumbnails and embeddings, False if it failed"""
    roi_ids, placeholders = _in_ids(roi_ids)
    if not roi_ids:
        return True
    return mpDB.delete("roi", f"id IN ({placeholders})", roi_ids)


def delete_media(mpDB, media_ids):
    """Delete media with their rois, thumbnails and embeddings, False if it failed"""
    media_ids, placeholders = _in_ids(media_ids)
    if not media_ids:
        return True
    return mpDB.delete("media", f"id IN ({placeholders})", media_ids)


def update_roi_box(mpDB, roi_id, frame, bbox_x, bbox_y, bbox_w, bbox_h):
    """
    Move a roi's box, keeping its id, individual, viewpoint and favorite

    Its embedding no longer matches the box, so it is dropped and emb set to 0,
    which the next Process run picks up. False if the box couldn't be saved.
    """
    saved = mpDB.edit_row("roi", roi_id, {"frame": frame,
                                          "bbox_x": round(bbox_x, 4), "bbox_y": round(bbox_y, 4),
                                          "bbox_w": round(bbox_w, 4), "bbox_h": round(bbox_h, 4),
                                          "emb": 0})
    if saved:
        mpDB.delete_emb(roi_id)
    return saved


def set_favorite(mpDB, roi_id, favorite):
    """Mark a roi as a favorite (1) or not (0), False if it couldn't be saved"""
    return mpDB.edit_row("roi", roi_id, {"favorite": int(favorite)})


def clear_project_data(mpDB):
    """
    Delete every media, roi, sequence and individual, their thumbnails and all embeddings

    Regions, surveys, stations and uploads are kept. False if any table couldn't be cleared.
    """
    cleared = all([mpDB.clear(table) for table in
                   ("media", "media_thumbnails", "roi", "roi_thumbnails", "sequence", "individual")])
    mpDB.clear_emb()
    return cleared
