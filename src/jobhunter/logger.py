import logging
from datetime import datetime
from pathlib import Path

from paths import LOGS_DIR


def setup_logger(logging_level: int, console_logging_level: int):
    file_name = Path(f"log{datetime.now().strftime('%Y%b%d%H%M%S')}").with_suffix(".log")
    LOGS_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(LOGS_DIR / file_name, encoding="utf-8")
    console_handler = logging.StreamHandler()

    file_handler.setLevel(logging_level)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(funcName)s | %(levelname)s: %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    console_handler.setLevel(console_logging_level)
    console_formatter = logging.Formatter(
        "%(levelname)s: %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
