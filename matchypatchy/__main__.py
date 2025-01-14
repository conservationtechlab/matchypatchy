'''
Main Function

'''
# GET CWD 
import sys, os
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
from matchypatchy import config

def main():
    cfg = config.initiate()
    mpDB = mpdb.MatchyPatchyDB(cfg['DB_PATH'])
    main_gui.main_display(mpDB, cfg)

if __name__ == "__main__":
    main()
