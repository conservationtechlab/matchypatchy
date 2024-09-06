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
    manifest = mpDB.fetch_table("roi")
    print(manifest)


    if manifest:
        manifest = pd.DataFrame(manifest, columns=["id", "frame", "bbox_x", "bbox_y", "bbox_w", "bbox_h",
                                              "viewpoint", "media_id", "species_id", "reviewed", "iid", "emb_id"])
    return manifest


