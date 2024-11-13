"""
Functions for Managing Species Table
"""
import pandas as pd


def fetch_species(mpDB):
    """
    Fetches species Table, Converts to DataFrame

    Args
        - mpDB
    Returns
        - dataframe of species table
    """

    species = mpDB.select("species")

    if species:
        return pd.DataFrame(species, columns=["id", "binomen", "common"])
    else:  # return empty
        return pd.DataFrame(columns=["id", "binomen", "common"])


def import_csv(mpDB, file_path):
    """
    Species CSV entry (id, binomen, common)

    Args
        - mpDB
        - file_path (str): path to csv of species
    """
    # TODO: Check not none
    species_list = pd.read_csv(file_path)

    assert "Binomen" in species_list.columns
    assert "Common" in species_list.columns

    for _, species in species_list.iterrows():

        species_id = mpDB.add_species(species['Binomen'], species['Common'])

    print(f"Added {len(species_list)} species to Database")
