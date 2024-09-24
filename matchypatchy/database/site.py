import pandas as pd

def fetch_sites(mpDB, survey_id=None):
    """
    Fetches sites associated with given survey, checks that they have unique names,

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
    

def user_editable_rows():
    return [1,2,3]