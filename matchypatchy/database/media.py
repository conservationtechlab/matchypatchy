"""
Functions for Importing and Manipulating Media
"""

import pandas as pd
import os
from ..utils import is_unique


# TODO: Check for duplicates
def import_csv(mpDB, manifest_filepath, valid_sites):
    """
    Media entry (id, filepath, ext, datetime, comment, site_id)
    """
    # ADD DTYPE CHECKS
    manifest = pd.read_csv(manifest_filepath)

    assert "FilePath" in manifest.columns
    assert "Site" in manifest.columns
    assert "Species" in manifest.columns

    # assert bbox in manifest.columns

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

        # check all sequence_id are the same
        if "sequence_id" in manifest.columns:
            sequence_id = group["sequence_id"].iloc[0] if is_unique(group["sequence_id"]) else None
        else:
            sequence_id = None
            
        filename = os.path.basename(filepath)
        _, ext = os.path.splitext(filename)

        try:
            site_id = valid_sites[site]
        except KeyError:
            print('Site referenced but not added to Database')
            return False

        media_id = mpDB.add_media(filepath, ext, site_id, datetime=datetime, sequence_id=sequence_id)

        # TODO: add dtype checks
        for _, roi in group.iterrows():
            # Frame number for videos, else 1 if image 
            # WARNING! WILL HAVE TO DYNAMICALLY PULL FRAME WHEN RUNNING miewid
            frame = roi['frame_number'] if 'frame_number' in manifest.columns else 1

            bbox_x = roi['bbox1']
            bbox_y = roi['bbox2']
            bbox_w = roi['bbox3']
            bbox_h = roi['bbox4']
            
            # add viewpoint if exists
            viewpoint = roi['Viewpoint'] if 'Viewpoint' in manifest.columns else None

            species = roi['Species']
            # look up species id
            if isinstance(species, str):
                species_id = mpDB.fetch_rows("species", f'common="{species}"', columns='id')
                if species_id:
                    species_id = species_id[0][0]

            # already references table id
            elif isinstance(species, int):
                species_id = species 
            else:
                print(f"Could not add detection for unknown species {species}")
                continue

            roi_id = mpDB.add_roi(frame, bbox_x, bbox_y, bbox_w, bbox_h, media_id, species_id,
                         viewpoint=None, reviewed=0, iid=None, emb_id=None)


    print(f"Added {len(unique_images)} files and {len(manifest)} ROIs to Database")


def fetch_media(mpDB):
    """
    Fetches sites associated with given survey, checks that they have unique names,

    Args
        - mpDB
        - survey_id (int): requested survey id 
    Returns
        - an inverted dictionary in order to match manifest site names to table id
    """
    media = mpDB.fetch_table("media")
    
    if media:
        media = pd.DataFrame(media, columns=["id", "filepath", "ext", "datetime", 'sequence_id',
                                             'comment', 'favorite', 'site_id'])
    print(media)
    return media 
