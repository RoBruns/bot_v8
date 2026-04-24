import logging
import os
import sys
from datetime import datetime

def setup_logger():
    """
    Sets up the logger to write to a file in the 'logs' directory.
    The log file name matches the current date and time (Brazilian pattern).
    """
    # Create logs directory if it doesn't exist
    # If running as a PyInstaller bundle, executable path is in sys.executable
    # Otherwise, it's the current working directory handling.
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.getcwd()
        
    logs_dir = os.path.join(base_dir, 'logs')
    
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # File name format: log_dd-mm-yyyy_HH-MM-SS.log
    now = datetime.now()
    log_filename = f"log_{now.strftime('%d-%m-%Y_%H-%M-%S')}.log"
    log_path = os.path.join(logs_dir, log_filename)

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%d/%m/%Y %H:%M:%S',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler(sys.stdout) # Keep printing to console as well
        ]
    )

    logging.info(f"Log iniciado: {log_path}")
    return log_path
