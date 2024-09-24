import pandas as pd

def fetch_species(mpDB):
    """
    Fetches sites associated with given survey, checks that they have unique names,

    Args
        - mpDB
        - survey_id (int): requested survey id 
    Returns
        - an inverted dictionary in order to match manifest site names to table id
    """

    species = mpDB.select("species")

    if species:
        return pd.DataFrame(species, columns=["id", "binomen", "common"])
    else:  # return empty
        return pd.DataFrame(columns=["id", "binomen", "common"])
    

def user_editable_rows():
    return [1,2]

