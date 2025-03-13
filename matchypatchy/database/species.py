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

def fetch_individual(mpDB):
    """
    Fetches species Table, Converts to DataFrame

    Args
        - mpDB
    Returns
        - dataframe of species table
    """
    individual = mpDB.select("individual")
    if individual:
        return pd.DataFrame(individual, columns=["id", "species_id", "name", "sex", "age"])
    else:  # return empty
        return pd.DataFrame(columns=["id", "species_id", "name", "sex", "age"])
