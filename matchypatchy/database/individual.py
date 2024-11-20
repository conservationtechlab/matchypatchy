"""
Functions for manipulating the individual table
"""


def merge(mpDB, data, query_sequence, match):
    """
    Merge two individuals after match
    """
    query_sequence = data.loc[query_sequence]
    match = data.loc[match]
    query_iid = query_sequence['individual_id'].iloc[0]
    match_iid =  match['individual_id']


    # query is unknown, give match name
    if query_iid is None:
        sequence = query_sequence['sequence_id'].iloc[0]
        keep_id = match_iid
        drop_id = None
    # match is older, update query
    elif query_iid > match_iid:
        sequence = query_sequence['sequence_id'].iloc[0]
        keep_id = match_iid
        drop_id = query_iid
    # query is older, update match
    else:
        sequence = match['sequence_id']
        keep_id = query_iid
        drop_id = match_iid
    # find all rois with newer name

    to_merge = data[data["sequence_id"] == sequence]
    for i in to_merge.index:
        mpDB.edit_row('roi', i, {'individual_id': int(keep_id)}, quiet=False)
    
    # delete newer individual in table 

