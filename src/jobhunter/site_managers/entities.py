from dataclasses import dataclass


@dataclass
class SiteVacancyData:
    vacancy_name: str = None
    vacancy_link: str = None
    company_name: str = None
    company_link: str = None
    vacancy_id: str = None
    vacancy_description: str = None
