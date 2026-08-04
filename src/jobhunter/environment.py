import os
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv, dotenv_values

from jobhunter.paths import ENV_PATH, ENV_EXAMPLE_PATH


class ENV_KEYS(Enum):
    GEMINI_API_KEY = "GEMINI_API_KEY", "see https://aistudio.google.com"
    PASS_LINKEDIN = "PASS_LINKEDIN",
    EMAIL_LINKEDIN = "EMAIL_LINKEDIN", "linkedin login"
    gmail_app_pass = "gmail_app_pass", "create app pass in google for email reading"
    gmail = "gmail",

    def __init__(self, key: str, description: str | None = None):
        self.key = key
        self.description = description


__env_file_fields = {}


def load_environment():
    global __env_file_fields

    load_dotenv(ENV_PATH)
    __env_file_fields = dotenv_values(ENV_PATH)


def get_missing_fields() -> list[str]:
    global __env_file_fields

    return [
        field
        for field in [value.key for value in ENV_KEYS]
        if not __env_file_fields.get(field)
    ]


def update_env(values: dict[str, str]):
    global __env_file_fields
    lines = []

    if not values:
        return

    __env_file_fields.update(values)

    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    key_indexes = {}

    for index, line in enumerate(lines):
        if not line.startswith("#") and "=" in line and not line.strip() == "=":
            key = line.split("=", 1)[0].strip()
            key_indexes[key] = index

    for key, value in __env_file_fields.items():
        new_line = f"{key}={value}"
        if key in key_indexes:
            lines[key_indexes[key]] = new_line
        else:
            lines.append(new_line)

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    for key, value in values.items():
        os.environ[key] = value


def _generate_env() -> list[str]:
    lines = []
    for value in ENV_KEYS:
        if value.description:
            lines.append(f"# {value.description}")
        lines.append(f"{value.key}=")

    return lines


def create_env_example():
    example = "\n".join(_generate_env())
    ENV_EXAMPLE_PATH.write_text(example, encoding="utf-8")
