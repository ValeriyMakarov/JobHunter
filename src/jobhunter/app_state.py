import logging
from collections.abc import Iterable
from pathlib import Path
from types import UnionType
from typing import Collection, Any, Union, get_args

from jobhunter.analyzer.entities import AnalyzedDataInfo
from jobhunter.checkpoint import checkpoint_manager, CheckpointFolderNames
from jobhunter.excel.entities import ApplicationDataRow, DeniedVacancyRow

from jobhunter.excel.table_manager import TableManager
from jobhunter.site_managers.entities import SiteVacancyData

log = logging.getLogger(__name__)

VacanciesDataTypes = Union[SiteVacancyData, AnalyzedDataInfo]
VACANCIES_DATA_TYPES_NAMES = "SiteVacancyData, AnalyzedDataInfo"


class AppState:
    def __init__(self, save_file_path: Path):
        self._current_vacancies_collected: list[SiteVacancyData] = []
        self._current_vacancies_parsed: list[SiteVacancyData] = []
        self._current_vacancies_analyzed:  list[AnalyzedDataInfo] = []
        self._checkpoint_vacancies_not_parsed: list[SiteVacancyData] = []
        self._checkpoint_vacancies_not_analyzed: list[SiteVacancyData] = []
        self._checkpoint_vacancies_not_saved: list[SiteVacancyData] = []
        self._checkpoint_vacancies_not_saved_metadata: list[AnalyzedDataInfo] = []
        self._tables: TableManager = TableManager(save_file_path)

    @staticmethod
    def are_instances(
        iterable: Iterable, expected_type: type | UnionType | tuple[Any, ...]
    ):
        for i in iterable:
            if not isinstance(i, expected_type):
                return False
        return True

    @staticmethod
    def get_unique_types_str(iterable: Iterable):
        return ", ".join({type(i).__name__ for i in iterable})

    @staticmethod
    def _get_ids(lst: list[VacanciesDataTypes]) -> set[str]:
        if not lst:
            return set()
        if lst and AppState.are_instances(lst, (SiteVacancyData, AnalyzedDataInfo)):
            return {i.vacancy_id for i in lst}
        raise TypeError(
            f"Unexpected type in list: {AppState.get_unique_types_str(lst)}. "
            f"Have to be {VACANCIES_DATA_TYPES_NAMES}."
        )

    @staticmethod
    def _remove_ids_from_lists(
        ids: Collection[str],
        *lists: list[SiteVacancyData | AnalyzedDataInfo]
    ):
        for lst in lists:
            if not lst:
                continue
            if lst and AppState.are_instances(lst, (SiteVacancyData, AnalyzedDataInfo)):
                lst[:] = [item for item in lst if item.vacancy_id not in ids]
                continue
            raise TypeError(
                f"Unexpected type in list: {AppState.get_unique_types_str(lst)}. "
                f"Have to be {VACANCIES_DATA_TYPES_NAMES}."
            )

    @property
    def current_vacancies_collected_list(self):
        return self._current_vacancies_collected.copy()

    def current_vacancies_collected_extend(
            self, values: Collection[SiteVacancyData]
    ):
        ids = self._tables.get_all_ids() | self._get_ids(self._current_vacancies_collected)
        self._current_vacancies_collected.extend(
            item
            for item in values
            if item.vacancy_id not in ids
        )

    @property
    def current_vacancies_parsed_list(self):
        return self._current_vacancies_parsed.copy()

    def current_vacancies_parsed_extend(
            self, values: Collection[SiteVacancyData]
    ):
        parsed_ids = self._tables.get_all_ids() | self._get_ids(self._current_vacancies_parsed)
        self._current_vacancies_parsed.extend(
            item
            for item in values
            if item.vacancy_id not in parsed_ids
        )

        parsed_ids = self._get_ids(self._current_vacancies_parsed)
        self._remove_ids_from_lists(parsed_ids, self._current_vacancies_collected)

    @property
    def current_vacancies_analyzed_list(self):
        return self._current_vacancies_analyzed.copy()

    def current_vacancies_analyzed_extend(
            self, values: Collection[AnalyzedDataInfo]
    ):
        analyzed_ids = self._tables.get_all_ids() | self._get_ids(self._current_vacancies_analyzed)
        self._current_vacancies_analyzed.extend(
            item
            for item in values
            if item.vacancy_id not in analyzed_ids
        )

        analyzed_ids = self._get_ids(self._current_vacancies_analyzed)
        self._remove_ids_from_lists(
            analyzed_ids,
            self._current_vacancies_collected, self._current_vacancies_parsed
        )

    @property
    def checkpoint_vacancies_not_parsed_list(self):
        return self._checkpoint_vacancies_not_parsed.copy()

    def checkpoint_vacancies_not_parsed_extend(
            self, values: Collection[SiteVacancyData]
    ):
        ids = self._tables.get_all_ids() | self._get_ids(self._checkpoint_vacancies_not_parsed)
        self._checkpoint_vacancies_not_parsed.extend(
            item
            for item in values
            if item.vacancy_id not in ids
        )

    @property
    def checkpoint_vacancies_not_analyzed_list(self):
        return self._checkpoint_vacancies_not_analyzed.copy()

    def checkpoint_vacancies_not_analyzed_extend(
            self, values: Collection[SiteVacancyData]
    ):
        parsed_ids = self._tables.get_all_ids() | self._get_ids(self._checkpoint_vacancies_not_analyzed)
        self._checkpoint_vacancies_not_analyzed.extend(
            item
            for item in values
            if item.vacancy_id not in parsed_ids
        )

        parsed_ids = self._get_ids(self._checkpoint_vacancies_not_analyzed)
        self._remove_ids_from_lists(parsed_ids, self._checkpoint_vacancies_not_parsed)

    @property
    def checkpoint_vacancies_not_saved_list(self):
        return self._checkpoint_vacancies_not_saved.copy()

    def checkpoint_vacancies_not_saved_extend(
            self, values: Collection[AnalyzedDataInfo]
    ):
        analyzed_ids = self._tables.get_all_ids() | self._get_ids(self._checkpoint_vacancies_not_saved)
        self._checkpoint_vacancies_not_saved_metadata.extend(
            item
            for item in values
            if item.vacancy_id not in analyzed_ids
        )

        analyzed_ids = self._get_ids(self._checkpoint_vacancies_not_saved)
        self._remove_ids_from_lists(
            analyzed_ids,
            self._checkpoint_vacancies_not_parsed,
            self._checkpoint_vacancies_not_analyzed
        )

    def read_checkpoint_files(self):
        log.debug("Reading checkpoint data.")
        data = checkpoint_manager.load_previous_checkpoints()

        vacancies_collected: list[SiteVacancyData] = data[
            CheckpointFolderNames.COLLECTED.value].copy()
        vacancies_parsed: list[SiteVacancyData] = data[
            CheckpointFolderNames.PARSED.value].copy()
        vacancies_analyzed_metadata: list[AnalyzedDataInfo] = data[
            CheckpointFolderNames.ANALYZED.value].copy()
        vacancies_analyzed: list[SiteVacancyData]

        ids_to_remove = self._tables.get_all_ids()
        self._remove_ids_from_lists(
            ids_to_remove,
            vacancies_analyzed_metadata, vacancies_parsed, vacancies_collected
        )
        vacancies_analyzed = [
            vacancy
            for vacancy, analyzed_data in zip(
                sorted(vacancies_parsed,
                       key=lambda vac_data: vac_data.vacancy_id),
                sorted(vacancies_analyzed_metadata,
                       key=lambda anal_data: anal_data.vacancy_id)
            )
            if vacancy.vacancy_id == analyzed_data.vacancy_id
        ]

        ids_to_remove = {item.vacancy_id for item in vacancies_analyzed_metadata}
        self._remove_ids_from_lists(
            ids_to_remove,
            vacancies_parsed, vacancies_collected
        )

        ids_to_remove = {item.vacancy_id for item in vacancies_parsed}
        self._remove_ids_from_lists(ids_to_remove, vacancies_collected)

        self._checkpoint_vacancies_not_parsed = vacancies_collected
        self._checkpoint_vacancies_not_analyzed = vacancies_parsed
        self._checkpoint_vacancies_not_saved = vacancies_analyzed
        self._checkpoint_vacancies_not_saved_metadata = vacancies_analyzed_metadata

    def has_unresolved_checkpoints(self):
        return bool(
            self._checkpoint_vacancies_not_parsed
            or self._checkpoint_vacancies_not_analyzed
        )

    def save_analysed_data(self):
        log.info("Saving analyzed data...")

        applications_rows = []
        denied_vacancies_rows = []
        parsed_vacancies = {}
        all_analyzed_data_list = self._checkpoint_vacancies_not_saved_metadata + self._current_vacancies_analyzed

        for item in self._checkpoint_vacancies_not_saved + self._current_vacancies_parsed:
            parsed_vacancies.setdefault(item.vacancy_id, item)

        for i, analyzed_data in enumerate(all_analyzed_data_list):
            log.info(
                f"Saving {i+1}/{len(all_analyzed_data_list)}. "
                f"{'Suitable' if analyzed_data.is_suitable else 'Not suitable'}."
            )
            if analyzed_data.is_suitable:
                application_row = ApplicationDataRow(
                    vacancy_id=analyzed_data.vacancy_id,
                    job_description=analyzed_data.vacancy_description
                )
                corresponding_site_data: SiteVacancyData = parsed_vacancies[analyzed_data.vacancy_id]

                application_row.vacancy_name = corresponding_site_data.vacancy_name
                application_row.vacancy_link = corresponding_site_data.vacancy_link
                application_row.company_name = corresponding_site_data.company_name
                application_row.company_link = corresponding_site_data.company_link
                application_row.status = "Pending" # todo: when application will be through the app
                application_row.application_date = None # todo: when application will be through the app
                application_row.finish_date = None # todo: when application will be through the app
                application_row.cv_name = None # todo: when application will be through the app

                applications_rows.append(application_row)
            else:
                denied_row: DeniedVacancyRow = DeniedVacancyRow(
                    vacancy_id=analyzed_data.vacancy_id
                )
                corresponding_site_data: SiteVacancyData = parsed_vacancies[ # todo: bug at error_2026Sep18202347.error.log
                    analyzed_data.vacancy_id]

                denied_row.vacancy_name = corresponding_site_data.vacancy_name
                denied_row.vacancy_link = corresponding_site_data.vacancy_link
                denied_row.company_name = corresponding_site_data.company_name
                denied_row.company_link = corresponding_site_data.company_link

                denied_vacancies_rows.append(denied_row)

        self._tables.applications_table.update(applications_rows)
        self._tables.denied_vacancies_table.update(denied_vacancies_rows)
        self._remove_ids_from_lists(
            self._get_ids(all_analyzed_data_list),
            self._checkpoint_vacancies_not_saved,
            self._checkpoint_vacancies_not_analyzed,
            self._checkpoint_vacancies_not_parsed,
            self._current_vacancies_collected,
            self._current_vacancies_parsed,
            self._current_vacancies_analyzed
        )
        self._tables.save_data()
