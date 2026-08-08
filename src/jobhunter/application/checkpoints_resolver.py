import logging

from jobhunter.app_state import AppState
from jobhunter.application import utils
from jobhunter.application.menu_commands import MenuCommands
from jobhunter.application.entities import CommandArgs
from jobhunter.cli.input import wait_for_command

log = logging.getLogger(__name__)


class CheckpointResolver:
    def __init__(self, state: AppState, menu_commands: MenuCommands):
        self._state = state
        self._commands = menu_commands

    def resolve(self):
        try:
            self._state.read_checkpoint_files()
        except Exception:
            log.error("Unexpected error while looking for previous results of application work.")
            log.debug("Unexpected error info:\n", exc_info=True)
        if self._state.checkpoint_vacancies_not_saved_list:
            self._state.save_analysed_data()
        if self._state.has_unresolved_checkpoints():
            first_prompt = (
                f"You have unprocessed data from the past 30 days. "
                f"Enter 'yes' if you want to process it."
            )
            command = wait_for_command(
                menu_commands_available=False, first_prompt=first_prompt,
                yes_available=True, no_available=True
            )
            handlers = {
                "exit": utils.finish_app
            }

            if command == "y":
                if self._state.checkpoint_vacancies_not_parsed_list:
                    self._commands.parse(CommandArgs(use_checkpoint=True))
                if self._state.checkpoint_vacancies_not_analyzed_list:
                    self._commands.analyze(CommandArgs(use_checkpoint=True))
                if self._state.checkpoint_vacancies_not_saved_list:
                    self._state.save_analysed_data()
            elif command == "n":
                return
            else:
                handlers[command]()
