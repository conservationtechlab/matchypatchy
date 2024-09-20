from ..utils import swap_keyvalue

def fetch_sites(mpDB, survey_id):
    """
    Fetches sites associated with given survey, checks that they have unique names,

    Args
        - mpDB
        - survey_id (int): requested survey id 
    Returns
        - an inverted dictionary in order to match manifest site names to table id
    """
    cond = f'survey_id={survey_id}'
    sites = dict(mpDB.select("site", columns="id, name", row_cond=cond))
    if not len(sites.keys()) == len(set(sites.keys())):
        AssertionError('Survey has duplicate site names, please fix before importing.')
    sites = swap_keyvalue(sites)
    return sites