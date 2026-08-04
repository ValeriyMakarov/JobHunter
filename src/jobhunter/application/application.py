import logging
import re
from inspect import cleandoc

import yaml
from pydantic import ValidationError

from jobhunter import paths
from jobhunter.utils import utils
from jobhunter.analizer.analyzers import PythonAQAVacancyAnalyzer, PYTHON_AQA_PROMPT
from jobhunter.app_state import AppState
from jobhunter.application.entities import CommandArgs
from jobhunter.application.errors import ExitApplication
from jobhunter.config.config import load_config, safe_load_config, save_config
from jobhunter.environment import load_environment, get_missing_fields, update_env
from jobhunter.site_managers.base_site_manager import BaseSiteManager
from jobhunter.site_managers.site_manager_provider import SiteManagerProvider

log = logging.getLogger(__name__)

# todo: обработать открытый файл вначале работы
class Application:
    def __init__(self):
        self.state: AppState | None = None
        self.config = safe_load_config()
        self.about_me = ""
        self._available_sites = []
        self._available_commands = [
            "exit", "help", "process", "run", "collect",
            "parse", "analyze", "apply", "settings"
        ]
        self.menu_commands_handlers = {
            "exit": self._exit,
            "help": self._help,
            "process": self._process,
            "run": self._run,
            "collect": self._collect,
            "parse": self._parse,
            "analyze": self._analyze,
            "apply": self._apply,
            "settings": self._settings
        }
        self._site_provider = SiteManagerProvider(self.config)

    def run(self):
        utils.ensure_structure()

        # config
        if not self.config:
            self._ensure_config()
        self._available_sites.extend(self.config.sites.model_dump())
        self.state = AppState(self.config.application_data_file)
        #env
        self._ensure_env()
        #about_me
        self._ensure_candidate_info()
        #save
        self._resolve_checkpoints()

        while True:
            command, *args = self._wait_for_command()
            self.menu_commands_handlers[command](CommandArgs(names=args))

    def _collect(self, args: CommandArgs):
        """
        Collect job links from specified sites.
        If no sites are specified, links will be collected from all available sites.
        """
        site_names = args.names if args.names else self._available_sites
        managers: list[BaseSiteManager] = [
            self._site_provider.get_manager(name) for name in site_names
        ]

        for manager in managers:
            job_list = manager.get_job_list()
            self.state.current_vacancies_collected_extend(job_list)

    def _parse(self, args: CommandArgs):
        """
        Parse data about jobs using previously collected job links from specified sites.
        If no sites are specified, jobs data will be collected from all available sites.
        """
        site_names = args.names if args.names else self._available_sites
        managers: list[BaseSiteManager] = [
            self._site_provider.get_manager(name) for name in site_names
        ]
        vacancy_list_to_use = (
            self.state.checkpoint_vacancies_not_parsed_list
            if args.use_checkpoint
            else self.state.current_vacancies_collected_list)

        for manager in managers:
            corresponding_vacancy_list = [
                vacancy_data
                for vacancy_data in vacancy_list_to_use
                if manager.SITE_NAME in vacancy_data.vacancy_link
            ]
            data_list = manager.collect_vacancies_data(corresponding_vacancy_list)
            if args.use_checkpoint:
                self.state.checkpoint_vacancies_not_analyzed_extend(data_list)
            else:
                self.state.current_vacancies_parsed_extend(data_list)

    def _analyze(self, args: CommandArgs):
        """
        Analyze collected jobs data using Gemini neural network.
        """
        analyzer = PythonAQAVacancyAnalyzer()
        prompt = PYTHON_AQA_PROMPT
        parsed_list_to_use = (
            self.state.checkpoint_vacancies_not_analyzed_list
            if args.use_checkpoint
            else self.state.current_vacancies_parsed_list)

        analyzed_data_list = analyzer.analyze_all(
            parsed_list_to_use, prompt=prompt, about_me=self.about_me
        )
        if args.use_checkpoint:
            self.state.checkpoint_vacancies_not_saved_extend(analyzed_data_list)
        else:
            self.state.current_vacancies_analyzed_extend(analyzed_data_list)

    def _apply(self, args: CommandArgs):
        """
        Not implemented.
        Open all suitable job links by one to apply.
        """
        print("This command is not implemented.")

    def _settings(self, args: CommandArgs):
        """
        Not implemented.
        Change app settings.
        """
        print("This command is not implemented.")

    def _run(self, args: CommandArgs):
        """
        Not implemented.
        Collect all jobs data from specified sites, analyze it and open all suitable jobs links by one to apply.
        If no sites are specified, jobs data will be collected from all available sites.
        """
        print("This command is not implemented.")

    def _process(self, args: CommandArgs):
        """
        Collect all jobs data from specified sites and analyze it.
        If no sites are specified, jobs data will be collected from all available sites.
        """
        self._collect(args)
        self._parse(args)
        self._analyze(args)

    def _help(self, args: CommandArgs):
        """
        Get info about available menu commands.
        """
        commands = args.names if args.names else self._available_commands
        for command_name in commands:
            if command_name not in self._available_commands:
                log.error(f"{command_name} is not available command.")
                return

        for command in commands:
            func = self.menu_commands_handlers[command]
            doc = cleandoc(func.__doc__) if func.__doc__ else "No info."
            print(f"Command '{command}':\n{doc}", end="\n\n")

    def _exit(self, *_):
        """
        Save all new application data to the file and quit.
        """
        self.state.save_analysed_data()
        self._finish_app()

    def _ensure_config(self):
        first_prompt = (
            "No config or file structure problem. See 'config.yaml.example'. "
            "Do you want to fill it manually in opened File Manager?"
        )
        common_prompt = "Do you want to fill config file manually in opened File Manager?"
        handlers = {
            "y": utils.open_folder,
            "open": utils.open_folder,
            "check": self._retry_config,
            "exit": self._finish_app
        }

        command = self._wait_for_command(
            first_prompt=first_prompt, common_prompt=common_prompt,
            menu_commands=False, yes_available=True,
            open_available=True, check_available=True)

        handlers[command]()

    def _retry_config(self):
        while True:
            try:
                self.config = load_config()
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
                break
            prompt = "Enter 'check' if you have finished or 'open' to open File Manager."
            handlers = {
                "open": utils.open_folder,
                "exit": self._finish_app
            }

            command = self._wait_for_command(
                common_prompt=prompt, menu_commands=False,
                open_available=True, check_available=True
            )
            if not command == "check":
                handlers[command]()

    def _wait_for_command(
                    self, first_prompt: str = None, common_prompt: str = "",
                    menu_commands: bool = True, yes_available: bool = False,
                    no_available: bool = False, check_available: bool = False,
                    open_available: bool = False, hint: bool = True
    ) -> tuple[str, list[str]] | str:
        exit_regexp = {
            "exit": re.compile(r"^\s*exit\s*$", re.IGNORECASE),
        }
        commands_regexps = {
            "help": re.compile(
                fr"^\s*help(?:\s+(?:{'|'.join(self._available_commands)}))*\s*$",
                re.IGNORECASE),
            "process": re.compile(
                fr"^\s*process(?:\s+(?:{'|'.join(self._available_sites)}))*\s*$",
                re.IGNORECASE),
            "run": re.compile(
                fr"^\s*run(?:\s+(?:{'|'.join(self._available_sites)}))*\s*$",
                re.IGNORECASE),
            "parse": re.compile(
                fr"^\s*parse(?:\s+(?:{'|'.join(self._available_sites)}))*\s*$",
                re.IGNORECASE),
            "analyze": re.compile(r"^\s*analyze\s*$", re.IGNORECASE),
            "settings": re.compile(r"^\s*settings\s*$", re.IGNORECASE)
        }
        yes_regexps = {
            "y": re.compile(r"^\s*y\s*$", re.IGNORECASE),
            "yes": re.compile(r"^\s*yes\s*$", re.IGNORECASE),
        }
        no_regexps = {
            "n": re.compile(r"^\s*n\s*$", re.IGNORECASE),
            "no": re.compile(r"^\s*no\s*$", re.IGNORECASE),
        }
        check_regexp = {
            "check": re.compile(r"^\s*check\s*$", re.IGNORECASE)
        }
        open_regexp = {
            "open": re.compile(r"^\s*open\s*$", re.IGNORECASE)
        }

        permitted_answers = dict(exit_regexp)
        if menu_commands:
            permitted_answers.update(commands_regexps)
        if yes_available:
            permitted_answers.update(yes_regexps)
        if no_available:
            permitted_answers.update(no_regexps)
        if check_available:
            permitted_answers.update(check_regexp)
        if open_available:
            permitted_answers.update(open_regexp)

        permitted_hint_commands = ["y", "n", "help", "check", "open", "exit"]
        hint_text = f"[{'/'.join(i for i in permitted_hint_commands if i in permitted_answers.keys())}] "

        common_prompt = f"{common_prompt}\n{hint_text if hint else ''}> "
        if first_prompt is None:
            first_prompt = common_prompt
        else:
            first_prompt = f"{first_prompt}\n{hint_text if hint else ''}> "

        text = input(first_prompt)
        while True:
            command: str = ""
            args: list[str] = []
            try:
                command, *args = [i.lower() for i in text.split()]
                if not re.match(permitted_answers[command], text):
                    raise ValueError
                if command in no_regexps.keys():
                    command = "n"
                if command in yes_regexps.keys():
                    command = "y"
                if args:
                    return command, *args
                else:
                    return command
            except KeyError:
                print("Entered command is invalid or not permitted.")
            except ValueError:
                print(f"Command {command} doesn't accept such arguments.")
                log.debug(
                    f"Command {command} doesn't accept arguments: "
                    f"{', '.join(*args)}. Filter = {permitted_answers[command]}")
            text = input(common_prompt)

    def _finish_app(self):
        raise ExitApplication

    def _ensure_env(self):
        first_prompt = (
            "No needed data in .env file. If you want to fill it manually in console, enter 'yes'."
            "Else enter 'no' and create or fill it in opened File Manager. Then enter 'check'. See '.env.example'.")
        common_prompt = "Do you want to fill env file manually in console?"
        handlers = {
            "n": utils.open_folder,
            "open": utils.open_folder,
            "exit": self._finish_app
        }
        while True:
            load_environment()
            missing_fields = get_missing_fields()
            if missing_fields:
                command = self._wait_for_command(
                    first_prompt=first_prompt, common_prompt=common_prompt,
                    menu_commands=False, open_available=True, yes_available=True,
                    no_available=True, check_available=True
                )
                if command == "y":
                    self._request_env_variables(missing_fields)
                    log.info("All entered environment variables saved.")
                    return
                if not command == "check":
                    handlers[command]()

    def _request_env_variables(self, variables: list[str]):
        result = {}
        for var in variables:
            result[var] = input(f"Enter {var}: ")
        update_env(result)

    def _resolve_checkpoints(self):
        try:
            self.state.read_checkpoint_files()
        except Exception:
            log.error("Unexpected error while looking for previous results of application work.")
            log.debug("Unexpected error info:\n", exc_info=True)
        if self.state.checkpoint_vacancies_not_saved_list:
            self.state.save_analysed_data()
        if self.state.has_unresolved_checkpoints():
            first_prompt = (
                f"You have unprocessed data from the past 30 days. "
                f"Enter 'yes' if you want to process it."
            )
            command = self._wait_for_command(
                first_prompt=first_prompt, menu_commands=False,
                yes_available=True, no_available=True
            )
            handlers = {
                "exit": self._finish_app
            }

            if command == "y":
                if self.state.checkpoint_vacancies_not_parsed_list:
                    self._parse(CommandArgs(use_checkpoint=True))
                if self.state.checkpoint_vacancies_not_analyzed_list:
                    self._analyze(CommandArgs(use_checkpoint=True))
                if self.state.checkpoint_vacancies_not_saved_list:
                    self.state.save_analysed_data()
            elif command == "n":
                return
            else:
                handlers[command]()

    def _ensure_candidate_info(self):
        file_path = paths.CANDIDATE_INFO_DIR / self.config.candidate_info_file_name
        if not self.config.candidate_info_file_name or not file_path.exists():
            first_prompt = (
                f"Candidate info not found. Create txt file with info about yourself in "
                f"{paths.CANDIDATE_INFO_DIR} folder and enter its name here. Open File Manager?"
            )
            common_prompt = "Do you want to open folder in File Manager."
            command = self._wait_for_command(
                first_prompt=first_prompt, common_prompt=common_prompt,
                menu_commands=False, yes_available=True,
                no_available=True, open_available=True
            )
            if command in ["y", "open"]:
                utils.open_folder(paths.CANDIDATE_INFO_DIR)
            if command == "exit":
                self._finish_app()

            while True:
                file_name = input("Enter file name: ")
                file_path = paths.CANDIDATE_INFO_DIR / file_name
                about_me = ""
                try:
                    about_me = utils.read_candidate_info(file_path)
                except FileNotFoundError:
                    print(f"There is no file with path '{file_path}'.")
                except ValueError:
                    print("This file is empty. Fill it with info about yourself.")

                if about_me:
                    self.about_me = about_me
                    save_config(self.config)
                    return

                common_prompt = "Do you want to open folder in File Manager again?"
                command = self._wait_for_command(
                    common_prompt=common_prompt, menu_commands=False,
                    yes_available=True, no_available=True, open_available=True
                )
                if command in ["y", "open"]:
                    utils.open_folder(paths.CANDIDATE_INFO_DIR)
                if command == "exit":
                    self._finish_app()
        else:
            while True:
                about_me = ""
                try:
                    about_me = utils.read_candidate_info(file_path)
                except ValueError:
                    print(f"File '{file_path}' is empty. Fill it with info about yourself.")

                if about_me:
                    self.about_me = about_me
                    save_config(self.config)
                    return

                common_prompt = "Do you want to open folder in File Manager?"
                command = self._wait_for_command(
                    common_prompt=common_prompt, menu_commands=False,
                    yes_available=True, no_available=True, open_available=True
                )
                if command in ["y", "open"]:
                    utils.open_folder(paths.CANDIDATE_INFO_DIR)
                if command == "exit":
                    self._finish_app()
