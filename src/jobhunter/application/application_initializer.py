import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from jobhunter.application import utils
from jobhunter import paths
from jobhunter.cli.input import wait_for_command
from jobhunter.config.config import create_config_example, load_config, \
    save_config
from jobhunter.config.models import Config
from jobhunter.environment import load_environment, get_missing_fields, update_env, create_env_example
from jobhunter.paths import PROGRAM_DATA_DIR, SETTINGS_DIR, CANDIDATE_INFO_DIR, SAVES_DIR

log = logging.getLogger(__name__)


class ApplicationInitializer:
    @staticmethod
    def ensure_structure():
        log.debug("Creating application data structure...")
        PROGRAM_DATA_DIR.mkdir(exist_ok=True)
        SETTINGS_DIR.mkdir(exist_ok=True)
        CANDIDATE_INFO_DIR.mkdir(exist_ok=True)
        SAVES_DIR.mkdir(exist_ok=True)
        create_config_example()
        create_env_example()

    @staticmethod
    def _read_candidate_info(path: Path) -> str:
        data = path.read_text()
        if not data:
            raise ValueError("Empty candidate info file.")
        return data

    @staticmethod
    def ensure_config() -> Config:
        log.info("Loading config...")

        first_prompt = (
            "No config or file structure problem. See 'config.yaml.example'. "
            "Do you want to fill it manually in opened File Manager?"
        )
        common_prompt = "Do you want to fill config file manually in opened File Manager?"
        handlers = {
            "y": utils.open_folder,
            "open": utils.open_folder,
            "check": ApplicationInitializer._retry_config,
            "exit": utils.finish_app
        }
        while True:
            command = wait_for_command(
                menu_commands_available=False,
                first_prompt=first_prompt, common_prompt=common_prompt,
                yes_available=True,
                open_available=True, check_available=True)

            config = handlers[command]()
            if type(config) == Config:
                return config

    @staticmethod
    def _retry_config() -> Config:
        while True:
            try:
                config = load_config()
            except FileNotFoundError:
                print("'config.yaml' not found.")
            except PermissionError:
                print("Unable to read config.yaml: access denied.")
            except yaml.YAMLError:
                print("'config.yaml' is not valid. See 'config.yaml.example'.")
            except ValidationError as e:
                e: ValidationError
                missing_fields = [
                    error["loc"]
                    for error in e.errors()
                    if error["type"] == "missing"
                ]
                validation_errors = [
                    error["msg"]
                    for error in e.errors()
                    if error["type"] == "value_error"
                ]
                print("'config.yaml' is not valid. See 'config.yaml.example'.")
                if missing_fields:
                    print(
                        f"Next fields are missing:",
                        *('.'.join(map(str, field)) for field in missing_fields),
                        sep="\n"
                    )
                if validation_errors:
                    print(*validation_errors, sep="\n")
            except Exception:
                log.error("Unexpected error while loading 'config.yaml'.")
                log.debug("Unexpected error info:\n", exc_info=True)
            else:
                log.info("Config is valid and read.")
                return config
            prompt = "Enter 'check' if you have finished or 'open' to open File Manager."
            handlers = {
                "open": utils.open_folder,
                "exit": utils.finish_app
            }

            command = wait_for_command(
                menu_commands_available=False, common_prompt=prompt,
                open_available=True, check_available=True
            )
            if not command == "check":
                handlers[command]()

    @staticmethod
    def ensure_env():
        log.info("Loading environment...")

        first_prompt = (
            "No needed data in .env file. If you want to fill it manually in console, enter 'yes'."
            "Else enter 'no' and create or fill it in opened File Manager. Then enter 'check'. See '.env.example'.")
        common_prompt = "Do you want to fill env file manually in console?"
        handlers = {
            "n": utils.open_folder,
            "open": utils.open_folder,
            "exit": utils.finish_app
        }
        while True:
            load_environment()
            missing_fields = get_missing_fields()
            if missing_fields:
                command = wait_for_command(
                    menu_commands_available=False,
                    first_prompt=first_prompt, common_prompt=common_prompt,
                    open_available=True, yes_available=True,
                    no_available=True, check_available=True
                )
                if command == "y":
                    ApplicationInitializer._request_env_variables(missing_fields)
                    log.info("All entered environment variables saved.")
                    return
                if not command == "check":
                    handlers[command]()
            break

    @staticmethod
    def _request_env_variables(variables: list[str]):
        result = {}
        for var in variables:
            result[var] = input(f"Enter {var}: ")
        update_env(result)

    @staticmethod
    def ensure_candidate_info(config: Config) -> str:
        log.info("Loading candidate info...")
        file_path = paths.CANDIDATE_INFO_DIR / config.candidate_info_file_name
        if not config.candidate_info_file_name or not file_path.exists():
            first_prompt = (
                f"Candidate info not found. Create txt file with info about yourself in "
                f"{paths.CANDIDATE_INFO_DIR} folder and enter its name here. Open File Manager?"
            )
            common_prompt = "Do you want to open folder in File Manager."
            command = wait_for_command(
                menu_commands_available=False,
                first_prompt=first_prompt, common_prompt=common_prompt,
                yes_available=True,
                no_available=True, open_available=True
            )
            if command in ["y", "open"]:
                utils.open_folder(paths.CANDIDATE_INFO_DIR)
            if command == "exit":
                utils.finish_app()

            while True:
                file_name = input("Enter file name: ")
                file_path = paths.CANDIDATE_INFO_DIR / file_name
                about_me = ""
                try:
                    about_me = ApplicationInitializer._read_candidate_info(file_path)
                except FileNotFoundError:
                    print(f"There is no file with path '{file_path}'.")
                except ValueError:
                    print("This file is empty. Fill it with info about yourself.")

                if about_me:
                    save_config(config)
                    return about_me

                common_prompt = "Do you want to open folder in File Manager again?"
                command = wait_for_command(
                    menu_commands_available=False, common_prompt=common_prompt,
                    yes_available=True, no_available=True, open_available=True
                )
                if command in ["y", "open"]:
                    utils.open_folder(paths.CANDIDATE_INFO_DIR)
                if command == "exit":
                    utils.finish_app()
        else:
            while True:
                about_me = ""
                try:
                    about_me = ApplicationInitializer._read_candidate_info(file_path)
                except ValueError:
                    print(f"File '{file_path}' is empty. Fill it with info about yourself.")

                if about_me:
                    save_config(config)
                    return about_me

                common_prompt = "Do you want to open folder in File Manager?"
                command = wait_for_command(
                    menu_commands_available=False, common_prompt=common_prompt,
                    yes_available=True, no_available=True, open_available=True
                )
                if command in ["y", "open"]:
                    utils.open_folder(paths.CANDIDATE_INFO_DIR)
                if command == "exit":
                    utils.finish_app()

