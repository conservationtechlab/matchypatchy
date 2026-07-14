"""
Functions for Handling Config Yaml

"""
import os
import sys
from pathlib import Path
import yaml
import animl
        

HOME_DIR = Path.cwd()

def resource_path(relative_path):
    """ Get path to resource whether running in dev or PyInstaller bundle """
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    
    if "__file__" in globals() or "__file__" in locals():
        # Path(__file__).resolve().parent is robust (resolves symlinks)
        install_dir = Path(__file__).resolve().parents[3]
        return install_dir / Path(relative_path)
    
    return os.path.abspath(relative_path)


def initiate(parent_dir=None, project_name="MatchyPatchy-Share"):
    """
    Initiate configuration file with default values if not present
    """
    if parent_dir is None:
        parent_dir = Path.cwd()

    # Append MatchyPatchy-Share to parent_dir
    home_dir = Path(parent_dir) / project_name
    
    # Set global variable for home_dir
    global HOME_DIR
    HOME_DIR = home_dir

    default_cfg = {
        'HOME_DIR': str(home_dir),
        'DB_DIR': str(home_dir / 'Database'),
        'ML_DIR': str(home_dir / 'Models'),
        'THUMBNAIL_DIR': str(home_dir / 'Thumbnails'),
        'VIDEO_FRAMES': 3,
        'REID_KEY': None,
        'VIEWPOINT_KEY': None,
        'DETECTOR_KEY': None,
        'KNN': 100,
        'SEQUENCE_DURATION': 60,
        'SEQUENCE_N': 3,
    }

    # Check if CUDA is available and set DEVICE accordingly
    providers = animl.get_onnx_device()
    if "CUDAExecutionProvider" in providers:
        default_cfg['DEVICE'] = "CUDAExecutionProvider"
    else:
        default_cfg['DEVICE'] = "CPUExecutionProvider"

    CONFIG_PATH = home_dir / '.config.yml'
    if CONFIG_PATH.exists():
        cfg = load_cfg()

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
        Path(home_dir).mkdir(exist_ok=True)
        with open(CONFIG_PATH, 'w') as cfg_file:
            yaml.dump(default_cfg, cfg_file)
        cfg = default_cfg

    # Make sure ML_DIR and DB_DIR exists
    Path(cfg['DB_DIR']).mkdir(exist_ok=True)
    Path(cfg['ML_DIR']).mkdir(exist_ok=True)
    Path(cfg['THUMBNAIL_DIR']).mkdir(exist_ok=True)

    return cfg


def update_project_folder(new_project, new_db):
    # Update home dir and config path
    global HOME_DIR
    HOME_DIR = Path(new_project)

    print("HOME_DIR CHANGED")
    print('HOME_DIR: ' + str(HOME_DIR))

    global CONFIG_PATH
    CONFIG_PATH = HOME_DIR / '.config.yml'

    if not Path(CONFIG_PATH).exists():
        cfg = initiate(parent_dir=Path(new_project).parent, 
                 project_name=Path(new_project).name)
    else:
        cfg = load_cfg()
        cfg['HOME_DIR'] = str(new_project)
        cfg['DB_DIR'] = str(new_db)

    # Check or create ML, Thumbnail and Frame folders
    new_ml = HOME_DIR / "Models"
    new_ml.mkdir(exist_ok=True)
    cfg['ML_DIR'] = str(new_ml)

    new_thumb = HOME_DIR / "Thumbnails"
    new_thumb.mkdir(exist_ok=True)
    cfg['THUMBNAIL_DIR'] = str(new_thumb)

    new_frame = HOME_DIR / "Frames"
    new_frame.mkdir(exist_ok=True)
    cfg['FRAME_DIR'] = str(new_frame)
    # save changes to yml
    update(cfg)


def load_cfg(key=None):
    """Load configuration file, return whole dict or particular key"""
    CONFIG_PATH = HOME_DIR / '.config.yml'
    # Load the config into a dict
    with open(CONFIG_PATH, 'r') as cfg_file:
        cfg = yaml.safe_load(cfg_file)
        if key:
            return cfg[key]
        else:
            return cfg


def add(key_dict, quiet=False):
    """Add new key(s) to config file"""
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
    """Update config file with new values from dict"""
    CONFIG_PATH = HOME_DIR / '.config.yml'
    # Update the yaml with new values
    with open(CONFIG_PATH, 'w') as cfg_file:
        yaml.dump(new_cfg, cfg_file)
