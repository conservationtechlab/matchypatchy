"""
Functions for managing ML models

"""
import wget
from pathlib import Path
from matchypatchy import config

MODELS = {0:("MegaDetector v5a", "md_v5a.0.0.pt", ), 2:("Andes", "sdzwa_andes_v1.pt"),
          1:("MegaDetector v5b", "md_v5b.0.0.pt", ), 3:("Amazon", "sdzwa_amazon_v1.onnx"),
          7:("MiewID v3", "miewid_v3.bin"),          4:("Savanna", "sdzwa_savanna_v3.pt"), 
          8:("Viewpoint", "viewpoint_jaguar.pt"),    5:("SE Asian Rainforest", "sdzwa_seasia_v1.pt"), 
                                                     6:("Southwest USA", "sdzwa_southwest_v3.pt"),
         }

CLASS_FILES = {2:("Andes", "sdzwa_andes_v1.csv"),
               3:("Amazon", "sdzwa_amazon_v1.csv"),
               4:("Savanna", "sdzwa_savanna_v3.csv"),
               5:("SE Asian Rainforest", "sdzwa_seasia_v1.csv"),
               6:("Southwest USA", "sdzwa_southwest_v3.csv"),}

MEGADETECTOR_DEFAULT = [0]
MIEW_DEFAULT = [7]

DETECTORS = [0,1]
CLASSIFIERS = [2,3,4,5,6]

def import_models(keys=MODELS.keys()):
    available_models = dict()
    for m in keys:
        path = config.ML_DIR / MODELS[m][1]
        if path.exists():
            available_models[m] = path

    if len(available_models == 1):
        return list(available_models)
    return available_models

def get_path(key):
    path = config.ML_DIR / MODELS[key][1]
    if path.exists():
        return path
    else:
        return None
    
def get_class_path(key):
    path = config.ML_DIR / CLASS_FILES[key][1]
    if path.exists():
        return path
    else:
        return None
    
def download(key):
    url = MODELS[key][2]
    path = config.ML_DIR / MODELS[key][1]
    wget.download(url,out=path)
        