"""Logger Configuration"""

import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import os

def setup_logger():
    os.makedirs("logs", exist_ok=True)

    format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(format_str))

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)

    return logging.getLogger(__name__)
