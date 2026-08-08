import subprocess
import sys
from pathlib import Path

from jobhunter.application.errors import ExitApplication
from jobhunter.config.models import Config
from jobhunter.paths import SETTINGS_DIR


def finish_app():
    raise ExitApplication


def open_folder(path: Path = None):
    path_to_open = path if path else SETTINGS_DIR
    if sys.platform == "win32":
        subprocess.Popen(["explorer", str(path_to_open)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path_to_open)])
    else:
        subprocess.Popen(["xdg-open", str(path_to_open)])


def get_available_sites(config: Config):
    return [site for site in config.sites.model_dump()]
