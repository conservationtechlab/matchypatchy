"""
Functions for Manipulating and Processing ROIs
"""
import pandas as pd

from matchypatchy.config import VIEWPOINT


def fetch_roi(mpDB):
    """
    Fetches roi table, converts to dataframe

    Args
        - mpDB
    Returns
        - an inverted dictionary in order to match manifest site names to table id
    """
    manifest = mpDB.select("roi")
    if manifest:
        rois = pd.DataFrame(manifest, columns=["id", "media_id", "frame", "bbox_x", "bbox_y", "bbox_w", "bbox_h",
                                               "species_id", "viewpoint", "reviewed", "individual_id", "emb_id"])
        rois = rois.replace({float('nan'): None})
        return rois
    else:
        return False


def fetch_roi_media(mpDB):
    """
    Fetch Info for Media Table
    columns = ['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint',
                'reviewed', 'media_id', 'species_id', 'individual_id', 'emb_id',
                'filepath', 'ext', 'timestamp', 'site_id', 'sequence_id', 'external_id',
                'comment', 'favorite', 'binomen', 'common', 'name', 'sex']
    """
    media, column_names = mpDB.all_media()
    rois = pd.DataFrame(media, columns=column_names)
    rois = rois.replace({float('nan'): None})
    rois = rois.set_index("id")
    return rois


def roi_metadata(roi, spacing=1.5):
    """
    Display relevant metadata in comparison label box
    """
    roi = roi.rename(index={"name": "Name",
                            "filepath": "File Path",
                            "comment": "Comment",
                            "timestamp": "Timestamp",
                            "site_id": "Site",
                            "sequence_id": "Sequence ID",
                            "viewpoint": "Viewpoint"})

    info_dict = roi[['Name', 'File Path', 'Timestamp', 'Site',
                     'Sequence ID', 'Viewpoint', 'Comment']].to_dict()

    # convert viewpoint to human-readable (0=Left, 1=Right)
    info_dict['Viewpoint'] = VIEWPOINT[info_dict['Viewpoint']]

    info_label = "<br>".join(f"{key}: {value}" for key, value in info_dict.items())

    html_text = f"""<div style="line-height: {spacing};">
                        {info_label}
                    </div>
                """
    return html_text


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
