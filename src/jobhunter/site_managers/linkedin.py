import logging
import os
import re
from dataclasses import replace

from playwright.sync_api import BrowserContext

from jobhunter.config import Config
from jobhunter.email_reader import get_linkedin_pin
from jobhunter.environment import ENV_KEYS
from jobhunter.site_managers.base_site_manager import BaseSiteManager, SiteVacancyData

log = logging.getLogger(__name__)


class LinkedinManager(BaseSiteManager):
    REQUIRES_BROWSER = True
    SITE_NAME = "linkedin"
    JOB_ID_REGEXP = re.compile(r"jobs/view/(\d+)/")

    def __init__(
            self, context: BrowserContext, context_file_loaded: bool, config: Config):
        self.url = "https://www.linkedin.com/jobs/"
        self.context = context
        self.is_context_loaded = context_file_loaded
        self.config = config

        self.vacancy_page = self.context.new_page()
        self.page = self.context.new_page()

        self._open_and_login()
        self._configure_state()

        # login page
        self.login_input = self.page.locator("#session_key")
        self.password_input = self.page.locator("#session_password")
        self.login_button = self.page.get_by_role("button", name="Войти")
        self.pin_input = self.page.locator("#input__email_verification_pin")
        self.submit_pin_button = self.page.locator("#email-pin-submit-button")

        # filters
        self.filter_searchbox = self.page.get_by_role(role="textbox", name="Title, skill or Company")
        self.location_searchbox = self.page.get_by_role(role="textbox", name="City, state, or zip code")
        self.all_filters_button = self.page.get_by_role(role="button", name="All filters")

        self.filter_dialog = self.page.get_by_role("dialog", name="All filters")
        self.sort_by_filters = self.filter_dialog.get_by_role(
            "group", name="Sort by filter").locator("label")
        self.job_type_filters = self.filter_dialog.get_by_role(
            "group", name="Job type filter").locator("label")
        self.remote_filters = self.filter_dialog.get_by_role(
            "group", name="Remote filter").locator("label")
        self.job_function_filters = self.filter_dialog.get_by_role(
            "group", name="Job function filter").locator("label")
        self.show_results_button = self.filter_dialog.get_by_role(
            "button", name="Apply")

        # job list
        self.next_button = self.page.locator(
            "div.scaffold-layout__list").get_by_role("button", name="Next")
        self.job_links = self.page.locator(
            "div.scaffold-layout__list").locator("a[href*='jobs/view/']")

        # job data
        self.company_name_locator = self.vacancy_page.locator(
            'div[aria-label*="Company,"] a').first
        self.vacancy_locator = self.vacancy_page.locator(
            '//button[@aria-label="More options"]/following::p').first
        self.description_locator = self.vacancy_page.get_by_text(
            "About the job").locator("xpath=/following::p").first

    def _open_and_login(self):
        linkedin_login = os.getenv(ENV_KEYS.EMAIL_LINKEDIN.value)
        linkedin_password = os.getenv(ENV_KEYS.PASS_LINKEDIN.value)
        gmail = os.getenv(ENV_KEYS.gmail.value)
        gmail_app_password = os.getenv(ENV_KEYS.gmail_app_pass.value)

        self.page.goto(self.url)

        try:
            if self.is_context_loaded:
                self.filter_searchbox.wait_for(state="visible")
                return
            else:
                self.login_input.wait_for(state="visible")
        except TimeoutError:
            if self.is_context_loaded and not self.login_input.is_visible():
                raise RuntimeError("Linkedin page has not loaded.")

        self.login_input.fill(linkedin_login)
        self.password_input.fill(linkedin_password)
        self.login_button.click()

        pin = get_linkedin_pin(gmail, gmail_app_password)

        self.pin_input.fill(pin)
        self.submit_pin_button.click()

    def _configure_state(self):
        main_filter = self.config.sites.linkedin.qa_filter
        filters = self.config.sites.linkedin.other_qa_filters

        self.filter_searchbox.fill(main_filter)
        self.location_searchbox.fill(filters.location)
        self.location_searchbox.press("Enter")

        self.all_filters_button.click()

        self.sort_by_filters.filter(has_text=filters.sort_by).check()
        self.job_type_filters.filter(has_text=filters.job_type).check()
        self.remote_filters.filter(has_text=filters.work_place).check()
        for item_name in filters.job_function:
            self.job_function_filters.filter(has_text=item_name).check()

        self.show_results_button.click()

    def get_job_list(self) -> list[SiteVacancyData]:
        links = set()
        old = []

        def get_links() -> list[str]:
            return self.job_links.evaluate_all("(els) => els.map(e => e.href)")

        def scroll_list():
            log.debug("Scrolling job list.")
            self.job_links.first.hover()
            for i in range(20):
                self.page.mouse.wheel(0, 500)
                self.page.wait_for_timeout(200)

        def wait_for_list_update(previous_data: list) -> bool:
            log.debug("Waiting for job list to update...")
            retries = 5
            while retries > 0:
                scroll_list()
                if not previous_data == get_links():
                    break
                retries -= 1
                log.debug("Job list has not loaded. Retrying.")
            else:
                log.debug(f"Job list has not loaded in {retries} retries.")
                return False
            return True

        log.info("Getting job list...")
        while True:
            try:
                if wait_for_list_update(old):
                    old = get_links()
                    links.update(old)
                if not self.next_button.is_visible():
                    break
                log.debug("Opening next page.")
                self.next_button.click()
            finally:
                pass

        return [self._convert_link_to_vacancy_data(link) for link in links]

    def _fill_vacancy_data(self, vacancy_data: SiteVacancyData):
        if not vacancy_data.vacancy_link.strip():
            error = "Vacancy link is empty."
            log.error(error)
            raise ValueError(error)
        self.vacancy_page.goto(vacancy_data.vacancy_link)

        #todo: if vacancy is not available or closed -> raise
        vacancy_name = self.vacancy_locator.text_content().strip()
        if not vacancy_name:
            error = "Vacancy name is empty."
            log.error(error)
            raise ValueError(error)
        company_name = self.company_name_locator.text_content().strip()
        if not company_name:
            error = "Company name is empty."
            log.error(error)
            raise ValueError(error)
        company_link = self.company_name_locator.get_attribute("href").strip()
        if not company_link:
            error = "Company link is empty."
            log.error(error)
            raise ValueError(error)

        texts_to_delete = ["About the job\n", '\n… more']
        vacancy_description = self.description_locator.inner_text().strip()
        if any(text in vacancy_description for text in texts_to_delete):
            error = "No vacancy description found."
            log.error(error)
            raise ValueError(error)
        vacancy_description = (
            vacancy_description.replace("About the job\n", "")
            .replace('\n… more', "")
        )
        if not vacancy_description:
            error = "Vacancy description is empty."
            log.error(error)
            raise ValueError(error)

        vacancy_data.vacancy_name = vacancy_name
        vacancy_data.company_name = company_name
        vacancy_data.company_link = company_link
        vacancy_data.vacancy_description = vacancy_description

    def collect_vacancies_data(
            self, vacancy_data_list: list[SiteVacancyData]
    ) -> list[SiteVacancyData]:
        links = map(
            lambda vacancy_data: vacancy_data.vacancy_link,
            vacancy_data_list
        )
        log.info("Collecting vacancies data from site...")
        log.debug(
            f"%i vacancies links to collect data from:\n%s",
            len(vacancy_data_list), "\n".join(links)
        )
        self.vacancy_page.bring_to_front()

        vacancies = []
        for i, vacancy in enumerate(vacancy_data_list):
            log.info(f"{i}/{len(vacancy_data_list)} Collecting data from {vacancy.vacancy_link}")
            vacancy_copy = replace(vacancy)
            try:
                vacancies.append(self._fill_vacancy_data(vacancy_copy))
            except TimeoutError:
                raise RuntimeError("Linkedin page has not loaded.")
        return vacancies
