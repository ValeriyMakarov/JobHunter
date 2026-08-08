import logging
import re
from typing import overload, Literal

log = logging.getLogger(__name__)


@overload
def wait_for_command(
        available_commands: list[str], available_sites: list[str],
        menu_commands_available: Literal[True] = True,
        first_prompt: str = None, common_prompt: str = "",
        yes_available: bool = False,
        no_available: bool = False, check_available: bool = False,
        open_available: bool = False, hint: bool = True
) -> tuple[str, list[str]] | str:
    ...


@overload
def wait_for_command(
        menu_commands_available: Literal[False],
        first_prompt: str = None, common_prompt: str = "",
        available_commands: list[str] = None, available_sites: list[str] = None,
        yes_available: bool = False,
        no_available: bool = False, check_available: bool = False,
        open_available: bool = False, hint: bool = True
) -> tuple[str, list[str]] | str:
    ...


def wait_for_command(
        menu_commands_available: bool = True,
        available_commands: list[str] = None, available_sites: list[str] = None,
        first_prompt: str = None, common_prompt: str = "",
        yes_available: bool = False,
        no_available: bool = False, check_available: bool = False,
        open_available: bool = False, hint: bool = True
) -> tuple[str, list[str]] | str:
    exit_regexp = {
        "exit": re.compile(r"^\s*exit\s*$", re.IGNORECASE),
    }
    commands_regexps = {
        "help": re.compile(
            fr"^\s*help(?:\s+(?:{'|'.join(available_commands)}))*\s*$",
            re.IGNORECASE),
        "process": re.compile(
            fr"^\s*process(?:\s+(?:{'|'.join(available_sites)}))*\s*$",
            re.IGNORECASE),
        "run": re.compile(
            fr"^\s*run(?:\s+(?:{'|'.join(available_sites)}))*\s*$",
            re.IGNORECASE),
        "parse": re.compile(
            fr"^\s*parse(?:\s+(?:{'|'.join(available_sites)}))*\s*$",
            re.IGNORECASE),
        "analyze": re.compile(r"^\s*analyze\s*$", re.IGNORECASE),
        "settings": re.compile(r"^\s*settings\s*$", re.IGNORECASE)
    } if menu_commands_available else {}
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
    if menu_commands_available:
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
