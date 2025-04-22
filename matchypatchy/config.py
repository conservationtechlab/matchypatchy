"""
Functions for Handling Config

"""
from pathlib import Path
import tempfile
import logging 
import yaml

HOME_DIR = Path.cwd() / "MatchyPatchy-Share"

def initiate():
    # create shareable home folder
    Path(HOME_DIR).mkdir(exist_ok=True)

     # temp dir
    tempfile.tempdir = tempfile.mkdtemp(prefix="MatchyPatchy_")
    
    default_cfg = {'TEMP_DIR': str(Path(tempfile.gettempdir())),
           'LOG_PATH': str(HOME_DIR / 'matchpatchy.log'),
           'DB_DIR': str(HOME_DIR / 'Database'),
           'ML_DIR': str(HOME_DIR / 'Models'),
           'FRAME_DIR': str(Path(tempfile.gettempdir()) / 'Frames'),
           'VIDEO_FRAMES': 1
    }

    # check if cfg exists, load
    if Path('config.yml').exists():
        cfg = load()
        for key in default_cfg.keys():
            if key not in cfg:
                cfg[key] = default_cfg[key]
        with open('config.yml', 'w') as cfg_file:
            yaml.dump(cfg, cfg_file)
    # else save default
    else:
        with open('config.yml', 'w') as cfg_file:
            yaml.dump(default_cfg, cfg_file)
        cfg = default_cfg

    # Make sure ML_DIR and DB_DIR exists
    Path(cfg['DB_DIR']).mkdir(exist_ok=True)
    Path(cfg['ML_DIR']).mkdir(exist_ok=True)
        
    # LOG CONFIG
    logging.basicConfig(filename=cfg['LOG_PATH'], encoding='utf-8', level=logging.DEBUG, force=True)
    logging.info('CWD: ' + str(HOME_DIR))
    logging.info('DB_DIR: ' + cfg['DB_DIR'])
    logging.info('TEMP_DIR: ' + cfg['TEMP_DIR'])
    logging.info('ML_DIR: ' + cfg['ML_DIR'])

    return cfg


def load(key=None):
    # Load the config into a dict
    with open('config.yml', 'r') as cfg_file:
        cfg = yaml.safe_load(cfg_file)
        if key:
            return cfg[key]
        else:
            return cfg

    
def add(key_dict, quiet=False):
    # Load the config into a dict
    with open('config.yml', 'r') as cfg_file:
        cfg = yaml.safe_load(cfg_file)
        for key in  key_dict.keys():
            if key in cfg and not quiet:
                print(f"Key '{key}' already exists. Value: {cfg[key]}")
            else:
                cfg[key] = key_dict[key]
    # rewrite config
    with open('config.yml', 'w') as cfg_file:
        yaml.dump(cfg, cfg_file)


def update(new_cfg):
    # Update the yaml with new values
    with open('config.yml', 'w') as cfg_file:
        yaml.dump(new_cfg, cfg_file)
