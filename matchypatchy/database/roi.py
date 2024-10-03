"""
Functions for Manipulating and Processing ROIs
"""

import pandas as pd


def fetch_roi(mpDB):
    """
    Fetches sites associated with given survey, checks that they have unique names,

    Args
        - mpDB
        - survey_id (int): requested survey id 
    Returns
        - an inverted dictionary in order to match manifest site names to table id
    """
    manifest = mpDB.select("roi")
    if manifest:
        rois = pd.DataFrame(manifest, columns=["id", "frame", "bbox_x", "bbox_y", "bbox_w", "bbox_h",
                                              "viewpoint", "reviewed", "media_id", "species_id",  "individual_id", "emb_id"])
        return rois
    else:
        return False


def update_roi_viewpoint(mpDB, roi_id, viewpoint):
    """Add embedding id once calculated
    Args:
        - mpDB: database object
        - roi_id (int): roi id to update
        - viewpoint (str): emb_id foreign key to add
    """
    return mpDB.edit_row("roi", roi_id, {"viewpoint":viewpoint})


def update_roi_embedding(mpDB, roi_id, emb_id):
    """Add embedding id once calculated
    Args:
        - mpDB: database object
        - roi_id (int): roi id to update
        - emb_id (int): emb_id foreign key to add
    """
    return mpDB.edit_row("roi", roi_id, {"emb_id":emb_id})


def update_roi_iid(mpDB, roi_id, iid):
    """Add individual id once confirmed
    
    Args:
        - mpDB: database object
        - roi_id (int): roi id to update
        - iid (int): iid foreign key to add
    """
    return mpDB.edit_row("roi", roi_id, {"iid":iid})


def roi_knn(mpDB, emb_id, k=3):
    query = mpDB.select("roi_emb", columns="embedding", row_cond= f'rowid={emb_id}')[0][0]
    neighbors = mpDB.knn(query)
    return neighbors


def match(mpDB): 
    info = "roi.id, media_id, reviewed, species_id, individual_id, emb_id, datetime, site_id, sequence_id, pair_id"
    # need sequence and pair ids from media to restrict comparisons shown to 
    rois, columns = mpDB.select_join("roi", "media", 'roi.media_id = media.id', columns=info)
    rois = pd.DataFrame(rois,columns=columns)
    print(rois)

    for _,roi in rois.iterrows():
        print(roi, roi["emb_id"])
        neighbors = roi_knn(mpDB, roi["emb_id"]) 
        print(neighbors)

