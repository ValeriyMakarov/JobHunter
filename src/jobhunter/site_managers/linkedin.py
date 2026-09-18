import logging
import os
import re
from dataclasses import replace
from typing import Callable

from time import time
from playwright.sync_api import BrowserContext, TimeoutError, Locator, Frame

from jobhunter.checkpoint import checkpoint_manager, CheckpointFolderNames
from jobhunter.config.config import Config
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

        # login page
        self.login_input = self.page.locator("#session_key")
        self.password_input = self.page.locator("#session_password")
        self.login_button = self.page.get_by_role("button", name="Войти")
        self.pin_input = self.page.locator("#input__email_verification_pin")
        self.submit_pin_button = self.page.locator("#email-pin-submit-button")

        # filters
        self.filter_searchbox = self.page.get_by_role(role="textbox", name="Title, skill or Company")
        self.location_searchbox = self.page.get_by_role(role="textbox", name="City, state, or zip code")

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

        self._load_login_data()
        self._open_and_login()
        self._configure_state()

    @staticmethod
    def _get_filter_dialog(frame: Frame):
        return frame.get_by_role("dialog", name="All filters")

    @property
    def all_filters_button_factory(self):
        def get_locator(frame: Frame):
            return frame.locator(
                "#search-reusables__filters-bar"
            ).get_by_role(role="button", name="All filters")
        return get_locator

    @property
    def sort_by_filters_factory(self):
        def get_locator(frame: Frame):
            return self._get_filter_dialog(frame).get_by_role(
            "group", name="Sort by filter"
            ).locator("label")
        return get_locator

    @property
    def job_type_filters_factory(self):
        def get_locator(frame: Frame):
            return self._get_filter_dialog(frame).get_by_role(
            "group", name="Job type filter"
            ).locator("label")
        return get_locator

    @property
    def remote_filters_factory(self):
        def get_locator(frame: Frame):
            return self._get_filter_dialog(frame).get_by_role(
            "group", name="Remote filter"
            ).locator("label")
        return get_locator

    @property
    def job_function_filters_factory(self):
        def get_locator(frame: Frame):
            return self._get_filter_dialog(frame).get_by_role(
            "group", name="Job function filter"
            ).locator("label")
        return get_locator

    @property
    def show_results_button_factory(self):
        def get_locator(frame: Frame):
            return self._get_filter_dialog(frame).get_by_role(
            "button", name="Apply"
            )
        return get_locator

    def _load_login_data(self):
        self.linkedin_login = os.getenv(ENV_KEYS.EMAIL_LINKEDIN.key)
        self.linkedin_password = os.getenv(ENV_KEYS.PASS_LINKEDIN.key)
        self.gmail = os.getenv(ENV_KEYS.gmail.key)
        self.gmail_app_password = os.getenv(ENV_KEYS.gmail_app_pass.key)

    def _find_element_in_frames(
        self, locator_factory: Callable[[Frame],Locator],
        wait_locator_seconds: int = 30
    ) -> Locator:
        """
        Looks for locator in all Iframes on the page and returns its object for the frame containing it.

        :param locator_factory: Callable object for building locator.
        Must take Frame as only argument and return Locator.
        :type locator_factory: Callable[[Frame],Locator]
        :param wait_locator_seconds: Time to wait locator in seconds.
        Default - 30.

        :returns: Locator of the frame it has been found in.

        :raises TimeoutError: if non found.
        """
        deadline = time() + wait_locator_seconds
        while deadline > time():
            for frame in self.page.frames:
                locator = locator_factory(frame)
                if locator.count() > 0:
                    return locator
            self.page.wait_for_timeout(1000)
        raise TimeoutError(
            f"Locator {locator_factory(self.page.main_frame)} is not found in iframes."
        )

    def _open_and_login(self):
        def needs_pin(wait_seconds: int = 30):
            deadline = time() + wait_seconds
            while deadline > time():
                if self.pin_input.is_visible():
                    return True
                elif self.filter_searchbox.is_visible():
                    return False
                self.page.wait_for_timeout(1000)
            raise TimeoutError("Neither PIN page nor Main page are loaded.")

        log.info("Trying to open main Linkedin page...")
        self.page.goto(self.url)

        try:
            if self.is_context_loaded:
                self.filter_searchbox.wait_for(state="visible")
                log.debug("Page loaded. User logged in with loaded browser context.")
                return
            else:
                self.login_input.wait_for(state="visible")
        except TimeoutError:
            if self.is_context_loaded and not self.login_input.is_visible():
                log.error("Unable to load page.")
                raise RuntimeError("Linkedin page has not loaded.")
        except Exception:
            log.error("Unexpected error while logining to Linkedin.")
            log.debug("Unexpected error info: ", exc_info=True)
            raise

        self.login_input.fill(self.linkedin_login)
        self.password_input.fill(self.linkedin_password)
        self.login_button.click()

        if needs_pin():
            pin = get_linkedin_pin(self.gmail, self.gmail_app_password)

            self.pin_input.fill(pin)
            self.submit_pin_button.click()

    def _configure_state(self):
        main_filter = self.config.sites.linkedin.qa_filter
        filters = self.config.sites.linkedin.other_qa_filters

        log.info("Configuring Linkedin filters.")
        self.filter_searchbox.fill(main_filter)
        self.location_searchbox.fill(filters.location)
        self.location_searchbox.press("Enter")

        self._find_element_in_frames(self.all_filters_button_factory).click()

        self._find_element_in_frames(
            self.sort_by_filters_factory
        ).filter(has_text=filters.sort_by).check()
        self._find_element_in_frames(
            self.job_type_filters_factory
        ).filter(has_text=filters.job_type).check()
        self._find_element_in_frames(
            self.remote_filters_factory
        ).filter(has_text=filters.work_place).check()
        for item_name in filters.job_function:
            self._find_element_in_frames(
                self.job_function_filters_factory
            ).filter(has_text=item_name).check()

        self._find_element_in_frames(self.show_results_button_factory).click()

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

        vacancy_data_list = [self._convert_link_to_vacancy_data(link) for link in links]

        for vacancy_data in vacancy_data_list:
            checkpoint_manager.make_checkpoint(
                vacancy_data, CheckpointFolderNames.COLLECTED
            )
        return vacancy_data_list

    def _fill_vacancy_data(self, vacancy_data: SiteVacancyData):
        def get_text(locator: Locator, wait_locator_seconds: int = 2):
            deadline = time() + wait_locator_seconds
            while deadline > time():
                text = locator.inner_text()
                if text != "":
                    return text
                self.page.wait_for_timeout(10)
            raise TimeoutError(f"Text not found for {locator}.")

        if not vacancy_data.vacancy_link.strip():
            error = "Vacancy link is empty."
            log.error(error)
            raise ValueError(error)
        self.vacancy_page.goto(vacancy_data.vacancy_link)
        self.vacancy_locator.wait_for(state="visible")

        #todo: if vacancy is not available or closed -> raise
        vacancy_name = get_text(self.vacancy_locator).strip()
        if not vacancy_name:
            error = "Vacancy name is empty."
            log.error(error)
            raise ValueError(error)
        company_name = get_text(self.company_name_locator).strip()
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
        vacancy_description = get_text(self.description_locator).strip()
        # if any(text in vacancy_description for text in texts_to_delete):
        #     error = "No vacancy description found."
        #     log.error(error)
        #     raise ValueError(error)
        vacancy_description = (
            vacancy_description.removeprefix("About the job\n")
            .removesuffix('\n… more')
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
            log.info(f"{i+1}/{len(vacancy_data_list)} Collecting data from {vacancy.vacancy_link}")
            vacancy_copy = replace(vacancy)
            try:
                self._fill_vacancy_data(vacancy_copy)
                vacancies.append(vacancy_copy)
                checkpoint_manager.make_checkpoint(
                    vacancy_copy, CheckpointFolderNames.PARSED
                )
                log.debug(f"Data {i+1}/{len(vacancy_data_list)} collected.")
            except TimeoutError:
                raise RuntimeError("Linkedin page has not loaded.")
        return vacancies
