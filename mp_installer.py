'''
MP Installer
'''
import time
start_time = time.time()
import sys
import os
os.environ["CHROMA_TELEMETRY"] = "FALSE"

from PyQt6.QtWidgets import QApplication

# START GUI
from matchypatchy.gui import MainWindow, AlertPopup
from matchypatchy.database import mpdb
from matchypatchy import config
from matchypatchy.algo import models

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
    
    models.update_model_yml()
    print(f"Startup took {time.time() - start_time:.2f} seconds")
    sys.exit(app.exec())
    

if __name__ == "__main__":
    main()
