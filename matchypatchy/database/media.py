"""
Functions for Manipulating and Processing ROIs
"""
import pandas as pd

IMAGE_EXT = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']
VIDEO_EXT = ['.mp4', '.avi', '.mov', '.mkv', '.wmv']

COLUMNS = ["filepath", "timestamp", "station_id", "camera_id", "sequence_id", "external_id",
           "comment", "viewpoint", "individual_id"]


def fetch_media(mpDB, ids=None):
    """
    Fetches all media info, converts to dataframe
    """
    if ids:
        ids_str = ', '.join(map(str, ids))
        media = mpDB.select("media", row_cond=f"id IN ({ids_str})")
    else:
        media = mpDB.select("media")

    if media:
        media = pd.DataFrame(media, columns=["id", "filepath", "ext", "timestamp",
                                             'station_id', "camera_id", 'sequence_id',
                                             "external_id", 'comment'])
        media = media.replace({float('nan'): None})
        return media
    else:
        return pd.DataFrame()


def fetch_roi(mpDB):
    """
    Fetches roi table, converts to dataframe
    """
    manifest = mpDB.select("roi")
    if manifest:
        rois = pd.DataFrame(manifest, columns=["roi_id", "media_id", "frame", "bbox_x", "bbox_y", "bbox_w", "bbox_h",
                                               "viewpoint", "reviewed", "favorite", "individual_id", "emb"])
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
                'filepath', 'ext', 'timestamp', 'station_id', 'camera_id', 'sequence_id', 'external_id',
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


def export_data(mpDB):
    """
    Fetch Info for Media Table
    columns = ['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
               'reviewed', 'favorite', 'media_id', 'individual_id', 'emb',
               'filepath', 'ext', 'timestamp', 'station_id', 'camera_id', 'sequence_id', 'external_id',
               'comment', 'name', 'sex', 'age',
                'station.id', 'station.name', 'lat', 'long', 'station.survey_id', 'survey.name', 'region.name']
    """
    media, column_names = mpDB.all_media()
    rois = pd.DataFrame(media, columns=column_names)
    rois = rois.replace({float('nan'): None})
    stations, column_names = mpDB.stations()
    stations = pd.DataFrame(stations, columns=column_names)
    stations = stations.replace({float('nan'): None})
    if not rois.empty:
        export_data = pd.merge(rois, stations, left_on="station_id", right_on="station.id")
        return export_data
    else:
        return None


def get_roi_bbox(roi):
    """Return the bbox coordinates for a given roi row"""
    if {'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h'}.issubset(roi.columns) and \
        roi[['bbox_x', 'bbox_y', 'bbox_w', 'bbox_h']].notnull().all(axis=None):
        return roi[['bbox_x', 'bbox_y', 'bbox_w', 'bbox_h']]
    return None


def get_roi_frame(roi):
    """Return the frame for a given roi row"""
    if {'frame'}.issubset(roi.columns):
        return roi['frame'].values[0]
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
    valid_stations = list(mpDB.select("station", columns="id", row_cond=f'survey_id={survey_id}', quiet=False)[0])
    survey_list = ",".join([str(s) for s in valid_stations])
    media = mpDB.select("media", columns="id", row_cond=f'station_id IN ({survey_list})', quiet=False)
    return media, len(media)
