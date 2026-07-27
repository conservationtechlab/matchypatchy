'''
Main entry point for MatchyPatchy application
'''

import os
import sys
import time
from PyQt6.QtWidgets import QApplication

from matchypatchy.logging_config import setup_logger, get_logger
from matchypatchy.gui import MainWindow


os.environ["CHROMA_TELEMETRY"] = "FALSE"

if __name__ == "__main__":
    start_time = time.time()
    
    # Setup application-wide logging
    root_logger = setup_logger()
    logger = get_logger(__name__)
    logger.info("=" * 70)
    logger.info("MatchyPatchy starting up...")

    try:
        app = QApplication(sys.argv)
        window = MainWindow(logger)
        logger.info("Main window initialized")
        window.show()
        
        startup_time = time.time() - start_time
        logger.info(f"Startup took {startup_time:.2f} seconds")
        logger.info("-" * 70)
        
        exit_code = app.exec()

    except Exception as e:
        logger.error(f"Fatal error during startup: {e}", exc_info=True)
        exit_code = 1
    
    finally:
        logger.info("MatchyPatchy shutting down")
        logger.info("=" * 70)
        sys.exit(exit_code)