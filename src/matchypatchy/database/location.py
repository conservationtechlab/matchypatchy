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


def fetch_stations(mpDB, survey_id=None, reset_index=False):
    """
    Fetches stations associated with given survey, Converts to DataFrame
    """
    if survey_id:
        stations = mpDB.select("station", row_cond="survey_id=?", params=(survey_id,))
    else:
        stations = mpDB.select("station")

    if stations:
        df = pd.DataFrame(stations, columns=["id", "name", "lat", "long", "survey_id"])
        if reset_index:
            df = df.set_index("id")
        return df

    return pd.DataFrame(columns=["id", "name", "lat", "long", "survey_id"])


def fetch_cameras(mpDB, station_id=None, reset_index=False):
    """
    Fetches cameras associated with given station, Converts to DataFrame
    """
    if station_id:
        cameras = mpDB.select("camera", row_cond="station_id=?", params=(station_id,))
    else:
        cameras = mpDB.select("camera")

    if cameras:
        df = pd.DataFrame(cameras, columns=["id", "name", "station_id"])
        if reset_index:
            df = df.set_index("id")
        return df

    return pd.DataFrame(columns=["id", "name", "station_id"])


def fetch_station_names_from_id(mpDB, station_id, camera_id=None):
    """Given a station id, return names and ids of survey and region"""
    station_name, survey_id = mpDB.select("station", "name, survey_id", row_cond="id=?", params=(station_id,))[0]
    survey_name, region_id = mpDB.select("survey", "name, region_id", row_cond="id=?", params=(survey_id,))[0]
    # camera
    if camera_id is None:
        camera_name = None
    else:
        camera_name = mpDB.select("camera", "name", row_cond="id=?", params=(camera_id,))[0][0]
    # region
    if region_id is None:
        region_name = None
    else:
        region_name = mpDB.select("region", "name", row_cond="id=?", params=(region_id,))
        region_name = region_name[0][0] if region_name else None
    return_dict = {'station_name': station_name,
                   'survey_id': survey_id,
                   'survey_name': survey_name,
                   'region_id': region_id,
                   'region_name': region_name,
                   'camera_id': camera_id,
                   'camera_name': camera_name}
    return return_dict


# NAMES ========================================================================
def region_names(mpDB):
    """(id, name) of every region"""
    return mpDB.query("SELECT id, name FROM region;") or []


def survey_names(mpDB, region_id=None):
    """(id, name) of every survey, or of the surveys in region_id"""
    if region_id is None:
        return mpDB.query("SELECT id, name FROM survey;") or []
    return mpDB.query("SELECT id, name FROM survey WHERE region_id=?;", (region_id,)) or []


def station_names(mpDB, survey_ids=None):
    """(id, name) of every station, or of the stations in survey_ids, an empty list giving none"""
    if survey_ids is None:
        return mpDB.query("SELECT id, name FROM station;") or []
    survey_ids = [int(s) for s in survey_ids]
    if not survey_ids:
        return []
    placeholders = ", ".join("?" * len(survey_ids))
    return mpDB.query(f"SELECT id, name FROM station WHERE survey_id IN ({placeholders});", survey_ids) or []


def camera_names(mpDB):
    """(id, name) of every camera"""
    return mpDB.query("SELECT id, name FROM camera;") or []


# REGIONS ======================================================================
def get_region(mpDB, region_id):
    """(name, timezone) of a region, None if it doesn't exist"""
    rows = mpDB.query("SELECT name, timezone FROM region WHERE id=?;", (region_id,))
    return rows[0] if rows else None


def region_by_name(mpDB, name):
    """(id, timezone) of the region with this name, None if there is none"""
    rows = mpDB.query("SELECT id, timezone FROM region WHERE name=?;", (name,))
    return rows[0] if rows else None


def set_region_timezone(mpDB, region_id, timezone):
    """Change a region's timezone, False if it couldn't be saved"""
    return mpDB.edit_row("region", region_id, {"timezone": timezone})


# SURVEYS ======================================================================
def get_survey(mpDB, survey_id):
    """(name, region_id, year_start, year_end) of a survey, None if it doesn't exist"""
    rows = mpDB.query("SELECT name, region_id, year_start, year_end FROM survey WHERE id=?;", (survey_id,))
    return rows[0] if rows else None


def survey_timezone(mpDB, survey_id):
    """Timezone of the survey's region, None (local time) if it has no region or timezone"""
    rows = mpDB.query("""SELECT region.timezone FROM survey
                         JOIN region ON region.id = survey.region_id
                         WHERE survey.id=?;""", (survey_id,))
    return rows[0][0] if rows else None


def update_survey(mpDB, survey_id, name, region_id, year_start, year_end):
    """Save a survey's fields, False if it couldn't be saved (eg. the name is taken)"""
    return mpDB.edit_row("survey", survey_id, {"name": name, "region_id": region_id,
                                               "year_start": year_start, "year_end": year_end},
                         allow_none=True)


def delete_survey(mpDB, survey_id):
    """Delete a survey with its stations, media and their embeddings"""
    return mpDB.delete("survey", "id=?", (survey_id,))


# STATIONS =====================================================================
def get_station(mpDB, station_id):
    """(name, lat, long) of a station, None if it doesn't exist"""
    rows = mpDB.query("SELECT name, lat, long FROM station WHERE id=?;", (station_id,))
    return rows[0] if rows else None


def update_station(mpDB, station_id, name, lat, long):
    """Save a station's fields, False if it couldn't be saved"""
    return mpDB.edit_row("station", station_id, {"name": name, "lat": lat, "long": long}, allow_none=True)


def delete_station(mpDB, station_id):
    """Delete a station with its media and their embeddings"""
    return mpDB.delete("station", "id=?", (station_id,))


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
