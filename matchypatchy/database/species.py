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


def import_csv(mpDB, file_path):
    """
    Media entry (id, filepath, ext, datetime, comment, site_id)
    """
    # TODO: Check not none
    species_list = pd.read_csv(file_path)

    assert "Binomen" in species_list.columns
    assert "Common" in species_list.columns

    for _, species in species_list.iterrows():

        species_id = mpDB.add_species(species['Binomen'],species['Common'])

    print(f"Added {len(species_list)} species to Database")