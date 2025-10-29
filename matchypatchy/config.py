"""
Functions for Handling Config Yaml

"""
import os
import sys
from pathlib import Path
import logging
import yaml

HOME_DIR = Path.cwd() / "MatchyPatchy-Share"


def resource_path(relative_path):
    """ Get path to resource whether running in dev or PyInstaller bundle """
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)


def initiate():
    # check if cfg exists, load
    default_cfg = {
        'HOME_DIR': str(HOME_DIR),
        'LOG_PATH': str(HOME_DIR / 'matchpatchy.log'),
        'DB_DIR': str(HOME_DIR / 'Database'),
        'ML_DIR': str(HOME_DIR / 'Models'),
        'THUMBNAIL_DIR': str(HOME_DIR / 'Thumbnails'),
        'VIDEO_FRAMES': 3,
        'REID_KEY': None,
        'VIEWPOINT_KEY': None,
        'DETECTOR_KEY': None,
        'KNN': 100,
        'SEQUENCE_DURATION': 60,
        'SEQUENCE_N': 3,
    }

    CONFIG_PATH = HOME_DIR / '.config.yml'
    if CONFIG_PATH.exists():
        cfg = load()

        # start from empty
        if cfg is None:
            with open(CONFIG_PATH, 'w') as cfg_file:
                yaml.dump(default_cfg, cfg_file)
            cfg = default_cfg
        # check remaining, save what's missing
        else:
            for key in default_cfg.keys():
                if key not in cfg:
                    cfg[key] = default_cfg[key]
            with open(CONFIG_PATH, 'w') as cfg_file:
                yaml.dump(cfg, cfg_file)

    else:
        Path(HOME_DIR).mkdir(exist_ok=True)
        with open(CONFIG_PATH, 'w') as cfg_file:
            yaml.dump(default_cfg, cfg_file)
        cfg = default_cfg

    # Make sure ML_DIR and DB_DIR exists
    Path(cfg['DB_DIR']).mkdir(exist_ok=True)
    Path(cfg['ML_DIR']).mkdir(exist_ok=True)
    Path(cfg['THUMBNAIL_DIR']).mkdir(exist_ok=True)

    # LOG CONFIG
    logging.basicConfig(filename=cfg['LOG_PATH'], encoding='utf-8', level=logging.DEBUG, force=True)
    logging.info('HOME_DIR: ' + str(HOME_DIR))

    return cfg


def load(key=None):
    CONFIG_PATH = HOME_DIR / '.config.yml'
    # Load the config into a dict
    with open(CONFIG_PATH, 'r') as cfg_file:
        cfg = yaml.safe_load(cfg_file)
        if key:
            return cfg[key]
        else:
            return cfg


def add(key_dict, quiet=False):
    CONFIG_PATH = HOME_DIR / '.config.yml'
    # Load the config into a dict
    with open(CONFIG_PATH, 'r') as cfg_file:
        cfg = yaml.safe_load(cfg_file)
        for key in key_dict.keys():
            if key in cfg and not quiet:
                print(f"Key '{key}' already exists. Value: {cfg[key]}")
            else:
                cfg[key] = key_dict[key]
    # rewrite config
    with open(CONFIG_PATH, 'w') as cfg_file:
        yaml.dump(cfg, cfg_file)


def update(new_cfg):
    CONFIG_PATH = HOME_DIR / '.config.yml'
    # Update the yaml with new values
    with open(CONFIG_PATH, 'w') as cfg_file:
        yaml.dump(new_cfg, cfg_file)
