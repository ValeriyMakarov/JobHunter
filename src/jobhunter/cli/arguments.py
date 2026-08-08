import argparse
import logging

log = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging to the log file."
    )
    parser.add_argument(
        "--console-debug",
        action="store_true",
        help="Enable debug logging to the console."
    )
    return parser.parse_args()
