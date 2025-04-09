"""
Functions for managing ML models

"""
import yaml
import logging
import urllib.request
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy import config


def update_model_yml():
    """
    Downloads the most recent version of the models.yml file from SDZWA server and updates internal file
    """
    # download current version
    try:
        urllib.request.urlretrieve("https://sandiegozoo.box.com/shared/static/2ajbcn5twyqvfd13521erp36qqrjxdel.yml", "models.yml")
        return True
    except urllib.error.URLError:
        logging.error("Unable to connect to server.")
        return False
    
def initiate_viewpoint_table(mpDB):
    VIEWPOINT = load('VIEWPOINT')
    


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
    ML_DIR = Path(config.load("ML_DIR"))
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

    with open('models.yml', 'r') as cfg_file:
        ml_cfg = yaml.safe_load(cfg_file)
        models = ml_cfg['MODELS']
        name = models[key][0]
        url = models[key][1]

        path = ML_DIR / Path(name)

        if not path.exists():  # check to see if it already exists first
            try:
                urllib.request.urlretrieve(url, path)
                return True
            except urllib.error.URLError:
                logging.error("Unable to connect to server.")
                return False
        if path.exists():  # validate that it downloaded
            # if key is a classifier, get class list and config
            if key in ml_cfg['CLASSIFIER_MODELS']:
                class_path = ML_DIR / ml_cfg['CLASS_FILES'][key][0]
                config_path = ML_DIR / ml_cfg['CONFIG_FILES'][key][0]
                if not class_path.exists():
                    try:
                        urllib.request.urlretrieve(ml_cfg['CLASS_FILES'][key][1], path)
                    except urllib.error.URLError:
                        logging.error("Unable to connect to server.")
                if not config_path.exists():
                    try:
                        urllib.request.urlretrieve(ml_cfg['CONFIG_FILES'][key][1], path)
                    except urllib.error.URLError:
                        logging.error("Unable to connect to server.")
                if class_path.exists() and config_path.exists():
                    # validate download
                    return True
                else:
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
