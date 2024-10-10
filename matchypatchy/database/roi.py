"""
Functions for Manipulating and Processing ROIs
"""

import pandas as pd


def fetch_roi(mpDB):
    """
    Fetches sites associated with given survey, checks that they have unique names,

    Args
        - mpDB
        - survey_id (int): requested survey id 
    Returns
        - an inverted dictionary in order to match manifest site names to table id
    """
    manifest = mpDB.select("roi")
    if manifest:
        rois = pd.DataFrame(manifest, columns=["id", "frame", "bbox_x", "bbox_y", "bbox_w", "bbox_h",
                                              "viewpoint", "reviewed", "media_id", "species_id",  "individual_id", "emb_id"])
        return rois
    else:
        return False


def fetch_roi_compare(mpDB):
    """
    Fetches sites associated with given survey, checks that they have unique names,

    Args
        - mpDB
        - survey_id (int): requested survey id 
    Returns
        - an inverted dictionary in order to match manifest site names to table id
    """
    manifest, _ = mpDB.select_join("roi", "media", "roi.media_id = media.id")
    if manifest:
        rois = pd.DataFrame(manifest, columns=["roi_id", "frame", "bbox_x", "bbox_y", "bbox_w", "bbox_h",
                                              "viewpoint", "reviewed", "media_id", "species_id", "individual_id", "emb_id",
                                              "media_id2", "filepath", "ext", "datetime", 'site_id', 'sequence_id', "pair_id", 'comment', 'favorite'])
        rois = rois.drop(columns=["media_id2"])
        rois.set_index("emb_id")
        return rois
    else:
        return False


def roi_knn(mpDB, emb_id, k=3):
    query = mpDB.select("roi_emb", columns="embedding", row_cond= f'rowid={emb_id}')[0][0]
    neighbors = mpDB.knn(query)
    return neighbors


def match(mpDB): 
    # 1. Get KNN for each ROI
    # 2. filter out matches from same sequence, pair
    # 3. rank ROIs by match scores 

    info = "roi.id, media_id, reviewed, species_id, individual_id, emb_id, datetime, site_id, sequence_id, pair_id"
    # need sequence and pair ids from media to restrict comparisons shown to 
    rois, columns = mpDB.select_join("roi", "media", 'roi.media_id = media.id', columns=info)
    rois = pd.DataFrame(rois,columns=columns)
    neighbor_dict = dict()
    nearest_dict = dict()

    for _,roi in rois.iterrows():
        neighbors = roi_knn(mpDB, roi["emb_id"]) 
        filtered_neighbors = filter(rois, roi['id'], neighbors)
        #print(roi['id'], filtered_neighbors)
        neighbor_dict[roi['id']] = filtered_neighbors
        nearest_dict[roi['id']] = filtered_neighbors[0][1]

    return neighbor_dict, nearest_dict


def filter(rois, roi_id, neighbors, threshold = 100):
    filtered = []
    query = rois[rois['id'] == roi_id]
    #print("query", query)

    for i in range(1,len(neighbors)):  # skip first one, self match
        match = rois[rois['emb_id'] == neighbors[i][0]]
        
        #print("match", match)
        # if not same individual or unlabeled individual:
        if (query['individual_id'].item() is None) or (match['individual_id'].item() != query['individual_id'].item()):
            # if not in same sequence
            if (query['sequence_id'].item() is None) or (match['sequence_id'].item() != query['sequence_id'].item()):
                # if not in same pair (should be redundent to sequence)
                if (query['pair_id'].item() is None) or (match['pair_id'].item() != query['pair_id'].item()):
                    # distance check (do first or last?)
                    if neighbors[i][1] < threshold:
                        filtered.append(neighbors[i])

    return sorted(filtered, key=lambda x: x[1])


def rank(nearest_dict):
    return sorted(nearest_dict.items(), key=lambda x: x[1])


def get_bbox(roi):
    return roi[['bbox_x','bbox_y','bbox_w','bbox_h']]