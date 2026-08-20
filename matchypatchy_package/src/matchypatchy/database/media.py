"""
Functions for Manipulating and Processing ROIs
"""
import hashlib
import pandas as pd
from pathlib import Path
from dataclasses import dataclass

IMAGE_EXT = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']
VIDEO_EXT = ['.mp4', '.avi', '.mov', '.mkv', '.wmv']


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
     # select ids
    if ids:
        ids_str = ', '.join(map(str, ids))
        row_cond=f"id IN ({ids_str})"
    else:
        row_cond=None
        
        
   # TODO: merge counts and query
    # fetch counts for media table data_type=0
    if counts:
        if row_cond is not None:
            media = mpDB._command(("SELECT media.*, COUNT(roi.id) AS count FROM media "
                                   "LEFT JOIN roi ON roi.media_id = media.id "
                                   f"GROUP BY media.id WHERE {row_cond};"), quiet=quiet)
        else:
            media = mpDB._command(("SELECT media.*, COUNT(roi.id) AS count FROM media "
                                   "LEFT JOIN roi ON roi.media_id = media.id "
                                   f"GROUP BY media.id;"), quiet=quiet)
            
        if media:
            media = pd.DataFrame(media, columns=["id","base_dir_id", "relative_path", "sha256", "ext", 
                                                 "timestamp", 'station_id', "camera_id", 'sequence_id',
                                                "external_id", 'comment', 'roi_count'])
            media = media.replace({float('nan'): None})
            return media
        else:
            return pd.DataFrame()
   # Query media with joined full paths
   else:
       query = """
          SELECT 
              m.id, m.base_dir_id, m.relative_path, m.sha256, m.ext,
              m.timestamp, m.station_id, m.camera_id, m.sequence_id,
              m.external_id, m.comment,
              u.base_dir || '/' || m.relative_path AS filepath
          FROM media m
          LEFT JOIN uploads u ON m.base_dir_id = u.id
      """

      if row_cond is not None:
          query += f" WHERE {condition}"
    
      media = mpDB._command(query)

      if media:
          media = pd.DataFrame(media, columns=["id", "filepath", "sha256", "ext", "timestamp",
                                              'station_id', "camera_id", 'sequence_id',
                                              "external_id", 'comment'])
          media = media.replace({float('nan'): None})
          return media
      else:
          return pd.DataFrame()


def fetch_roi(mpDB, media_id=None):
    """
    Fetches roi table with media filepaths, converts to dataframe
    """
    query = """
        SELECT 
            r.id, r.media_id, r.frame, r.bbox_x, r.bbox_y, r.bbox_w, r.bbox_h,
            r.viewpoint, r.reviewed, r.favorite, r.individual_id, r.emb,
            u.base_dir || '/' || m.relative_path AS filepath
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
    else:
        return pd.DataFrame()


def fetch_roi_media(mpDB, rids=None, reset_index=True):
    """
    Fetch Combined Roi and Media Info for Media Table
    columns = ['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
                'reviewed', 'favorite', 'media_id', 'individual_id', 'emb',
                'filepath', 'sha256', 'ext', 'timestamp', 'station_id', 'camera_id', 'sequence_id', 'external_id',
                'comment', 'name', 'sex', 'age']
    """
    if rids:
        ids_str = ', '.join(map(str, rids))
        media, column_names = mpDB.all_media(row_cond=f"roi.id IN ({ids_str})")
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
        return pd.DataFrame(individual, columns=["id", "name", "sex", "age"]).set_index("id")
    else:  # return empty
        return pd.DataFrame(columns=["id", "name", "sex", "age"]).set_index("id")


def get_roi_bbox(roi):
    """Return the bbox coordinates for a given roi row"""
    if {'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h'}.issubset(roi.columns) and \
        roi[['bbox_x', 'bbox_y', 'bbox_w', 'bbox_h']].notnull().all(axis=None):
        return roi[['bbox_x', 'bbox_y', 'bbox_w', 'bbox_h']]
    return None


def get_sequence(id, roi_media):
    """
    Return two lists of roi.ids

    Group by capture, order by frame number
    """
    sequence_id = roi_media.loc[id, "sequence_id"]
    sequence = roi_media[roi_media['sequence_id'] == sequence_id]
    sequence = sequence.sort_values(by=['timestamp'])
    return sequence.index.to_list()


def sequence_roi_dict(roi_media):
    """
    Return two lists of roi.ids

    Group by capture, order by frame number
    """
    sequence_dict = dict()
    sequence_ids = roi_media["sequence_id"].to_list()
    for s in sequence_ids:
        sequence = roi_media[roi_media['sequence_id'] == s]
        sequence_dict[s] = sequence.index.to_list()
    return sequence_dict


def individual_roi_dict(roi_media):
    """
    Return two lists of roi.ids

    Group by capture, order by frame number
    """
    individual_dict = dict()
    individual_ids = roi_media["individual_id"].to_list()
    for iid in individual_ids:
        individual = roi_media[roi_media['individual_id'] == iid]
        individual_dict[iid] = individual.index.to_list()
    return individual_dict


def media_count(mpDB, survey_id):
    """
    Get number of media files associated with a given survey_id
    """
    valid_stations = list(mpDB.select("station", columns="id", row_cond=f'survey_id={survey_id}')[0])
    survey_list = ",".join([str(s) for s in valid_stations])
    media = mpDB.select("media", columns="id", row_cond=f'station_id IN ({survey_list})')
    return media, len(media)
