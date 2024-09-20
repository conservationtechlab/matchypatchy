"""
Functions for Manipulating and Processing ROIs
"""

import pandas as pd
from ..sqlite_vec import serialize_float32

def fetch_roi(mpDB):
    """
    Fetches sites associated with given survey, checks that they have unique names,

    Args
        - mpDB
        - survey_id (int): requested survey id 
    Returns
        - an inverted dictionary in order to match manifest site names to table id
    """
    manifest = mpDB.fetch_table("roi")
    if manifest:
        rois = pd.DataFrame(manifest, columns=["id", "frame", "bbox_x", "bbox_y", "bbox_w", "bbox_h",
                                              "viewpoint", "media_id", "species_id", "reviewed", "iid", "emb_id"])
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


def roi_knn(mpDB, roi_id, k=3):
    roi_emb_ids = mpDB.fetch_rows("roi", f"id={roi_id}", columns = "id, emb_id")  

    query = roi_emb_ids[0]

    results = db.execute(
        """
        SELECT
            roi_emb.id,
            distance,
            rio.id,
            iid,
        FROM roi_emb
        LEFT JOIN roi ON roi.emb_id = roi_emb.id
        WHERE embedding MATCH ?
            AND k = 3
        ORDER BY distance
        """,
        [serialize_float32(query)],
    ).fetchall()

    for row in results:
        print(row)