"""
Functions for Managing Region, Survey and Station Tables
"""
import pandas as pd


def fetch_surveys(mpDB):
    """Fetches survey Table, Converts to DataFrame"""
    surveys = mpDB.select("survey")
    if surveys:
        return pd.DataFrame(surveys, columns=["id", "name", "region", "year_start", "year_end"])

    return pd.DataFrame(columns=["id", "name", "region", "year_start", "year_end"])


def fetch_regions(mpDB):
    """Fetches region Table, Converts to DataFrame"""
    regions = mpDB.select("region")
    if regions:
        return pd.DataFrame(regions, columns=["id", "name", "timezone"])

    return pd.DataFrame(columns=["id", "name", "timezone"])


def fetch_stations(mpDB, survey_id=None):
    """
    Fetches stations associated with given survey, Converts to DataFrame
    """
    if survey_id:
        stations = mpDB.select("station", row_cond=f'survey_id={survey_id}')
    else:
        stations = mpDB.select("station")

    if stations:
        return pd.DataFrame(stations, columns=["id", "name", "lat", "long", "survey_id"])

    return pd.DataFrame(columns=["id", "name", "lat", "long", "survey_id"])


def fetch_station_names_from_id(mpDB, station_id):
    """Given a station id, return names and ids of survey and region"""
    station_name, suvery_id = mpDB.select("station", "name, survey_id", row_cond=f"id={station_id}")[0]
    survey_name, region_id = mpDB.select("survey", "name, region_id", row_cond=f"id={suvery_id}")[0]
    region_name = mpDB.select("region", "name", row_cond=f"id={region_id}")[0][0]
    return_dict = {'station_name': station_name,
                   'suvery_id': suvery_id,
                   'survey_name': survey_name,
                   'region_id': region_id,
                   'region_name': region_name}
    return return_dict


TZ_CONVERT_DICT = {
    # ============= WINDOWS TIMEZONE NAMES =============
    # Pacific
    'Pacific Standard Time': 'America/Los_Angeles',
    'Pacific Daylight Time': 'America/Los_Angeles',
    'Pacific Daylight Time (Mexico)': 'America/Los_Angeles',

    # Mountain
    'Mountain Standard Time': 'America/Denver',
    'Mountain Daylight Time': 'America/Denver',
    'Mountain Standard Time (Mexico)': 'America/Chihuahua',

    # Central
    'Central Standard Time': 'America/Chicago',
    'Central Daylight Time': 'America/Chicago',
    'Central America Standard Time': 'America/Guatemala',
    'Central Standard Time (Mexico)': 'America/Mexico_City',

    # Eastern
    'Eastern Standard Time': 'America/New_York',
    'Eastern Daylight Time': 'America/New_York',
    'Eastern Standard Time (Mexico)': 'America/Mexico_City',
    'Eastern Daylight Time (Mexico)': 'America/Mexico_City',

    # Other US/Americas
    'Alaska Standard Time': 'America/Anchorage',
    'Alaskan Daylight Time': 'America/Anchorage',
    'Hawaii-Aleutian Standard Time': 'Pacific/Honolulu',
    'Hawaii-Aleutian Daylight Time': 'Pacific/Honolulu',
    'Samoa Standard Time': 'Pacific/Apia',
    'Chamorro Standard Time': 'Pacific/Guam',
    'Canada Central Standard Time': 'America/Regina',
    'US Eastern Standard Time': 'America/Indianapolis',

    # Europe
    'GMT Standard Time': 'Europe/London',
    'Central Europe Standard Time': 'Europe/Berlin',
    'Romance Standard Time': 'Europe/Paris',
    'W. Central Africa Standard Time': 'Africa/Lagos',
    'South Africa Standard Time': 'Africa/Johannesburg',
    'FLE Standard Time': 'Europe/Kiev',
    'GTB Standard Time': 'Europe/Bucharest',
    'Middle East Standard Time': 'Asia/Baghdad',

    # Asia
    'China Standard Time': 'Asia/Shanghai',
    'Tokyo Standard Time': 'Asia/Tokyo',
    'Korea Standard Time': 'Asia/Seoul',
    'Singapore Standard Time': 'Asia/Singapore',
    'India Standard Time': 'Asia/Kolkata',
    'Bangkok Standard Time': 'Asia/Bangkok',
    'Magadan Standard Time': 'Asia/Magadan',
    'Vladivostok Standard Time': 'Asia/Vladivostok',

    # Australia
    'AUS Central Standard Time': 'Australia/Darwin',
    'AUS Eastern Standard Time': 'Australia/Sydney',
    'Tasmania Standard Time': 'Australia/Hobart',
    'W. Australia Standard Time': 'Australia/Perth',

    # ============= macOS/Linux TIMEZONE NAMES =============
    # (These are mostly IANA already, but included for completeness)
    'PST': 'America/Los_Angeles',
    'PDT': 'America/Los_Angeles',
    'MST': 'America/Denver',
    'MDT': 'America/Denver',
    'CST': 'America/Chicago',
    'CDT': 'America/Chicago',
    'EST': 'America/New_York',
    'EDT': 'America/New_York',
    'GMT': 'Europe/London',
    'BST': 'Europe/London',
    'CET': 'Europe/Paris',
    'CEST': 'Europe/Paris',
    'IST': 'Asia/Kolkata',
    'JST': 'Asia/Tokyo',
    'AEST': 'Australia/Sydney',
    'AEDT': 'Australia/Sydney',
    'UTC': 'UTC',
}
