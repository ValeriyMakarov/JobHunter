import logging
import re
from abc import ABC, abstractmethod
from typing import ClassVar

from jobhunter.site_managers.entities import SiteVacancyData

log = logging.getLogger(__name__)


class BaseSiteManager(ABC):
    REQUIRES_BROWSER: ClassVar[bool] = False
    SITE_NAME: ClassVar[str] = None
    JOB_ID_REGEXP: ClassVar[str] = None

    @abstractmethod
    def get_job_list(self) -> list[SiteVacancyData]:
        ...

    @abstractmethod
    def collect_vacancies_data(
            self, vacancy_data_list: list[SiteVacancyData]
    ) -> list[SiteVacancyData]:
        ...

    def _convert_link_to_vacancy_data(self, link: str) -> SiteVacancyData:
        res = re.search(self.JOB_ID_REGEXP, link)
        vacancy_id = f"{self.SITE_NAME}{res[1]}" if res else None
        if not vacancy_id:
            log.error("Could not find vacancy id.")
        return SiteVacancyData(vacancy_link=link, vacancy_id=vacancy_id)
