from dataclasses import dataclass
from typing import Optional


@dataclass
class SiteVacancyData:
    vacancy_name: Optional[str] = None
    vacancy_link: Optional[str] = None
    company_name: Optional[str] = None
    company_link: Optional[str] = None
    vacancy_id: Optional[str] = None
    vacancy_description: Optional[str] = None
