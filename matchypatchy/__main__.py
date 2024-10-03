'''
Main Function

'''
from .gui import main_gui
from .database import mpdb

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


def main(filepath='matchypatchy.db'):
    mpDB = mpdb.MatchyPatchyDB(filepath)
    main_gui.main_display(mpDB)


if __name__ == "__main__":
    main()
