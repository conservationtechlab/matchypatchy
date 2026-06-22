'''
Main entry point for MatchyPatchy application
'''

import os
import sys
import time
import logging
from PyQt6.QtWidgets import QApplication

from matchypatchy.logging_config import setup_logger, get_logger
from matchypatchy.gui import MainWindow, AlertPopup
from matchypatchy.database import mpdb
from matchypatchy import config


os.environ["CHROMA_TELEMETRY"] = "FALSE"

if __name__ == "__main__":
    start_time = time.time()
    
    # Setup application-wide logging
    root_logger = setup_logger("matchypatchy.log", log_level=logging.INFO)
    logger = get_logger(__name__)
    logger.info("=" * 70)
    logger.info("MatchyPatchy starting up...")
    
    cfg = config.initiate()
    logger.info(f"Configuration loaded from {cfg['HOME_DIR']}")
        
    mpDB = mpdb.MatchyPatchyDB(cfg['DB_DIR'], logger)
    logger.info(f"Database initialized at: {cfg['DB_DIR']}")

    app = QApplication(sys.argv)
    window = MainWindow(mpDB, logger)
    logger.info("Main window initialized")
    window.show()
    
    if not mpDB.key:
        logger.warning("Database contains an error")
        dialog = AlertPopup(window,
                            prompt="""Existing database contains an error.
                                        Please select a valid database in the configuration settings.""")
        if dialog.exec():
            del dialog
        logger.error("Database error: key mismatch or missing. User prompted to select a valid database.")
    
    startup_time = time.time() - start_time
    logger.info(f"Startup took {startup_time:.2f} seconds")
    logger.info("=" * 70)
    
    exit_code = app.exec()
