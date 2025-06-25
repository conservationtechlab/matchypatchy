"""
Functions for Manipulating and Processing ROIs
"""
import pandas as pd

IMAGE_EXT = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']
VIDEO_EXT = ['.avi', '.mp4', '.wmv', '.mov']

COLUMNS = ["filepath", "timestamp", "station_id", "camera_id", "sequence_id", "external_id",
           "comment", "viewpoint", "species_id", "individual_id"]


def fetch_media(mpDB, ids=None):
    """
    Fetches stations associated with given survey, checks that they have unique names
    (8) columns; (2) keys

    Args
        - mpDB
        - survey_id (int): requested survey id
    Returns
        - an inverted dictionary in order to match manifest station names to table id
    """
    if ids:
        ids_str = ', '.join(map(str, ids))
        media = mpDB.select("media", row_cond=f"id IN ({ids_str})")
    else:
        media = mpDB.select("media")

    if media:
        media = pd.DataFrame(media, columns=["id", "filepath", "ext", "timestamp", 'station_id',
                                             "camera_id", 'sequence_id', "external_id", 'comment', 'favorite'])
        media = media.replace({float('nan'): None})
        return media
    else:
        return pd.DataFrame()

    def load_selected_media(self):
        """
        Fetch all columns from both `roi` and `media` tables for the selected ROI IDs.
        """
        ids_str = ', '.join(map(str, self.ids))

        # Use all_media to get a complete view of each ROI
        data, col_names = self.mpDB.all_media(row_cond=f"roi.id IN ({ids_str})")

        # Create DataFrame
        df = pd.DataFrame(data, columns=col_names)
        df = df.replace({float('nan'): None}).reset_index(drop=True)

        return df


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
                                               "species_id", "viewpoint", "reviewed", "individual_id", "emb"])
        rois = rois.replace({float('nan'): None})
        return rois
    else:
        return False


def fetch_roi_media(mpDB, rids=None, reset_index=True):
    """
    Fetch Info for Media Table
    columns = ['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
                'reviewed', 'media_id', 'species_id', 'individual_id', 'emb',
                'filepath', 'ext', 'timestamp', 'station_id', 'camera_id', 'sequence_id', 'external_id',
                'comment', 'favorite', 'binomen', 'common', 'name', 'sex', 'age']
    """
    if rids:
        ids_str = ', '.join(map(str, rids))
        media, column_names = mpDB.all_media(row_cond=f"roi.id IN ({ids_str})")
    else:
        media, column_names = mpDB.all_media()
    rois = pd.DataFrame(media, columns=column_names)
    rois['viewpoint'] = rois["viewpoint"].astype(int, errors='ignore')
    rois = rois.replace({float('nan'): None})

    if reset_index:
        rois = rois.set_index("id")
    return rois


def export_data(mpDB):
    """
    Fetch Info for Media Table
    columns = ['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
                'reviewed', 'media_id', 'species_id', 'individual_id', 'emb',
                'filepath', 'ext', 'timestamp', 'station_id', 'camera_id', 'sequence_id', 'external_id',
                'comment', 'favorite', 'binomen', 'common', 'name', 'sex', 'age',
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

    valid_stations = list(mpDB.select("station", columns="id", row_cond=f'survey_id={survey_id}', quiet=False)[0])
    survey_list = ",".join([str(s) for s in valid_stations])
    media = mpDB.select("media", columns="id", row_cond=f'station_id IN ({survey_list})', quiet=False)
    return len(media)
