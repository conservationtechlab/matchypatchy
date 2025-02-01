"""
Functions for Handling Config

"""
from pathlib import Path
import tempfile
import logging 
import yaml


def initiate():
    cfg_path = Path('config.yml')

    tempfile.tempdir = tempfile.mkdtemp(prefix="MatchyPatchy_")

    default_cfg = {'TEMP_DIR': str(Path(tempfile.gettempdir())),
           'LOG_PATH': str(Path.cwd() / 'matchpatchy.log'),
           'DB_PATH': str(Path.cwd() / 'matchypatchy.db'),
           'ML_DIR': str(Path.cwd() / 'Models'),
           'FRAME_DIR': str(Path(tempfile.gettempdir()) / "Frames"),  # frame dir only temporary while processing for animl
    }

    # check if cfg exists, load
    if cfg_path.exists():
        cfg = load()
    # else save default
    else:
        with open(cfg_path, 'w') as cfg_file:
            yaml.dump(default_cfg, cfg_file)
        cfg = default_cfg

    # Make sure ML_DIR exists
    Path(cfg['ML_DIR']).mkdir(exist_ok=True)
        
    # LOG CONFIG
    logging.basicConfig(filename=cfg['LOG_PATH'], encoding='utf-8', level=logging.DEBUG, force=True)
    logging.info('CWD: ' + str(Path.cwd()))
    logging.info('mpDB: ' + cfg['DB_PATH'])
    logging.info('TEMP_DIR: ' + cfg['TEMP_DIR'])
    logging.info('ML_DIR: ' + cfg['ML_DIR'])
    logging.debug('FRAME_DIR: ' + cfg['FRAME_DIR'])

    return cfg


def load(key=None):
    # Load the config into a dict
    with open('config.yml', 'r') as cfg_file:
        cfg = yaml.safe_load(cfg_file)
        if key:
            return cfg[key]
        else:
            return cfg


def update(new_cfg):
    # Update the yaml with new values
    with open('config.yml', 'w') as cfg_file:
        yaml.dump(new_cfg, cfg_file)
