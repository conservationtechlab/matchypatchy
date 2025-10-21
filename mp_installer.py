'''
MP Installer
'''
import time
start_time = time.time()
import sys
import os

from PyQt6.QtWidgets import QApplication

# START GUI
from matchypatchy.gui import MainWindow, AlertPopup
from matchypatchy.database import mpdb
from matchypatchy import config
from matchypatchy.algo import models

os.environ["CHROMA_TELEMETRY"] = "FALSE"


def main():
    app = QApplication(sys.argv)
    cfg = config.initiate()
    mpDB = mpdb.MatchyPatchyDB(cfg['DB_DIR'])
    window = MainWindow(mpDB)
    window.show()
    
    if not mpDB.key:
        dialog = AlertPopup(window, prompt='Existing database contains an error. Please select a valid database in the configuration settings.')
        if dialog.exec():
            del dialog
    
    print(f"Startup took {time.time() - start_time:.2f} seconds")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
