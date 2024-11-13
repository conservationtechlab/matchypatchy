"""
CONFIG

Create temp dir, log file, db file
Global Variables
"""
from pathlib import Path
import tempfile
import logging


tempfile.tempdir = tempfile.mkdtemp(prefix="MatchyPatchy_")
TEMP_DIR = Path(tempfile.gettempdir())

LOGFILE = Path.cwd() / 'matchpatchy.log'
DB_PATH = Path.cwd() / 'matchypatchy.db'
ML_DIR = Path.cwd() / 'Models'
FRAME_DIR = TEMP_DIR / "Frames"  # frame dir only temporary while processing for animl

logging.basicConfig(filename=LOGFILE, encoding='utf-8', level=logging.DEBUG, force=True)
logging.info('CWD: ' + str(Path.cwd()))
logging.info('mpDB: ' + str(DB_PATH))
logging.info('TEMP_DIR: ' + str(TEMP_DIR))
logging.info('MLDIR: ' + str(ML_DIR))
logging.debug('FRAME_DIR: ' + str(FRAME_DIR))

# CREATE MODEL FOLDER
ML_DIR.mkdir(exist_ok=True)

# GLOBALS
VIEWPOINT = {None: "None", 0: "Left", 1: "Right"}
