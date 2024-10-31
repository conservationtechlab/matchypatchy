"""
Functions for Managing Site Table
"""
import pandas as pd


def fetch_sites(mpDB, survey_id=None):
    """
    Fetches sites associated with given survey, Converts to DataFrame

    Args
        - mpDB
        - survey_id (int): requested survey id 
    Returns
        - an inverted dictionary in order to match manifest site names to table id
    """
    if survey_id:
        sites = mpDB.select("site", row_cond=f'survey_id={survey_id}')
    else:
        sites = mpDB.select("site")

    if sites:
        return pd.DataFrame(sites, columns=["id", "name", "lat", "long", "survey_id"])
    else:  # return empty
        return pd.DataFrame(columns=["id", "name", "lat", "long", "survey_id"])


def import_csv(mpDB, file_path, survey_id):
    """
    Site entry (id, name, lat, long)
    """
    # TODO: TEST NOT NULL
    site_list = pd.read_csv(file_path)

    assert "Name" in site_list.columns
    assert "Latitude" in site_list.columns
    assert "Longitude" in site_list.columns

    for _, site in site_list.iterrows():
        site_id = mpDB.add_site(site['Name'], site['Latitude'], site['Longitude'], survey_id)

    print(f"Added {len(site_list)} sites to Database")