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
    regions = mpDB.select("region")
    if regions:
        return pd.DataFrame(regions, columns=["id", "name"])
    else:
        return pd.DataFrame(columns=["id", "name"])
    
def fetch_station_names_from_id(mpDB, station_id):
    # given a station id, return names and ids of survey and region
    station_name, suvery_id = mpDB.select("station", "name, survey_id", row_cond=f"id={station_id}")[0]
    survey_name, region_id = mpDB.select("survey", "name, region_id", row_cond=f"id={suvery_id}")[0]
    region_name = mpDB.select("region", "name", row_cond=f"id={region_id}")[0][0]
    return_dict = {'station_name': station_name, 
                   'suvery_id': suvery_id,
                   'survey_name': survey_name,
                   'region_id': region_id,
                   'region_name': region_name}
    return  return_dict