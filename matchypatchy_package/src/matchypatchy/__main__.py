'''
Main entry point for MatchyPatchy application
'''

import os
import sys
import time
import logging
from PyQt6.QtWidgets import QApplication

from logging_config import setup_logger, get_logger
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
    logger.info("=" * 70)
    
    try:
        app = QApplication(sys.argv)
        logger.info("Qt Application created")
        
        cfg = config.initiate()
        logger.info(f"Configuration loaded from: {cfg.get('CONFIG_PATH', 'default')}")
        
        mpDB = mpdb.MatchyPatchyDB(cfg['DB_DIR'], logger)
        logger.info(f"Database initialized at: {cfg['DB_DIR']}")
        
        window = MainWindow(mpDB, logger)
        window.show()
        logger.info("MainWindow displayed")
        
        if not mpDB.key:
            logger.warning("Database contains an error")
            dialog = AlertPopup(window,
                                prompt="""Existing database contains an error.
                                          Please select a valid database in the configuration settings.""")
            if dialog.exec():
                del dialog
        
        startup_time = time.time() - start_time
        logger.info(f"Startup took {startup_time:.2f} seconds")
        logger.info("=" * 70)
        
        exit_code = app.exec()
        
    except Exception as e:
        logger.error(f"Fatal error during startup: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        logger.info("=" * 70)
        logger.info("MatchyPatchy shutting down")
        logger.info("=" * 70)
        sys.exit(exit_code)