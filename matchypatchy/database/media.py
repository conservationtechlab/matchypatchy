"""
Functions for Importing and Manipulating Media
"""

import pandas as pd
from datetime import datetime, timedelta


IMAGE_EXT = ['.jpg','.jpeg','.png','.bmp','.tif', '.tiff']
VIDEO_EXT = ['.avi','.mp4','.wmv','.mov']

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
        media = pd.DataFrame(media, columns=["id", "filepath", "ext", "timestamp", 'site_id',
                                             'sequence_id', "capture_id", 'comment', 'favorite'])
    return media 



def user_editable_rows():
    return [1,2,3,4,5,6]
