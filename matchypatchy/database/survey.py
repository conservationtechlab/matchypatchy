import pandas as pd


def fetch_surveys(mpDB):
    """
    Fetches sites associated with given survey, checks that they have unique names,

    Args
        - mpDB
        - survey_id (int): requested survey id 
    Returns
        - an inverted dictionary in order to match manifest site names to table id
    """
    surveys = mpDB.select("survey")
    if surveys:
        return pd.DataFrame(surveys, columns=["id", "name", "year_start", "year_end", "region"])
    else:
        return pd.DataFrame(columns=["id", "name", "year_start", "year_end", "region"])
    

def user_editable_rows():
    return [1,2,3,4]