import logging
from typing import overload, Literal, Union

from playwright.sync_api import sync_playwright

from jobhunter import paths
from jobhunter.config import Config
from jobhunter.site_managers.linkedin import LinkedinManager

log = logging.getLogger(__name__)

manager_types_union = Union[LinkedinManager]
manager_names_union = Union[Literal["linkedin"]]


class SiteManagerProvider:
    def __init__(self, config: Config):
        self.config = config
        self._playwright = sync_playwright().start()
        self._browser = None
        self._context = None
        self._is_context_loaded = False

        self._site_managers_cls = {
            "linkedin": LinkedinManager,
            # "headhunter": HeadHunterManager
        }
        self._site_managers = {}

    def _create_browser(self):
        self._browser = self._playwright.chromium.launch(headless=False)

    def _create_context(self):
        if not self._browser:
            self._create_browser()
        try:
            self._context = self._browser.new_context(
                storage_state=paths.CONTEXT_JSON_PATH)
            self._is_context_loaded = True
        except Exception:
            log.error("Unexpected error while loading browser context.")
            log.debug("Unexpected error info:\n", exc_info=True)
            self._context = self._browser.new_context()
            self._is_context_loaded = False

    @overload
    def get_manager(self, name: Literal["linkedin"]) -> LinkedinManager:
        ...

    @overload
    def get_manager(self, name: str) -> manager_types_union:
        ...

    def get_manager(self, name: str):

        manager = self._site_managers.get(name)
        if not manager:
            manager_cls = self._site_managers_cls[name]

            if manager_cls.REQUIRES_BROWSER:
                if not self._context:
                    self._create_context()
                manager = manager_cls(self._context, self._is_context_loaded, self.config)
            else:
                manager = manager_cls(self.config)
            self._site_managers[name] = manager

        return manager

    def _save_context(self):
        try:
            paths.CONTEXT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._context.storage_state(path=paths.CONTEXT_JSON_PATH)
        except Exception:
            log.error("Unexpected error while saving browser context.")
            log.debug("Unexpected error info:\n", exc_info=True)

    def close(self):
        self._save_context()

        self._context.close()
        self._browser.close()
        self._playwright.stop()

#
# class SiteManagerProvider:
#     def __enter__(self):
#         return self._site_manager
#
#     def __init__(self, name: manager_names_union, config: dict):
#         self.config = config
#         self.playwright = sync_playwright().start()
#         self.browser = self.playwright.chromium.launch(headless=False)
#         self.site_managers = {}
#         self._register_site_managers()
#         self._site_manager = self._get_manager(name)
#
#     def _register_site_managers(self):
#         self.site_managers["linkedin"] = LinkedinManager
#         # self.site_managers["headhunter"] = HeadHunterManager
#
#     @overload
#     def _get_manager(self, name: Literal["linkedin"]) -> LinkedinManager:
#         ...
#
#     @overload
#     def _get_manager(self, name: str) -> manager_types_union:
#         ...
#
#     def _get_manager(self, name: str):
#         manager_cls = self.site_managers[name]
#         if manager_cls.REQUIRES_BROWSER:
#             return manager_cls(self.browser, self.config)
#         else:
#             return manager_cls(self.config)
#
#     def close(self):
#         if self.browser:
#             self.browser.close()
#         self.playwright.stop()
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self._site_manager.__exit__(exc_type, exc_val, exc_tb)
#         self.close()
