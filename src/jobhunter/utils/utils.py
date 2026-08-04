import subprocess
import sys
from pathlib import Path

from jobhunter.config.config import create_config_example
from jobhunter.environment import create_env_example
from jobhunter.paths import PROGRAM_DATA_DIR, SETTINGS_DIR, CANDIDATE_INFO_DIR, SAVES_DIR


def ensure_structure():
    PROGRAM_DATA_DIR.mkdir(exist_ok=True)
    SETTINGS_DIR.mkdir(exist_ok=True)
    CANDIDATE_INFO_DIR.mkdir(exist_ok=True)
    SAVES_DIR.mkdir(exist_ok=True)
    create_config_example()
    create_env_example()


def open_folder(path: Path = None):
    path_to_open = path if path else SETTINGS_DIR
    if sys.platform == "win32":
        subprocess.Popen(["explorer", str(path_to_open)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path_to_open)])
    else:
        subprocess.Popen(["xdg-open", str(path_to_open)])


def read_candidate_info(path: Path):
    data = path.read_text()
    if not data:
        raise ValueError("Empty candidate info file.")
    return data
