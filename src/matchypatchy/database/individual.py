"""
Functions for Managing the Individual Table
"""


def individual_names(mpDB):
    """(id, name) of every individual"""
    return mpDB.query("SELECT id, name FROM individual;") or []


def individual_roi_counts(mpDB):
    """(id, name, number of rois) of every individual, including those with no rois"""
    # group by the individual, not the roi side of the join: grouping on roi.individual_id
    # folds every individual without rois into one NULL group
    return mpDB.query("""SELECT individual.id, individual.name, COUNT(roi.id)
                         FROM individual LEFT JOIN roi ON roi.individual_id = individual.id
                         GROUP BY individual.id;""") or []


def unidentified_roi_count(mpDB):
    """Number of rois without an individual"""
    rows = mpDB.query("SELECT COUNT(*) FROM roi WHERE individual_id IS NULL;")
    return rows[0][0] if rows else 0


def get_individual(mpDB, individual_id):
    """(name, sex) of an individual, None if it doesn't exist"""
    rows = mpDB.query("SELECT name, sex FROM individual WHERE id=?;", (individual_id,))
    return rows[0] if rows else None


def individual_name_exists(mpDB, name):
    """True if an individual already has this name"""
    return bool(mpDB.query("SELECT 1 FROM individual WHERE name=? LIMIT 1;", (name,)))


def update_individual(mpDB, individual_id, name, sex):
    """Save an individual's name and sex, False if it couldn't be saved"""
    return mpDB.edit_row("individual", individual_id, {"name": name, "sex": sex}, allow_none=True)
