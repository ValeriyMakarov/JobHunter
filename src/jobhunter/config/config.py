from types import UnionType, NoneType
from typing import Any, get_args

import yaml
from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from jobhunter.paths import CONFIG_PATH, CONFIG_EXAMPLE_PATH
from .models import Config


def load_config() -> Config:
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)
    return Config(**config)


def safe_load_config() -> Config | None:
    try:
        return load_config()
    except Exception:
        return None


def save_config(config: Config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as file:
        yaml.safe_dump(
            config.model_dump(),
            file,
            allow_unicode=True,
            sort_keys=False
        )


def _generate_yaml(model: type[BaseModel], indent: int = 0):
    def is_model(_type: Any) -> bool:
        return isinstance(_type, type) and issubclass(_type, BaseModel)

    def convert_to_yaml_list(lst: list):
        lines = []
        prefix = " " * (indent + 2)

        for item in lst:
            lines.append(f"{prefix}- {item}")

        return lines

    lines = []
    prefix = " " * indent

    for name, field in model.model_fields.items():
        if field.description:
            lines.append(
                f"{prefix}# {field.description}"
            )

        annotation = field.annotation
        if isinstance(annotation, UnionType):
            types = [_type for _type in get_args(annotation) if is_model(_type)]
            if types:
                annotation = types[0]
            else:
                annotation = next(
                    _type
                    for _type in get_args(annotation)
                    if not issubclass(_type, NoneType)
                )

        if is_model(annotation):
            lines.append(f"{prefix}{name}:")
            lines.extend(
                _generate_yaml(annotation, indent + 2)
            )
        else:
            if not field.default == PydanticUndefined:
                value = field.default
            elif field.default_factory:
                value = field.default_factory()
            else:
                value = ""

            if isinstance(value, list):
                value = convert_to_yaml_list(value)
                lines.append(f"{prefix}{name}:")
                lines.extend(value)
            else:
                lines.append(f"{prefix}{name}: {value}")

    return lines


def create_config_example():
    example = _generate_yaml(Config)
    CONFIG_EXAMPLE_PATH.write_text("\n".join(example), encoding="utf-8")
