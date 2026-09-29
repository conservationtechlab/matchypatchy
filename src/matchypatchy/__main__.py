'''
Main entry point for MatchyPatchy application
'''

import os
import sys
import time
from pathlib import Path
from PyQt6.QtWidgets import QApplication

from matchypatchy.logging_config import setup_logger, get_logger
from matchypatchy.gui import MainWindow


def setup_cuda_path():
    """Dynamically find and add NVIDIA CUDA/cuDNN libraries to PATH"""
    try:
        # Try to find nvidia packages in site-packages
        import site
        site_packages = site.getsitepackages()
        
        if isinstance(site_packages, str):
            site_packages = [site_packages]
        
        for site_dir in site_packages:
            nvidia_lib_path = Path(site_dir) / "nvidia"
            
            if nvidia_lib_path.exists():
                dll_folders = [
                    nvidia_lib_path / "cuda_runtime" / "bin",
                    nvidia_lib_path / "cuda_nvrtc" / "bin",
                    nvidia_lib_path / "cublas" / "bin",
                    nvidia_lib_path / "cudnn" / "bin",
                ]
                
                for folder in dll_folders:
                    if folder.exists():
                        os.environ['PATH'] = str(folder) + os.pathsep + os.environ['PATH']
                
                return True
    except Exception as e:
        print(f"Warning: Could not setup CUDA path: {e}")
    
    return False


if __name__ == "__main__":
    start_time = time.time()
    
    # Setup application-wide logging
    root_logger = setup_logger()
    logger = get_logger(__name__)
    logger.info("=" * 70)
    logger.info("MatchyPatchy starting up...")

    exit_code = 1  # Default to error; overwritten on successful run

    try:
        setup_cuda_path()
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