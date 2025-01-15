"""
Functions for Importing and Manipulating Media
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
