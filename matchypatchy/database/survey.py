"""
Functions for Managing Survey Table
"""
import pandas as pd


def fetch_surveys(mpDB):
    """
    Fetches survey Table, Converts to DataFrame

    Args
        - mpDB
    """
    surveys = mpDB.select("survey")
    if surveys:
        return pd.DataFrame(surveys, columns=["id", "name", "region", "year_start", "year_end"])
    else:
        return pd.DataFrame(columns=["id", "name", "region", "year_start", "year_end"])

def fetch_regions(mpDB):
    # TODO
    pass