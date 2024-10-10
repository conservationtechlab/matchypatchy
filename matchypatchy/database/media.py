"""
Functions for Importing and Manipulating Media
"""

import pandas as pd
from datetime import datetime, timedelta


def fetch_media(mpDB):
    """
    Fetches sites associated with given survey, checks that they have unique names
    (8) columns; (2) keys

    Args
        - mpDB
        - survey_id (int): requested survey id 
    Returns
        - an inverted dictionary in order to match manifest site names to table id
    """
    media = mpDB.select("media")
    
    if media:
        media = pd.DataFrame(media, columns=["id", "filepath", "ext", "datetime", 'site_id',
                                             'sequence_id', "pair_id", 'comment', 'favorite'])
    return media 


def user_editable_rows():
    return [1,2,3,4,5,6]


def get_sequence_id(media, max_seq=3, max_time=60):
    """
    Assumes media is pd DataFrame
    """
    # Sort by time?

    assert "DateTime" in media.columns

    grouped = []
    group = []
    media['sequence_id'] = None
    
    #media = media.sort_values(by=['Site','DateTime'])
    print(media)

    for i,image in media.iterrows():
        if not group:
            group.append(image)
        else:
            # Check if the current timestamp is within one minute of the first in the group
            if image['DateTime'] - group[0]['DateTime'] <= timedelta(seconds=max_time) and len(group) < max_seq:
                group.append(image)
            else:
                # Save the current group and start a new one
                grouped.append(group)
                group = [image]

    if group:
        grouped.append(group)  # Add the last group

    sequence_id = 1
    for g in grouped:
        for i in g:
            media.loc[i.name,"sequence_id"] = sequence_id
        sequence_id += 1

    return media
