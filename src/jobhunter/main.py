import logging
import traceback

from jobhunter.application.application import Application
from jobhunter.application.errors import ExitApplication
from cli import get_args
from logger import setup_logger
from jobhunter.utils.error_handler import save_exception_to_file

log = logging.getLogger(__name__)


def main():
    app = Application()
    app.run()


if __name__ == '__main__':
    try:
        args = get_args()
        setup_logger(
            logging_level=logging.DEBUG if args.debug else logging.INFO,
            console_logging_level=logging.DEBUG if args.console_debug else logging.INFO
        )
        main()
    except ExitApplication:
        log.info("Application finished.")
    except KeyboardInterrupt:
        log.info("Application stopped by user with ctrl C.")
    except Exception:
        try:
            error_file_path = save_exception_to_file()
            log.info(f"Application crashed. See details in {error_file_path}")
        except Exception:
            traceback.print_exc()
