"""Logger Configuration"""

import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import os

def setup_logger():
    os.makedirs("logs", exist_ok=True)

    format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    file_handler = TimedRotatingFileHandler(
        "logs/charlotte.log", when="midnight", backupCount=7
    )
    file_handler.setFormatter(logging.Formatter(format_str))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(format_str))

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logging.getLogger(__name__)
