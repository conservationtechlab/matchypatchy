"""
Functions for Importing and Manipulating Media
"""

import pandas as pd
import os
from ..utils import swap_keyvalue

def is_unique(s):
    a = s.to_numpy() # s.values (pandas<0.24)
    return (a[0] == a).all()

# TODO: Check to see if file already in database
def import_csv(mpDB, manifest_filepath, valid_sites):
    """
    Media entry (id, filepath, ext, datetime, comment, site_id)
    """
    # ADD DTYPE CHECKS
    manifest = pd.read_csv(manifest_filepath)
    assert "FilePath" in manifest.columns
    assert "Site" in manifest.columns

    manifest.sort_values(by=["FilePath"])

    unique_images = manifest.groupby("FilePath")
    for filepath, group in unique_images:
        # check all sites are the same
        if is_unique(group["Site"]):
            site = group["Site"].iloc[0]
        else:
            AssertionError(f"File {filepath} has ROI references to multiple sites, should be one.") 
        # check all datetimes are the same
        if is_unique(group["FileModifyDate"]):
            datetime = group["FileModifyDate"].iloc[0]
        else:
            AssertionError(f"File {filepath} has ROI references to multiple datetimes, should be one.") 
        filename = os.path.basename(filepath)
        _, ext = os.path.splitext(filename)

        try:
            site_id = valid_sites[site]
        except KeyError:
            print('Site referenced but not added to Database')
            return False

        mpDB.add_media(filepath, ext, site_id, datetime=datetime)

        # TODO: add all ROIs within group
        # for roi in group: 

    print("Added files to Database")

    
def fetch_sites(mpDB, survey_id):
    """
    Fetches sites associated with given survey, checks that they have unique names,

    Args
        - mpDB
        - survey_id (int): requested survey id 
    Returns
        - an inverted dictionary in order to match manifest site names to table id
    """
    cond = f'survey_id={survey_id}'
    sites = dict(mpDB.fetch_rows("site", cond, columns="id, name"))
    if not len(sites.keys()) == len(set(sites.keys())):
        AssertionError('Survey has duplicate site names, please fix before importing.')
    sites = swap_keyvalue(sites)
    return sites