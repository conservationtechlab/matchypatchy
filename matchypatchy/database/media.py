"""
Functions for Manipulating and Processing ROIs
"""
import pandas as pd

IMAGE_EXT = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']
VIDEO_EXT = ['.avi', '.mp4', '.wmv', '.mov']

COLUMNS = ["filepath", "timestamp", "station_id", "sequence_id", "external_id",
           "comment", "viewpoint", "species_id", "individual_id"]


def fetch_media(mpDB):
    """
    Fetches stations associated with given survey, checks that they have unique names
    (8) columns; (2) keys

    Args
        - mpDB
        - survey_id (int): requested survey id
    Returns
        - an inverted dictionary in order to match manifest station names to table id
    """
    media = mpDB.select("media")
    if media:
        media = pd.DataFrame(media, columns=["id", "filepath", "ext", "timestamp", 'station_id',
                                             'sequence_id', "external_id", 'comment', 'favorite'])
        media = media.replace({float('nan'): None})
        return media
    else:
        return pd.DataFrame()


def fetch_roi(mpDB):
    """
    Fetches roi table, converts to dataframe

    Args
        - mpDB
    Returns
        - an inverted dictionary in order to match manifest station names to table id
    """
    manifest = mpDB.select("roi")
    if manifest:
        rois = pd.DataFrame(manifest, columns=["roi_id", "media_id", "frame", "bbox_x", "bbox_y", "bbox_w", "bbox_h",
                                               "species_id", "viewpoint", "reviewed", "individual_id", "emb_id"])
        rois = rois.replace({float('nan'): None})
        return rois
    else:
        return False


def fetch_roi_media(mpDB, reset_index=True):
    """
    Fetch Info for Media Table
    columns = ['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
                'reviewed', 'media_id', 'species_id', 'individual_id', 'emb_id',
                'filepath', 'ext', 'timestamp', 'station_id', 'sequence_id', 'external_id',
                'comment', 'favorite', 'binomen', 'common', 'name', 'sex', 'age']
    """
    media, column_names = mpDB.all_media()
    rois = pd.DataFrame(media, columns=column_names)
    rois = rois.replace({float('nan'): None})
    if reset_index:
        rois = rois.set_index("id")
    return rois


def get_bbox(roi):
    """
    Return the bbox coordinates for a given roi row
    """
    return roi[['bbox_x', 'bbox_y', 'bbox_w', 'bbox_h']]


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

    valid_stations = list(mpDB.select("station", columns="id", row_cond= f'survey_id={survey_id}', quiet=False)[0])
    survey_list = ",".join([str(s) for s in valid_stations])
    media = mpDB.select("media", columns="id", row_cond= f'station_id IN ({survey_list})', quiet=False)
    return len(media)