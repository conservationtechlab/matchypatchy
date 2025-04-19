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
           'CONFIG_PATH': str(HOME_DIR / 'config.yml'),
           'DB_DIR': str(HOME_DIR / 'Database'),
           'ML_DIR': str(HOME_DIR / 'Models'),
           'VIDEO_FRAMES': 1
    }

    # check if cfg exists, load
    if Path(default_cfg['CONFIG_PATH']).exists():
        cfg = load(default_cfg['CONFIG_PATH'])
        #TODO : CHECK IF ALL PARAMETERS ARE PRESENT
    # else save default
    else:
        with open(default_cfg['CONFIG_PATH'], 'w') as cfg_file:
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


def load(config_path, key=None):
    # Load the config into a dict
    with open(config_path, 'r') as cfg_file:
        cfg = yaml.safe_load(cfg_file)
        if key:
            return cfg[key]
        else:
            return cfg
        
def add(config_path, key_dict):
    # Load the config into a dict
    print(key_dict)
    with open(config_path, 'r') as cfg_file:
        cfg = yaml.safe_load(cfg_file)
        

        #try cfg[key_dict.keys()]:

        #else:
            



def update(new_cfg):
    # Update the yaml with new values
    with open('config.yml', 'w') as cfg_file:
        yaml.dump(new_cfg, cfg_file)
