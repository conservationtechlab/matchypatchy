import pandas as pd


def filter_viewpoint(manifest, value=None):
    if value is None:
        filter = manifest[manifest["viewpoint"].isna()]
    else:
        filter = manifest[manifest["viewpoint"] == value]
    return filter


def predict_viewpoint(manifest, viewpoint_model):
    # filter before or after?
    unlabeled = filter_viewpoint(manifest)
    print(unlabeled)
    

