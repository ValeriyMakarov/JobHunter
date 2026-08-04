from pathlib import Path
from platformdirs import user_config_dir

PROGRAM_DATA_DIR = Path(user_config_dir("JobHunter", appauthor=False))
SETTINGS_DIR = PROGRAM_DATA_DIR / "settings"
CONFIG_PATH = SETTINGS_DIR / "config.yaml"
CONFIG_EXAMPLE_PATH = SETTINGS_DIR / "config.yaml.example"
CANDIDATE_INFO_DIR = SETTINGS_DIR / "candidate_info"
CONTEXT_JSON_PATH = SETTINGS_DIR / "context.json"
ENV_PATH = SETTINGS_DIR / ".env"
ENV_EXAMPLE_PATH = SETTINGS_DIR / ".env.example"
SAVES_DIR = SETTINGS_DIR / "saves"

LOGS_DIR = PROGRAM_DATA_DIR / "logs"
ERRORS_DIR = LOGS_DIR / "errors"
