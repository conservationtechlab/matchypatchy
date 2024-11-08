"""
Functions for managing ML models

"""
import wget
from pathlib import Path
from matchypatchy import config

MODELS = {"MegaDetector v5a": ("md_v5a.0.0.pt", "https://sandiegozoo.box.com/shared/static/xj3496ii5hxtomf0s38axb1agn5u9up8.pt"), 
          "MegaDetector v5b": ("md_v5b.0.0.pt", ),
          "Andes": ("sdzwa_andes_v1.pt"),
          "Amazon Rainforest": ("sdzwa_amazon_v1.onnx",),
          "Savanna":  ("sdzwa_savanna_v3.pt",), 
          "SE Asian Rainforest": ("sdzwa_seasia_v1.pt",), 
          "Southwest USA": ("sdzwa_southwest_v3.pt", 'https://sandiegozoo.box.com/shared/static/ucbk8kc2h3qu15g4xbg0nvbghvo1cl97.pt'),
          "MiewID v2": ("miewid_v2.bin",), 
          "MiewID v3": ("miewid_v3.bin",),          
          "Jaguar Viewpoint": ("viewpoint_jaguar.pt",),                        
         }

CLASS_FILES = {"Andes": ("sdzwa_andes_v1_classes.csv"),
               "Amazon Rainforest": ("sdzwa_amazon_v1_classes.csv"),
               "Savanna": ("sdzwa_savanna_v3_classes.csv"),
               "SE Asian Rainforest": ("sdzwa_seasia_v1_classes.csv"),
               "Southwest USA": ("sdzwa_southwest_v3_classes.csv", 'https://sandiegozoo.box.com/shared/static/tetfkotf295espoaw8jyco4tk1t0trtt.csv'),}

MEGADETECTOR_DEFAULT = [0]
MIEW_DEFAULT = [7]

DETECTORS = ["MegaDetector v5a", "MegaDetector v5b"]
CLASSIFIERS = ["Andes","Amazon Rainforest", "Savanna", "SE Asian Rainforest", "Southwest USA"]
REIDS = ["MiewID v3", "MiewID v2"]
VIEWPOINTS = ["Jaguar Viewpoint"]

def available_models(keys=MODELS.keys()):
    models_dict = dict()
    for m in keys:
        path = config.ML_DIR / MODELS[m][0]
        if path.exists():
            models_dict[m] = path
    # if looking for a particular model, give back path
    return models_dict

def get_path(key):
    if key is None: 
        return None
    path = config.ML_DIR / MODELS[key][0]
    if path.exists():
        return path
    else:
        return None
    
def get_class_path(key):
    if key is None: 
        return None
    path = config.ML_DIR / CLASS_FILES[key][0]
    if path.exists():
        return path
    else:
        return None
    
def download(key):
    url = MODELS[key][1]
    path = config.ML_DIR / MODELS[key][0]
    wget.download(url,out=path)
        