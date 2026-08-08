import logging
from inspect import cleandoc
from typing import Callable

from jobhunter.analizer.analyzers import PythonAQAVacancyAnalyzer, \
    PYTHON_AQA_PROMPT
from jobhunter.app_state import AppState
from jobhunter.application import utils
from jobhunter.application.entities import CommandArgs
from jobhunter.site_managers.base_site_manager import BaseSiteManager
from jobhunter.site_managers.site_manager_provider import SiteManagerProvider

log = logging.getLogger(__name__)


class MenuCommands:
    def __init__(
        self, available_sites: list[str], site_provider: SiteManagerProvider,
        state: AppState, about_me: str
    ):
        self._available_sites = available_sites
        self._site_provider = site_provider
        self._state = state
        self._about_me = about_me

        self._commands_handlers = {
            "exit": self.exit,
            "help": self.help,
            "process": self.process,
            "run": self.run,
            "collect": self.collect,
            "parse": self.parse,
            "analyze": self.analyze,
            "apply": self.apply,
            "settings": self.settings
        }
        self._available_commands = list(self._commands_handlers)

    @property
    def commands_handlers(self) -> dict[str, Callable]:
        return self._commands_handlers.copy()

    @property
    def available_commands(self) -> list[str]:
        return self._available_commands.copy()

    def collect(self, args: CommandArgs):
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
            self._state.current_vacancies_collected_extend(job_list)

    def parse(self, args: CommandArgs):
        """
        Parse data about jobs using previously collected job links from specified sites.
        If no sites are specified, jobs data will be collected from all available sites.
        """
        site_names = args.names if args.names else self._available_sites
        managers: list[BaseSiteManager] = [
            self._site_provider.get_manager(name) for name in site_names
        ]
        vacancy_list_to_use = (
            self._state.checkpoint_vacancies_not_parsed_list
            if args.use_checkpoint
            else self._state.current_vacancies_collected_list)

        for manager in managers:
            corresponding_vacancy_list = [
                vacancy_data
                for vacancy_data in vacancy_list_to_use
                if manager.SITE_NAME in vacancy_data.vacancy_link
            ]
            data_list = manager.collect_vacancies_data(corresponding_vacancy_list)
            if args.use_checkpoint:
                self._state.checkpoint_vacancies_not_analyzed_extend(data_list)
            else:
                self._state.current_vacancies_parsed_extend(data_list)

    def analyze(self, args: CommandArgs):
        """
        Analyze collected jobs data using Gemini neural network.
        """
        analyzer = PythonAQAVacancyAnalyzer()
        prompt = PYTHON_AQA_PROMPT
        parsed_list_to_use = (
            self._state.checkpoint_vacancies_not_analyzed_list
            if args.use_checkpoint
            else self._state.current_vacancies_parsed_list)

        analyzed_data_list = analyzer.analyze_all(
            parsed_list_to_use, prompt=prompt, about_me=self._about_me
        )
        if args.use_checkpoint:
            self._state.checkpoint_vacancies_not_saved_extend(analyzed_data_list)
        else:
            self._state.current_vacancies_analyzed_extend(analyzed_data_list)

    def apply(self, args: CommandArgs):
        """
        Not implemented.
        Open all suitable job links by one to apply.
        """
        print("This command is not implemented.")

    def settings(self, args: CommandArgs):
        """
        Not implemented.
        Change app settings.
        """
        print("This command is not implemented.")

    def run(self, args: CommandArgs):
        """
        Not implemented.
        Collect all jobs data from specified sites, analyze it and open all suitable jobs links by one to apply.
        If no sites are specified, jobs data will be collected from all available sites.
        """
        print("This command is not implemented.")

    def process(self, args: CommandArgs):
        """
        Collect all jobs data from specified sites and analyze it.
        If no sites are specified, jobs data will be collected from all available sites.
        """
        self.collect(args)
        self.parse(args)
        self.analyze(args)

    def help(self, args: CommandArgs):
        """
        Get info about available menu commands.
        """
        commands = args.names if args.names else self._available_commands
        for command_name in commands:
            if command_name not in self._available_commands:
                log.error(f"{command_name} is not available command.")
                return

        for command in commands:
            func = self.commands_handlers[command]
            doc = cleandoc(func.__doc__) if func.__doc__ else "No info."
            print(f"Command '{command}':\n{doc}", end="\n\n")

    def exit(self, *_):
        """
        Save all new application data to the file and quit.
        """
        self._state.save_analysed_data()
        self._site_provider.close()
        utils.finish_app()
