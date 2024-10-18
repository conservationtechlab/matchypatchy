"""
Functions for manipulating the individual table
"""


def merge(mpDB, query, match):
    """
    Merge two individuals after match
    """
    # keep name that is older
    new_id = max(query['individual_id'].item(), match['individual_id'].item())
    old_id = min(query['individual_id'].item(), match['individual_id'].item())

    # find all rois with newer name
    to_merge = mpDB.select('roi', columns='id', row_cond=f'individual_id={new_id}')
    print(to_merge)

    for roi in to_merge:
        pass
        #mpDB.edit_row('roi', roi, {'individual_id': old_id})
    
    # delete newer individual in table 

