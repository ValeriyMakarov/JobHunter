from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ApplicationColumnNames(Enum):
    APPLICATION_DATE = "Application date"
    VACANCY_NAME = "Vacancy name"
    COMPANY_NAME = "Company name"
    VACANCY_LINK = "Vacancy link"
    COMPANY_LINK = "Company link"
    JOB_DESCRIPTION = "Job description"
    VACANCY_ID = "Vacancy id"
    STATUS = "Status"
    FINISH_DATE = "Finish date"
    CV_NAME = "CV name"


class DeniedVacanciesColumnNames(Enum):
    VACANCY_ID = "Vacancy ID"
    VACANCY_NAME = "Vacancy name"
    VACANCY_LINK = "Vacancy link"
    COMPANY_NAME = "Company name"
    COMPANY_LINK = "Company link"


class CompaniesBlacklistColumnNames(Enum):
    COMPANY_NAME = "Company name"
    COMPANY_LINK = "Company link"
    REASON = "Reason"


class SheetNames(Enum):
    APPLICATIONS = "Applications", ApplicationColumnNames
    DENIED_VACANCIES = "Denied vacancies", DeniedVacanciesColumnNames
    COMPANIES_BLACKLIST = "Companies blacklist", CompaniesBlacklistColumnNames

    def __init__(self, sheet_name, columns_enum):
        self.sheet_name = sheet_name
        self.columns_enum = columns_enum


@dataclass
class ApplicationDataRow:
    _vacancy_id: str
    application_date: Optional[str] = None
    vacancy_name: Optional[str] = None
    company_name: Optional[str] = None
    vacancy_link: Optional[str] = None
    company_link: Optional[str] = None
    job_description: Optional[str] = None
    status: Optional[str] = None
    finish_date: Optional[str] = None
    cv_name: Optional[str] = None

    @property
    def vacancy_id(self):
        return self._vacancy_id

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, ApplicationDataRow):
            return NotImplemented
        return value.vacancy_id == self._vacancy_id

    def __hash__(self) -> int:
        return hash(self._vacancy_id)


@dataclass
class CompanyBlacklistRow:
    company_name: str
    company_link: Optional[str] = None
    reason: Optional[str] = None


@dataclass
class DeniedVacancyRow:
    _vacancy_id: str
    vacancy_name: Optional[str] = None
    vacancy_link: Optional[str] = None
    company_name: Optional[str] = None
    company_link: Optional[str] = None

    @property
    def vacancy_id(self):
        return self._vacancy_id

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, DeniedVacancyRow):
            return NotImplemented
        return value.vacancy_id == self._vacancy_id

    def __hash__(self) -> int:
        return hash(self._vacancy_id)