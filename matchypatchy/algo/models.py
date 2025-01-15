"""
Functions for managing ML models

"""
import yaml
import urllib.request
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy import config


def update_model_yml():
    """
    Downloads the most recent version of the models.yml file from SDZWA server and updates internal file
    """
    # download current version
    urllib.request.urlretrieve("http://www.example.com", "models.yml")


def load(key=None):
    # load the yaml file
    with open('models.yml', 'r') as cfg_file:
        cfg = yaml.safe_load(cfg_file)
        if key:
            return cfg[key]
        else:
            return cfg
        
def get_path(key):
    ML_DIR = Path(config.load("ML_DIR"))
    MODELS = load('MODELS')
    if key is None:
        return None
    path = ML_DIR / MODELS[key][0]
    if path.exists():
        return path
    else:
        return None

def get_class_path(key):
    ML_DIR = Path(config.load("ML_DIR"))
    CLASS_FILES = load('CLASS_FILES')
    if key is None:
        return None
    path = ML_DIR / CLASS_FILES[key][0]
    if path.exists():
        return path
    else:
        return None

def get_config_path(key):
    ML_DIR = config.load("ML_DIR")
    CONFIG_FILES = load('CONFIG_FILES')
    if key is None:
        return None
    path = ML_DIR / CONFIG_FILES[key][0]
    if path.exists():
        return path
    else:
        return None
        
def download(key):
    # read model directory
    ML_DIR = Path(config.load("ML_DIR"))
    
    with open('models.yml', 'r') as ml_cfg:
    
        path = ML_DIR / ml_cfg['MODELS'][key][0]

        if not path.exists():  # check to see if it already exists first
            urllib.request.urlretrieve(ml_cfg['MODELS'][key][1], path)

        if path.exists():  # validate that it downloaded
            # if key is a classifier, get class list and config
            if key in ml_cfg['CLASSIFIERS']: 
                class_path = ML_DIR / ml_cfg['CLASS_FILES'][key][0]
                config_path = ML_DIR / ml_cfg['CONFIG_FILES'][key][0]
                if not class_path.exists():
                    urllib.request.urlretrieve(ml_cfg['CLASS_FILES'][key][1], path)
                if not config_path.exists():
                    urllib.request.urlretrieve(ml_cfg['CONFIG_FILES'][key][1], path)
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


class DownloadMLThread(QThread):
    """
    Thread for downloading ML model
    """
    downloaded = pyqtSignal(str)

    def __init__(self, checked_models):
        super().__init__()
        self.checked_models = checked_models

    def run(self):
        for key in self.checked_models:
            download(key)