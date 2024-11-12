"""
Functions for Manipulating and Processing ROIs
"""
import pandas as pd

from matchypatchy.config import VIEWPOINT

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
        rois = pd.DataFrame(manifest, columns=["id", "media_id", "frame", "bbox_x", "bbox_y", "bbox_w", "bbox_h",
                                               "species_id", "viewpoint", "reviewed", "individual_id", "emb_id"])
        return rois
    else:
        return False

    
def fetch_roi_media(mpDB):
    """
    Fetch Info for Media Table 
    """
    columns = ['id', 'frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'viewpoint', 
                'reviewed', 'media_id', 'species_id', 'individual_id', 'emb_id', 
                'filepath', 'ext', 'timestamp', 'site_id', 'sequence_id', 'capture_id',
                'comment', 'favorite', 'binomen', 'common', 'name', 'sex']
    media, column_names = mpDB.all_media()
    rois = pd.DataFrame(media, columns=column_names)
    rois = rois.set_index("id")
    return rois


def roi_knn(mpDB, emb_id, k=5):
    query = mpDB.select("roi_emb", columns="embedding", row_cond= f'rowid={emb_id}')[0][0]
    neighbors = mpDB.knn(query, k=k)
    return neighbors


def match(mpDB, sequences, k=3):
    """
    # 1. Get sequences of ROIS
    # 2. Get KNN for each ROI in sequence
    # 3. filter out matches from same sequence, capture
    # 4. rank ROIs by match scores 
    
    """
    info = "roi.id, media_id, reviewed, species_id, individual_id, emb_id, timestamp, site_id, sequence_id, capture_id"
    # need sequence and capture ids from media to restrict comparisons shown to 
    rois, columns = mpDB.select_join("roi", "media", 'roi.media_id = media.id', columns=info)
    rois = pd.DataFrame(rois,columns=columns)
    neighbor_dict = dict()
    distance_dict = dict()
    nearest_dict = dict()

    # TODO: WHAT TO DO IF NO NEIGHBORS?
    for s in sequences:
        for roi_id in sequences[s]:
            emb_id = rois.loc[rois['id'] == roi_id, "emb_id"].item()
            neighbors = roi_knn(mpDB, emb_id, k=k)
            filtered_neighbors = filter(rois, roi_id, neighbors)
            if filtered_neighbors:
                neighbor_dict.setdefault(s, []).extend(filtered_neighbors)
        # sort after matching full sequence
        if s in neighbor_dict.keys():
            # save closest neighbor
            ranked = sorted(neighbor_dict[s], key=lambda x: x[1])
            nearest_dict[s] = ranked[0][1]
            neighbor_dict[s] = remove_duplicate_matches(ranked)


    return neighbor_dict, nearest_dict
    

# TODO: MERGE SEQUENCES
def filter(rois, roi_id, neighbors, threshold = 100):
    """
    Returns list of valid neighbors by roi_emb.id
    """
    filtered = []
    query = rois[rois['id'] == roi_id].squeeze()
    for i in range(len(neighbors)):  # skip first one, self match
        match = rois[rois['emb_id'] == neighbors[i][0]].squeeze()

        # if not same individual or unlabeled individual:
        if (query['individual_id'] is None) or (match['individual_id'] != query['individual_id']):
            # if not in same sequence
            if (query['sequence_id'] is None) or (match['sequence_id'] != query['sequence_id']):
                # if not in same capture (should be redundent to sequence)
                if (query['capture_id'] is None) or (match['capture_id'] != query['capture_id']):
                    # distance check (do first or last?)
                    if neighbors[i][1] < threshold and neighbors[i][1] > 0:
                        # replace emb_id with roi_id
                        match_roi_id = int(match['id'])
                        filtered.append((match_roi_id, neighbors[i][1]))
    return filtered


def remove_duplicate_matches(matches):
    filtered = []
    seen = set()
    for item in matches:
        if item[0] not in seen:
            filtered.append(item)
            seen.add(item[0])
    return filtered


def roi_metadata(roi, spacing=1.5):
    """
    Display relevant metadata in comparison label box
    """
    roi = roi.rename(index={"name": "Name", 
                            "filepath": "File Path",
                            "comment":"Comment",
                            "timestamp": "Timestamp",
                            "site_id": "Site",
                            "sequence_id": "Sequence ID",
                            "viewpoint": "Viewpoint"})

    info_dict = roi[['Name','File Path','Timestamp','Site','Sequence ID', 'Viewpoint', 'Comment']].to_dict()

    # convert viewpoint to human-readable
    info_dict['Viewpoint'] = VIEWPOINT[info_dict['Viewpoint']]

    info_label = "<br>".join(f"{key}: {value}" for key, value in info_dict.items())

    html_text = f"""
        <div style="line-height: {spacing};">
            {info_label}
        </div>
        """

    return html_text


def get_bbox(roi): 
    """
    Return the bbox coordinates for a given roi row
    """
    return roi[['bbox_x','bbox_y','bbox_w','bbox_h']]


def get_sequence(id, roi_media):
    """
    Return two lists of roi.ids

    Group by capture, order by frame number
    """
    sequence
    sequence_id = roi_media.loc[id, "sequence_id"]
    sequence = roi_media[roi_media['sequence_id'] == sequence_id]
    sequence = sequence.sort_values(by=['capture_id'])
    return sequence.index.to_list()



def sequence_roi_dict(roi_media):
    """
    Return two lists of roi.ids

    Group by capture, order by frame number
    """
    sequence_dict = dict()
    sequence_ids = roi_media["sequence_id"].to_list()
    for s in sequence_ids:
        sequence = roi_media[roi_media['sequence_id'] == s]
        sequence_dict[s] = sequence.index.to_list()
    return sequence_dict
