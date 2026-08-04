from dataclasses import dataclass


@dataclass
class CommandArgs:
    use_checkpoint: bool = False
    names: list[str] = None
