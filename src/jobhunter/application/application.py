import logging

from jobhunter.app_state import AppState
from jobhunter.application import utils
from jobhunter.application.application_initializer import \
    ApplicationInitializer
from jobhunter.application.checkpoints_resolver import CheckpointResolver
from jobhunter.application.entities import CommandArgs
from jobhunter.application.menu_commands import MenuCommands
from jobhunter.cli.input import wait_for_command
from jobhunter.config.config import safe_load_config
from jobhunter.site_managers.site_manager_provider import SiteManagerProvider

log = logging.getLogger(__name__)


class Application:
    def __init__(self):
        self._commands: MenuCommands | None = None
        self.state: AppState | None = None
        self.config = safe_load_config()
        self.about_me = ""
        self._available_sites = []

        self._site_provider = SiteManagerProvider(self.config)

    def run(self):
        ApplicationInitializer.ensure_structure()
        ApplicationInitializer.ensure_env()

        if not self.config:
            self.config = ApplicationInitializer.ensure_config()
        self.state = AppState(self.config.application_data_file)
        self._available_sites = utils.get_available_sites(self.config)
        self.about_me = ApplicationInitializer.ensure_candidate_info(self.config)

        self._commands = MenuCommands(
            available_sites=self._available_sites,
            site_provider=self._site_provider,
            state=self.state,
            about_me=self.about_me
        )
        CheckpointResolver(self.state, self._commands).resolve()

        self._command_loop()

    def _command_loop(self):
        while True:
            command, *args = wait_for_command(
                available_commands=self._commands.available_commands,
                available_sites=self._available_sites
            )
            self._commands.commands_handlers[command](CommandArgs(names=args))
