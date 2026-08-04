import logging
import math
import re
from abc import ABC, abstractmethod
from time import sleep, monotonic

from google import genai
from google.genai.errors import ClientError

from jobhunter.analizer.entities import AnalyzedDataInfo
from jobhunter.analizer.errors import DayQuotaExceededError, ModelUnavailableError, \
    ModelInvalidAnswerError
from jobhunter.environment import ENV_KEYS
from jobhunter.site_managers.base_site_manager import SiteVacancyData

log = logging.getLogger(__name__)


PYTHON_AQA_PROMPT = """
    Junior vacancy flags:
    - Execute predefined test cases
    - Maintain existing automated tests
    - Write simple automation scripts
    - Follow existing frameworks and processes
    - Work under guidance
    - Basic programming and testing knowledge
    - Limited ownership
    - Mostly feature-level testing tasks

    Middle vacancy flags:
    - Develop and maintain automated tests
    - Create test cases from requirements
    - Work independently on assigned features
    - Extend existing automation frameworks
    - UI/API/regression/integration testing
    - Debug test failures
    - Write reusable automation components
    - Work with CI/CD and version control
    - Participate in code reviews
    - Improve testing processes
    - Own testing for specific areas
    
    Senior vacancy flags:
    - Define automation strategy or testing approach
    - Design or significantly change framework architecture
    - Own automation infrastructure decisions
    - Lead QA initiatives
    - Mentor other engineers
    - Establish testing standards and processes
    - Drive quality improvements across teams
    - Make independent technical decisions with high impact
    - Own quality for complex systems/products
    - Coordinate work between teams

    Might be not Senior flags:
    - Focuses mainly on writing automated tests rather than defining automation approach
    - Requires only maintenance or extension of existing tests/framework without technical ownership
    - Does not mention responsibility for automation architecture or major technical decisions
    - No ownership beyond assigned features or individual tasks
    - No involvement in defining testing strategy, quality standards, or processes
    - No mentoring, technical leadership, or guidance of other engineers
    - No responsibility for complex systems, cross-team initiatives, or product-level quality
    
    Analise next vacancy text and tell:
    - If position is for QA
    Use: True, False
    - Determine the actual proficiency level required by vacancy based only on the responsibilities and requirements.
    Use Junior, Middle and Senior flags listed earlier. Ignore vacancy name, inflated titles and required years in the vacancy.
    Use: Junior, Middle, Senior 
    - Level of automation on this position in percents
    Use: 0-for only manual, 100-for automation only, -1 if unknown
    - If this is Python vacancy (it is required or 'will be a plus')
    Use: 1-for True, 0-if surly False, -1 if unknown 
    - How suitable I am for this position in percents
    Use: 0-if not suitable, 100-if fully suitable
    - Very short and unique summary, include main technologies and difference in required and my experience
    Format of summary:
        Role focuses on testing types or frameworks.
        Main technologies: several main technologies of the role.
        Missing: only difference in required and my experience and technologies (use short phrases or just list technologies).
    Use less than 100 words in one line, don't use line break symbols.
    Wright summary like data, not answer to me.
    
    Format for the answer:
        qa vacancy, proficiency level, automation level, pythonish vacancy, suitableness, description
    
    Example of the answer:
        qa=True, prof=Middle, auto=50, pythonish=-1, suitableness=100, description=...
    
    About me:
    {about_me}
    
    Vacancy name:
    {vacancy_name}
    
    Vacancy text:
    {vacancy_text}
"""


class VacancyAnalyzer(ABC):
    def __init__(self):
        self._client = genai.Client(api_key=ENV_KEYS.GEMINI_API_KEY.value)

        self._model = "gemini-3.1-flash-lite"
        self._RPM = 15
        self._RPD = 500

        self._min_response_delay = math.ceil(60 / self._RPM)
        self._last_response_time = 0

    def _wait_before_next_request(self, wait: int = 0):
        time_to_wait = wait if wait else self._min_response_delay - math.ceil(monotonic() - self._last_response_time)

        if time_to_wait <= 0:
            return
        if not wait:
            log.debug("Waiting before next model request: %ds.", time_to_wait)

        sleep(time_to_wait)

    def _get_response(self, prompt: str, wait: int = 180) -> str:
        def backoff():
            delay = self._min_response_delay
            while True:
                yield delay if delay < 60 else 60
                delay *= 2

        log.debug(f"Getting response from model={self._model}")

        self._wait_before_next_request()

        deadline = monotonic() + wait
        delay = backoff()
        regexp = re.compile(r"Quota exceeded.+limit: (\d+), model:")
        response_text = ""

        while monotonic() <= deadline:
            self._last_response_time = monotonic()
            next_delay = next(delay)
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=prompt
                )
                if response and response.text:
                    response_text = response.text
                    break
            except ClientError as e:
                limit = re.search(regexp, e.details)
                if e.status == "RESOURCE_EXHAUSTED" and limit:
                    if limit == self._RPD:
                        raise DayQuotaExceededError("Daily quota exceeded for this model.") from e
                    if limit == 0:
                        raise ModelUnavailableError("This model is unavailable for usage.") from e

            log.warning("Waiting before next model request: %ds.", next_delay)
            self._wait_before_next_request(next_delay)

        if not response_text.strip():
            raise ModelInvalidAnswerError("Model responded with invalid answer.")

        return response_text

    def analyze_all(
            self, vacancies_list: list[SiteVacancyData], prompt: str, about_me: str
    ) -> list[AnalyzedDataInfo]:
        result = []
        for index, vacancy in enumerate(vacancies_list):
            log.info(f"Analyzing vacancy data for id={vacancy.vacancy_id} ({index}/{len(vacancies_list)}).")
            data_info = AnalyzedDataInfo(vacancy.vacancy_id)
            try:
                is_suitable, description = self._analyze_vacancy(
                    system_prompt=prompt, about_me=about_me,
                    vacancy_text=vacancy.vacancy_description,
                    vacancy_name=vacancy.vacancy_name
                )
                data_info.is_suitable = is_suitable
                data_info.vacancy_description = description
            except DayQuotaExceededError as e:
                log.error("Model reached daily quota.")
                raise e
            except ModelInvalidAnswerError:
                pass
            else:
                result.append(data_info)
        return result

    @abstractmethod
    def _analyze_vacancy(
            self, system_prompt: str, about_me: str,
            vacancy_text: str, vacancy_name: str) -> tuple[bool, str]:
        pass


class PythonAQAVacancyAnalyzer(VacancyAnalyzer):
    def _analyze_vacancy(
            self, system_prompt: str, about_me: str,
            vacancy_text: str, vacancy_name: str) -> tuple[bool, str]:
        log.debug(
            "Vacancy name: %s\n" 
            "\tSystem prompt:\n\t%s\n"
            "\tVacancy text:\n\t%s\n"
            "\tAbout me:\n\t%s",
            vacancy_name, system_prompt, vacancy_text, about_me
        )
        prompt = system_prompt.format(
            about_me=about_me,
            vacancy_name=vacancy_name,
            vacancy_text=vacancy_text
        )
        expected_auto_level = 30
        expected_suitableness = 10
        expected_senior_suitableness = 50

        response_text = self._get_response(prompt)

        is_qa = None
        prof_level = None
        auto = None
        pythonish = None
        suitableness = None
        description = None

        result = re.search(r"qa=(True|False)", response_text)
        if result:
            is_qa = bool(result[1])
        result = re.search(r"prof=(Junior|Middle|Senior)", response_text)
        if result:
            prof_level = result[1]
        result = re.search(r"auto=(-?\d+)", response_text)
        if result:
            auto = int(result[1])
        result = re.search(r"pythonish=(-?\d+)", response_text)
        if result:
            pythonish = int(result[1])
        result = re.search(r"suitableness=(\d+)", response_text)
        if result:
            suitableness = int(result[1])
        result = re.search(r"description=(.+)", response_text)
        if result:
            description = result[1]

        data_part = (
            f"is qa vacancy={is_qa}, proficiency level={prof_level}, automation level={auto}%, "
            f"is python vacancy={bool(pythonish) if pythonish>0 else 'Unknown'}, "
            f"suitableness level={suitableness}%, {description=}"
        )
        if None in (is_qa, prof_level, auto, pythonish, suitableness, description):
            log.error(f"Failed to analyze vacancy: {vacancy_name=}")
            log.debug(f"Failed analysis data for {vacancy_name=}: {data_part}")
            raise ModelInvalidAnswerError("Model responded with invalid answer or format.")

        if not is_qa:
            log.debug(f"Vacancy {vacancy_name} is not for QA.")
            return False, description
        if not pythonish:
            log.debug(f"Vacancy is not for Pythonist.")
            return False, description
        if auto < expected_auto_level and not auto == -1:
            log.debug(f"Vacancy is not suitable for candidate. Automation level={auto}%")
            return False, description
        if (
            suitableness < expected_suitableness
            or suitableness < expected_senior_suitableness and prof_level == "Senior"
        ):
            log.debug(
                "Vacancy is not suitable for candidate. Suitableness level=%d%, proficiency level=%s",
                suitableness, prof_level
            )
            return False, description

        log.debug(f"Vacancy is suitable. Data: {data_part}")
        return True, description
