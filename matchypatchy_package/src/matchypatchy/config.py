"""
Functions for Handling Config Yaml

"""
import os
import sys
from pathlib import Path
import yaml
import animl


class mpConfig():
    def __init__(self, home_dir):
        """Initiate configuration file with default values if not present"""

        home_dir = Path(home_dir)

        # initiate defualts
        self.HOME_DIR = home_dir
        self.CONFIG_PATH = home_dir / '.config.yml'
        self.DB_DIR = home_dir / 'Database'
        self.ML_DIR = home_dir /  'Models'
        self.THUMBNAIL_DIR = home_dir / 'Thumbnails'
        self.FRAME_DIR = home_dir / 'Frames'
        self.VIDEO_FRAMES = 3
        self.REID_KEY = None
        self.VIEWPOINT_KEY = None
        self.DETECTOR_KEY = None
        self.KNN = 100
        self.SEQUENCE_DURATION = 60
        self.SEQUENCE_N = 3
        # Check if CUDA is available and set DEVICE accordingly
        providers = animl.get_onnx_device(quiet=True)
        if "CUDAExecutionProvider" in providers:
            self.DEVICE = "CUDAExecutionProvider"
        else:
            self.DEVICE = "CPUExecutionProvider"

        # load configuration if it exists
        if home_dir.exists():
            self.load()
        # create a new project folder and save
        else:
            home_dir.mkdir(parents=True, exist_ok=True)
            # create necessary project folders
            self.create_folders()
            # save to yaml
            self.save()

    def load(self):
        """Load configuration from the YAML file if it exists."""
        if self.CONFIG_PATH.exists():
            with open(self.CONFIG_PATH, 'r') as cfg_file:
                cfg = yaml.safe_load(cfg_file)
                self.DB_DIR = Path(cfg.get('DB_DIR', self.HOME_DIR / 'Database'))
                self.ML_DIR = Path(cfg.get('ML_DIR', self.HOME_DIR / 'Models'))
                self.THUMBNAIL_DIR = Path(cfg.get('THUMBNAIL_DIR', self.HOME_DIR / 'Thumbnails'))
                self.FRAME_DIR = Path(cfg.get('FRAME_DIR', self.HOME_DIR / 'Frames'))
                self.VIDEO_FRAMES = cfg.get('VIDEO_FRAMES', 3)
                self.REID_KEY = cfg.get('REID_KEY', None)
                self.VIEWPOINT_KEY = cfg.get('VIEWPOINT_KEY', None)
                self.DETECTOR_KEY = cfg.get('DETECTOR_KEY', None)
                self.KNN = cfg.get('KNN', 100)
                self.SEQUENCE_DURATION = cfg.get('SEQUENCE_DURATION', 60)
                self.SEQUENCE_N = cfg.get('SEQUENCE_N', 3)
                self.DEVICE = cfg.get('DEVICE', "CPUExecutionProvider")

        # config file not found, save the current defaults
        else:
            print(f"Configuration file not found at {self.CONFIG_PATH}. Saving default configuration.")
            self.HOME_DIR.mkdir(parents=True, exist_ok=True)
            self.set_default()
            self.save()

        # make sure all necessary directories exist
        self.create_folders()


    def save(self):
        """Save the current configuration to the YAML file."""
        output_cfg = {
            'HOME_DIR': str(self.HOME_DIR),
            'DB_DIR': str(self.DB_DIR),
            'ML_DIR': str(self.ML_DIR),
            'THUMBNAIL_DIR': str(self.THUMBNAIL_DIR),
            'VIDEO_FRAMES': self.VIDEO_FRAMES,
            'REID_KEY': self.REID_KEY,
            'VIEWPOINT_KEY': self.VIEWPOINT_KEY,
            'DETECTOR_KEY': self.DETECTOR_KEY,
            'KNN': self.KNN,
            'SEQUENCE_DURATION': self.SEQUENCE_DURATION,
            'SEQUENCE_N': self.SEQUENCE_N,
            'DEVICE': self.DEVICE,
        }
        with open(self.CONFIG_PATH, 'w') as cfg_file:
            yaml.dump(output_cfg, cfg_file)

    def set_default(self):
        """Reset the configuration to default values."""
        self.DB_DIR = self.HOME_DIR / 'Database'
        self.ML_DIR = self.HOME_DIR /  'Models'
        self.THUMBNAIL_DIR = self.HOME_DIR / 'Thumbnails'
        self.FRAME_DIR = self.HOME_DIR / 'Frames'
        self.VIDEO_FRAMES = 3
        self.REID_KEY = None
        self.VIEWPOINT_KEY = None
        self.DETECTOR_KEY = None
        self.KNN = 100
        self.SEQUENCE_DURATION = 60
        self.SEQUENCE_N = 3
        if "CUDAExecutionProvider" in animl.get_onnx_device(quiet=True):
            self.DEVICE = "CUDAExecutionProvider"
        else:
            self.DEVICE = "CPUExecutionProvider"

    def create_folders(self):
        """Create necessary project folders if they do not exist."""
        self.DB_DIR.mkdir(parents=True, exist_ok=True)
        self.ML_DIR.mkdir(parents=True, exist_ok=True)
        self.THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
        self.FRAME_DIR.mkdir(parents=True, exist_ok=True)

    def update(self, key_dict):
        """Update the configuration with new key-value pairs."""
        for key, value in key_dict.items():
            setattr(self, key, value)

        # rewrite config
        self.save()


# ==============================================================================
def resource_path(relative_path):
    # TODO: test with installer
    """ Get path to resource whether running in dev or installed bundle """
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)

    if "__file__" in globals() or "__file__" in locals():
        current_location = Path(__file__).resolve()
        if 'site-packages' in current_location.parts:
            matchypatchy_dir = current_location.parents[0]  # Go up 1 level
        else:
            matchypatchy_dir = current_location.parents[2]  # Go up 2 levels
        # Assumes this function is in src/matchypatchy/
        return matchypatchy_dir / relative_path

    return os.path.abspath(relative_path)


def asset_path(relative_path):
    """ Get path to resource whether running in dev or installed bundle """
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)

    if "__file__" in globals() or "__file__" in locals():
        current_location = Path(__file__).resolve()

        if 'site-packages' in current_location.parts:
            matchypatchy_dir = current_location.parents[0]  # tbd
        else:
            matchypatchy_dir =current_location.parents[0]

        return matchypatchy_dir / 'assets' / relative_path

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
        'SMART_FRAMES': True,
        'VIDEO_FPS': 1,
        'N_FRAMES': 3,
        'REID_KEY': None,
        'VIEWPOINT_KEY': None,
        'DETECTOR_KEY': None,
        'KNN': 100,
        'SEQUENCE_DURATION': 60,
        'SEQUENCE_N': 3,
    }

    # Check if CUDA is available and set DEVICE accordingly
    providers = animl.get_onnx_device(quiet=True)
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
