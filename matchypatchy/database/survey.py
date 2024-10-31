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
        return pd.DataFrame(surveys, columns=["id", "name", "year_start", "year_end", "region"])
    else:
        return pd.DataFrame(columns=["id", "name", "year_start", "year_end", "region"])
