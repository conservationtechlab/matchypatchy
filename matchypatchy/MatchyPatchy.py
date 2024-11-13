'''
Installable Version of Main Function

'''
# GET CWD
import os
import sys
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    os.chdir(application_path)

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
from matchypatchy.gui import main_gui
from matchypatchy.database import mpdb
from matchypatchy.config import DB_PATH

def main():
    mpDB = mpdb.MatchyPatchyDB(DB_PATH)
    main_gui.main_display(mpDB)

if __name__ == "__main__":
    main()
