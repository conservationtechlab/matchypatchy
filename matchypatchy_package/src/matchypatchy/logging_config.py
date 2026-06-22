import logging
import logging.handlers
from pathlib import Path

def setup_logger(log_file="matchypatchy.log", log_level=logging.INFO):
    """
    Setup application-wide logger that all modules can use.
    Returns the root logger configured with file and console handlers.
    """
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s - %(name)s - %(message)s'
    )
    
    # File handler (rotating to avoid huge log files)
    log_path = Path(log_file)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5  # Keep 5 backup files
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Console handler (optional - for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    return root_logger

def get_logger(name):
    """
    Get a logger for a specific module.
    Use this in all your modules: logger = get_logger(__name__)
    """
    return logging.getLogger(name)