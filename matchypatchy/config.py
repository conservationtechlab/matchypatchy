"""
CONFIG


"""
import os
import tempfile
import logging

tempfile.tempdir = tempfile.mkdtemp(prefix="MatchyPatchy_")

LOGFILE = os.path.join(os.getcwd(), 'matchpatchy.log')
DB_PATH = os.path.join(os.getcwd(), 'matchypatchy.db')
ML_PATH = os.path.join(os.getcwd(), 'Models')
TEMPDIR =tempfile.gettempdir()

logging.basicConfig(filename=LOGFILE, encoding='utf-8', level=logging.DEBUG, force=True) 
logging.info('CWD: ' + os.getcwd())
logging.info('mpDB: ' + DB_PATH)
logging.info('TEMPDIR: ' + TEMPDIR) # prints the current temporary directory

# CREATE MODEL FOLDER