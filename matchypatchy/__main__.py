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
LOGFILE = os.path.join(os.getcwd(),'matchpatchy.log')
logging.basicConfig(filename=LOGFILE, encoding='utf-8', level=logging.DEBUG, force=True) 
logging.info('CWD: ' + os.getcwd())


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
    filepath = os.path.join(os.getcwd(), 'matchypatchy.db')
    logging.info('mpDB: ' + filepath)
    mpDB = mpdb.MatchyPatchyDB(filepath)
    main_gui.main_display(mpDB)


if __name__ == "__main__":
    main()
