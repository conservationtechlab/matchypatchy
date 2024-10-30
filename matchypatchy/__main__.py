'''
Main Function

'''
# GET CWD 
import sys, os
import logging

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    os.chdir(application_path)

# SET UP LOGGING
from . import config
logging.basicConfig(filename=config.LOGFILE, encoding='utf-8', level=logging.DEBUG, force=True) 
logging.info('CWD: ' + os.getcwd())
logging.info('mpDB: ' + config.DB_PATH)
logging.info('TEMPDIR: ' + config.TEMPDIR) # prints the current temporary directory


# DISABLE HUGGINGFACE
import requests
from huggingface_hub import configure_http_backend
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
def backend_factory() -> requests.Session:
    session = requests.Session()
    session.verify = False
    return session
configure_http_backend(backend_factory=backend_factory)


# START GUI
from .gui import main_gui
from .database import mpdb

def main():   
    mpDB = mpdb.MatchyPatchyDB(config.DB_PATH)
    main_gui.main_display(mpDB)


if __name__ == "__main__":
    main()
