"""
Functions for managing ML models

"""
import wget
from pathlib import Path
from matchypatchy import config

MODELS = {0:("MegaDetector v5a", "md_v5a.0.0.pt", "https://sandiegozoo.box.com/shared/static/xj3496ii5hxtomf0s38axb1agn5u9up8.pt"), 
          1:("MegaDetector v5b", "md_v5b.0.0.pt", ),
          2:("Andes", "sdzwa_andes_v1.pt"),
          3:("Amazon", "sdzwa_amazon_v1.onnx"),
          4:("Savanna", "sdzwa_savanna_v3.pt"), 
          5:("SE Asian Rainforest", "sdzwa_seasia_v1.pt"), 
          6:("Southwest USA", "sdzwa_southwest_v3.pt", 'https://sandiegozoo.box.com/shared/static/ucbk8kc2h3qu15g4xbg0nvbghvo1cl97.pt'),
          7:("MiewID v2", "miewid_v2.bin"), 
          8:("MiewID v3", "miewid_v3.bin"),          
          9:("Viewpoint", "viewpoint_jaguar.pt"),    
                                                     
         }

CLASS_FILES = {2:("Andes", "sdzwa_andes_v1.csv"),
               3:("Amazon", "sdzwa_amazon_v1.csv"),
               4:("Savanna", "sdzwa_savanna_v3.csv"),
               5:("SE Asian Rainforest", "sdzwa_seasia_v1.csv"),
               6:("Southwest USA", "sdzwa_southwest_v3_classes.csv", 'https://sandiegozoo.box.com/shared/static/tetfkotf295espoaw8jyco4tk1t0trtt.csv'),}

MEGADETECTOR_DEFAULT = [0]
MIEW_DEFAULT = [7]

DETECTORS = [0,1]
CLASSIFIERS = [2,3,4,5,6]
REIDS = [7,8]
VIEWPOINTS = [9]

def available_models(keys=MODELS.keys()):
    models_dict = dict()
    for m in keys:
        path = config.ML_DIR / MODELS[m][1]
        if path.exists():
            models_dict[m] = path
    # if looking for a particular model, give back path
    return models_dict

def get_path(key):
    if key is None: 
        return None
    path = config.ML_DIR / MODELS[key][1]
    if path.exists():
        return path
    else:
        return None
    
def get_class_path(key):
    if key is None: 
        return None
    path = config.ML_DIR / CLASS_FILES[key][1]
    if path.exists():
        return path
    else:
        return None
    
def download(key):
    url = MODELS[key][2]
    path = config.ML_DIR / MODELS[key][1]
    wget.download(url,out=path)
        