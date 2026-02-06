"""
Functions for managing ML models

"""
import yaml
import logging
import urllib.request
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.config import resource_path


def update_model_yml():
    """
    Downloads the most recent version of the models.yml file from SDZWA server and updates internal file
    """
    # download current version
    model_yml_path = resource_path("assets/models.yml")
    try:
        urllib.request.urlretrieve("https://sandiegozoo.box.com/shared/static/8o59iqmvjfic9btuarijfk30oocr5xkf.yml", model_yml_path)
        return True
    except urllib.error.URLError:
        logging.error("Unable to connect to server.")
        return False


def load_model(key=None):
    """Loads ML model configuration from models.yml, returns full dict or specific key"""
    model_yml_path = resource_path("assets/models.yml")

    with open(model_yml_path, 'r') as cfg_file:
        cfg = yaml.safe_load(cfg_file)
        if key:
            return cfg[key]
        else:
            return cfg


def is_valid_reid_model(basename):
    """Checks if given basename is a valid reid model"""
    models = ('REID_MODELS')
    if basename in models:
        return True
    else:
        return False


def get_path(ML_DIR, key):
    """Gets path to ML model in ML_DIR"""
    MODELS = load_model('MODELS')
    if key is None:
        return None
    path = ML_DIR / MODELS[key][0]
    if path.exists():
        return path
    else:
        return None


def delete(ML_DIR, key):
    """Deletes ML model from ML_DIR"""
    path = get_path(ML_DIR, key)
    if path:
        path.unlink()


def download(ML_DIR, key):
    """Downloads ML model to ML_DIR"""
    model_yml_path = resource_path("assets/models.yml")
    with open(model_yml_path, 'r') as cfg_file:
        ml_cfg = yaml.safe_load(cfg_file)
        models = ml_cfg['MODELS']
        name = models[key][0]
        url = models[key][1]

        path = ML_DIR / Path(name)

        if not path.exists():  # check to see if it already exists first
            for url in url if isinstance(url, list) else [url]:
                try:
                    urllib.request.urlretrieve(url, path)
                    return True
                except urllib.error.URLError:
                    logging.error("Unable to connect to server.")
                    return False
        if path.exists():  # validate that it downloaded
            return True
        else:
            return False


class DownloadMLThread(QThread):
    """
    Thread for downloading ML model
    """
    downloaded = pyqtSignal(str)

    def __init__(self, ml_dir, checked_models):
        super().__init__()
        self.checked_models = checked_models
        self.ml_dir = ml_dir

    def run(self):
        for key in self.checked_models:
            download(self.ml_dir, key)
