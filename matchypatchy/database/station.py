"""
Functions for Managing station Table
"""
import pandas as pd


def fetch_stations(mpDB, survey_id=None):
    """
    Fetches stations associated with given survey, Converts to DataFrame

    Args
        - mpDB
        - survey_id (int): requested survey id
    Returns
        - an inverted dictionary in order to match manifest station names to table id
    """
    if survey_id:
        stations = mpDB.select("station", row_cond=f'survey_id={survey_id}')
    else:
        stations = mpDB.select("station")

    if stations:
        return pd.DataFrame(stations, columns=["id", "name", "lat", "long", "survey_id"])
    else:  # return empty
        return pd.DataFrame(columns=["id", "name", "lat", "long", "survey_id"])


def import_csv(mpDB, file_path, survey_id):
    """
    station entry (id, name, lat, long)
    """
    # TODO: TEST NOT NULL
    station_list = pd.read_csv(file_path)

    assert "Name" in station_list.columns
    assert "Latitude" in station_list.columns
    assert "Longitude" in station_list.columns

    for _, station in station_list.iterrows():
        station_id = mpDB.add_station(station['Name'], station['Latitude'], station['Longitude'], survey_id)

    print(f"Added {len(station_list)} stations to Database")
