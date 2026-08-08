import logging
import pickle
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from jobhunter.analyzer.entities import AnalyzedDataInfo
from paths import SAVES_DIR
from jobhunter.site_managers.entities import SiteVacancyData

log = logging.getLogger(__name__)


class CheckpointFolderNames(Enum):
    COLLECTED = "collected"
    PARSED = "parsed"
    ANALYZED = "analyzed"


class CheckpointManager:
    DATE_FORMAT = "%Y%b%d%H%M%S%f"
    EXTENSION = ".pickle"

    def __init__(self):
        self._current_save_dir = None
        self._previous_save_dir = None

    def _create_current_session_dir(self):
        if not self._current_save_dir:
            date_formatted = self._make_name_from_date(datetime.now())
            self._current_save_dir = SAVES_DIR / date_formatted
            self._current_save_dir.mkdir(parents=True)

    def _make_name_from_date(self, date: datetime, add_extension: bool = False) -> str:
        date_formatted = date.strftime(self.DATE_FORMAT)
        return f"{date_formatted}{self.EXTENSION}" if add_extension else date_formatted

    def _make_date_from_name(self, name: str) -> datetime:
        date = datetime.strptime(name.removesuffix(self.EXTENSION), self.DATE_FORMAT)
        return date

    def make_checkpoint(
            self, obj: SiteVacancyData | AnalyzedDataInfo,
            folder: CheckpointFolderNames
    ):
        log.debug(f"Creating checkpoint in {folder.value} for {type(obj)}.")
        if not self._current_save_dir:
            self._create_current_session_dir()
        file_name = self._make_name_from_date(datetime.now(), add_extension=True)
        target_folder = self._current_save_dir / folder.value
        path = target_folder / file_name

        target_folder.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as file:
            pickle.dump(obj, file)
        log.debug(f"Checkpoint saved to {path}.")

    def load_previous_checkpoints(self) -> dict:
        def is_valid_name(name: str) -> bool:
            try:
                self._make_date_from_name(name)
            except Exception:
                return False
            return True

        def get_checkpoint_files(dir_path: Path) -> list[Path]:
            return [
                file
                for file in dir_path.iterdir()
                if file.is_file() and file.name.endswith(self.EXTENSION)
            ]

        def read_saved_data(path: Path):
            with path.open("rb") as file:
                return pickle.load(file)

        checkpoint_folders_names = [folder.value for folder in CheckpointFolderNames]

        def get_content(path: Path) -> dict:
            content = {name: [] for name in checkpoint_folders_names}

            folders = [
                file
                for file in path.iterdir()
                if file.is_dir() and file.name in checkpoint_folders_names
            ]
            for folder in folders:
                content[folder.name] = [
                    read_saved_data(file)
                    for file in get_checkpoint_files(folder)
                ]

            return content

        load_since_time = datetime.now() - timedelta(days=30)
        all_checkpoints = {name: [] for name in checkpoint_folders_names}

        checkpoint_folders_paths = [
            file
            for file in SAVES_DIR.iterdir()
            if (
                file.is_dir()
                and is_valid_name(file.name)
                and self._make_date_from_name(file.name) > load_since_time
            )
        ]
        if not checkpoint_folders_paths:
            log.debug("No checkpoints in save folder.")
            return all_checkpoints

        log.debug("Collecting checkpoints")
        checkpoint_folders_paths.sort(
            key=lambda path: self._make_date_from_name(path.name),
            reverse=True
        )
        for folder_path in checkpoint_folders_paths:
            content = get_content(folder_path)
            for folder_name in checkpoint_folders_names:
                data_list = content[folder_name]
                all_checkpoints[folder_name].extend(data_list)

        for folder_name in checkpoint_folders_names:
            unique_checkpoints = {}
            for item in all_checkpoints[folder_name]:
                if type(item) == SiteVacancyData:
                    item: SiteVacancyData
                    key = item.vacancy_id
                elif type(item) == AnalyzedDataInfo:
                    item: tuple[str, tuple[bool, str]]
                    key = item[0]
                else:
                    raise TypeError("Unexpected type of deserialized item.")
                unique_checkpoints.setdefault(key, item)
            all_checkpoints[folder_name] = list(unique_checkpoints.values())

        log.debug(f"Previous checkpoints successfully read. Data:\n{all_checkpoints}")
        return all_checkpoints


checkpoint_manager = CheckpointManager()
