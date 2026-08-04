from dataclasses import dataclass
from enum import Enum


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
    vacancy_id: str
    application_date: str = None
    vacancy_name: str = None
    company_name: str = None
    vacancy_link: str = None
    company_link: str = None
    job_description: str = None
    status: str = None
    finish_date: str = None
    cv_name: str = None


@dataclass
class CompanyBlacklistRow:
    company_name: str
    company_link: str = None
    reason: str = None


@dataclass
class DeniedVacancyRow:
    vacancy_id: str
    vacancy_name: str = None
    vacancy_link: str = None
    company_name: str = None
    company_link: str = None

