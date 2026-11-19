"""Each Re-ID model's embeddings live in their own chroma collection."""
import pytest

from matchypatchy.database.mpdb import MatchyPatchyDB
from matchypatchy.database.setup import KEY_COLLECTION, emb_collection_name


def _ids(db, model):
    collection = db.chroma.get_collection(emb_collection_name(model))
    return sorted(int(i) for i in collection.get(include=[])["ids"])


def _recorded(db):
    """roi_embedding as {roi id: sorted models}"""
    recorded = {}
    for roi_id, model in db.db.execute("SELECT roi_id, model FROM roi_embedding;"):
        recorded.setdefault(roi_id, []).append(model)
    return {roi_id: sorted(models) for roi_id, models in recorded.items()}


def _emb_column(db):
    """emb of fetch_roi (1 for an embedding from the active model) as {roi id: emb}"""
    from matchypatchy.database.media import fetch_roi
    rois = fetch_roi(db)
    return dict(zip(rois["roi_id"], rois["emb"]))


@pytest.fixture
def rois(tmp_db):
    """Three rois, embedded by MiewID (3-d) and the first two by MegaDescriptor (4-d)"""
    db, _ = tmp_db
    station_id = db.add_station("Site01", None, None, 1)
    upload_id = db.add_upload("D:/2023")
    media_id = db.add_media(upload_id, "a.jpg", "hash", ".jpg", "2023-01-01", station_id)
    roi_ids = [db.add_roi(media_id, 0, 0.1, 0.1, 0.2, 0.2) for _ in range(3)]
    for n, roi_id in enumerate(roi_ids):
        db.add_emb(roi_id, [1.0, float(n), 0.0], model="MiewID_v3")
    for n, roi_id in enumerate(roi_ids[:2]):
        db.add_emb(roi_id, [0.0, 1.0, float(n), 1.0], model="MegaDescriptor_l_384")
    return db, roi_ids


def test_collection_names():
    assert emb_collection_name(None) == KEY_COLLECTION
    # MiewID embeddings were stored in the key collection before there was one per model
    assert emb_collection_name("MiewID_v3") == KEY_COLLECTION
    assert emb_collection_name("miewid_v3") == KEY_COLLECTION
    assert emb_collection_name("MegaDescriptor_l_384") == "emb_MegaDescriptor_l_384"
    assert emb_collection_name("Some Model (v2)") == "emb_Some_Model__v2"


def test_models_with_different_sizes_get_their_own_collections(rois):
    db, roi_ids = rois

    assert _ids(db, "MiewID_v3") == roi_ids
    assert _ids(db, "MegaDescriptor_l_384") == roi_ids[:2]
    assert db.chroma.get_collection(emb_collection_name("MegaDescriptor_l_384")).metadata["key"] == db.key


def test_knn_and_similarity_use_the_active_model(rois):
    db, roi_ids = rois

    db.set_emb_model("MegaDescriptor_l_384")
    neighbors = db.knn(roi_ids[0], k=3)["ids"][0]
    assert sorted(int(i) for i in neighbors) == roi_ids[:2]
    # no MegaDescriptor embedding for the third roi
    assert db.calculate_similarity(roi_ids[0], roi_ids[2]) is None

    db.set_emb_model("MiewID_v3")
    neighbors = db.knn(roi_ids[0], k=3)["ids"][0]
    assert sorted(int(i) for i in neighbors) == roi_ids
    assert db.calculate_similarity(roi_ids[0], roi_ids[2]) is not None


def test_add_emb_records_each_model(rois):
    db, roi_ids = rois
    mega = "MegaDescriptor_l_384"

    assert _recorded(db) == {roi_ids[0]: [mega, "MiewID_v3"], roi_ids[1]: [mega, "MiewID_v3"],
                             roi_ids[2]: ["MiewID_v3"]}


def test_emb_models_counts_rois_per_model(rois):
    db, _ = rois
    assert db.emb_models() == [("MegaDescriptor_l_384", 2), ("MiewID_v3", 3)]


def test_emb_column_follows_the_active_model(rois):
    db, roi_ids = rois

    db.set_emb_model("MegaDescriptor_l_384")
    assert _emb_column(db) == {roi_ids[0]: 1, roi_ids[1]: 1, roi_ids[2]: 0}

    db.set_emb_model("MiewID_v3")
    assert _emb_column(db) == {roi_id: 1 for roi_id in roi_ids}

    # a model nothing has been embedded with yet
    db.set_emb_model("New_Model")
    assert _emb_column(db) == {roi_id: 0 for roi_id in roi_ids}


def test_key_collection_aliases_name_one_model(rois):
    db, roi_ids = rois

    for model in (None, "miewid_v3", "MiewID_v3"):
        db.set_emb_model(model)
        assert db.emb_model == "MiewID_v3"
        assert _emb_column(db) == {roi_id: 1 for roi_id in roi_ids}


def test_redrawn_box_drops_every_models_record(rois):
    from matchypatchy.database.media import update_roi_box
    db, roi_ids = rois

    assert update_roi_box(db, roi_ids[0], 0, 0.3, 0.3, 0.2, 0.2) is True

    assert roi_ids[0] not in _recorded(db)
    assert roi_ids[1] in _recorded(db)


def test_add_emb_for_a_missing_roi_records_nothing(rois):
    db, _ = rois
    db.add_emb(999, [1.0, 0.0, 0.0], model="MiewID_v3")
    assert 999 not in _recorded(db)


def test_sync_rebuilds_records_from_the_collections(rois):
    db, roi_ids = rois
    mega = "MegaDescriptor_l_384"
    expected = _recorded(db)
    # lost, and stale rows, eg. a database migrated from roi.emb or a crash mid-write
    db.db.execute("DELETE FROM roi_embedding WHERE model = 'MiewID_v3';")
    db.db.execute("INSERT INTO roi_embedding (roi_id, model) VALUES (?, ?);", (roi_ids[2], mega))
    db.db.commit()

    db.sync_roi_embeddings()

    assert _recorded(db) == expected


def test_deletes_reach_every_model(rois):
    db, roi_ids = rois

    assert db.delete("roi", f"id={roi_ids[0]}")

    assert _ids(db, "MiewID_v3") == roi_ids[1:]
    assert _ids(db, "MegaDescriptor_l_384") == roi_ids[1:2]


def test_clear_emb_clears_every_model(rois):
    db, _ = rois

    db.clear_emb()

    assert _recorded(db) == {}
    names = [getattr(c, "name", c) for c in db.chroma.list_collections()]
    assert names == [KEY_COLLECTION]
    assert _ids(db, "MiewID_v3") == []
    assert db.chroma.get_collection(KEY_COLLECTION).metadata["key"] == db.key


def test_orphans_pruned_from_every_model_on_open(tmp_path, null_logger):
    db = MatchyPatchyDB(str(tmp_path))
    db.add_emb(999, [1.0, 0.0, 0.0], model="MiewID_v3")
    db.add_emb(999, [1.0, 0.0, 0.0, 0.0], model="MegaDescriptor_l_384")
    db.close()

    db = MatchyPatchyDB(str(tmp_path))

    assert db.key
    assert _ids(db, "MiewID_v3") == []
    assert _ids(db, "MegaDescriptor_l_384") == []
    db.close()
