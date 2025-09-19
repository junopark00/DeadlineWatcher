# -*- coding: utf-8 -*-

import logging
from logging.handlers import RotatingFileHandler
import os
from watcher.config_loader import config

def setup_logger():
    log_dir = os.path.expanduser(config.log_dir)
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, config.log_file)

    logger = logging.getLogger("Watcher")
    logger.setLevel(logging.DEBUG)

    if not logger.hasHandlers():
        fh = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3)
        formatter = logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger
