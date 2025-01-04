"""
Functions for managing ML models

"""
import wget
from matchypatchy import config

MODELS = {"MegaDetector v5a": ("md_v5a.0.0.pt", "https://sandiegozoo.box.com/shared/static/xj3496ii5hxtomf0s38axb1agn5u9up8.pt"),
          "MegaDetector v5b": ("md_v5b.0.0.pt", ),
          "Andes": ("sdzwa_andes_v1.pt", "https://sandiegozoo.box.com/shared/static/a25q2uojqj8undj1x9mz26w1xayotcbl.pt"),
          "Amazon Rainforest": ("sdzwa_amazon_v1.onnx", ""),
          "Savanna": ("sdzwa_savanna_v3.pt", "https://sandiegozoo.box.com/shared/static/m1h1q689bma52rosuk00k3o6zgt2nrc1.pt"),
          "SE Asian Rainforest": ("sdzwa_seasia_v1.pt",),
          "Southwest USA": ("sdzwa_southwest_v3.pt", 'https://sandiegozoo.box.com/shared/static/ucbk8kc2h3qu15g4xbg0nvbghvo1cl97.pt'),
          "MiewID v2": ("miewid_v2.bin", "https://sandiegozoo.box.com/shared/static/juqbgz2s6lh0wkmqf0b7slc5ay9nvclw.bin"),
          "MiewID v3": ("miewid_v3.bin", "https://sandiegozoo.box.com/shared/static/n1yaagklcyvh7a1x8fv6coek6eaqpnbh.bin"),
          "Jaguar Viewpoint": ("viewpoint_jaguar.pt",)}

CLASS_FILES = {"Andes": ("sdzwa_andes_v1_classes.csv", "https://sandiegozoo.box.com/shared/static/dopxswxuhaxa6m8ff8uezsa1mrmun7v6.csv"),
               "Amazon Rainforest": ("sdzwa_amazon_v1_classes.csv", ""),
               "Savanna": ("sdzwa_savanna_v3_classes.csv", "https://sandiegozoo.box.com/shared/static/r5fcvksluzgk1qfi1ayjik3ew5v9279s.csv"),
               "SE Asian Rainforest": ("sdzwa_seasia_v1_classes.csv"),
               "Southwest USA": ("sdzwa_southwest_v3_classes.csv", 'https://sandiegozoo.box.com/shared/static/tetfkotf295espoaw8jyco4tk1t0trtt.csv')}

CONFIG_FILES = {"Andes": ("sdzwa_andes_v1_config.yml", "https://sandiegozoo.box.com/shared/static/doup3sv4qa7q700c5v4wfeg82f5zia1r.yml"),
               "Amazon Rainforest": ("sdzwa_amazon_v1_config.yml", ""),
               "Savanna": ("sdzwa_savanna_v3_config.yml", "https://sandiegozoo.box.com/shared/static/i2gwllghyc0ezmy5pb83h0h1i19f7yhx.yml"),
               "SE Asian Rainforest": ("sdzwa_seasia_v1_config.yml"),
               "Southwest USA": ("sdzwa_southwest_v3_config.yml", 'https://sandiegozoo.box.com/shared/static/tetfkotf295espoaw8jyco4tk1t0trtt.csv')}

MEGADETECTOR_DEFAULT = [0]
MIEW_DEFAULT = [7]

DETECTORS = ["MegaDetector v5a", "MegaDetector v5b"]
CLASSIFIERS = ["Andes", "Amazon Rainforest", "Savanna", "SE Asian Rainforest", "Southwest USA"]
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


def get_config_path(key):
    if key is None:
        return None
    path = config.ML_DIR / CONFIG_FILES[key][0]
    if path.exists():
        return path
    else:
        return None


def download(key):
    path = config.ML_DIR / MODELS[key][0]
    if not path.exists():  # check to see if it already exists first
        wget.download(MODELS[key][1], out=str(path))
    if path.exists():  # validate that it downloaded
        # if key is a classifier, get class list and config
        if key in CLASSIFIERS: 
            class_path = config.ML_DIR / CLASS_FILES[key][0]
            config_path = config.ML_DIR / CONFIG_FILES[key][0]
            if not class_path.exists():
                wget.download(CLASS_FILES[key][1], out=str(class_path))
            if not config_path.exists():
                wget.download(CONFIG_FILES[key][1], out=str(config_path))
            if class_path.exists() and config_path.exists():
                # validate download
                return True
            else: 
                # download failed
                return False
        else:
            # model downloaded, not a classifier
            return True
    else:
        # download failed
        return False
    