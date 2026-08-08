import logging
import traceback

from jobhunter.application.errors import ExitApplication
from jobhunter.cli.arguments import get_args
from jobhunter.main import main
from jobhunter.logger import setup_logger
from jobhunter.utils.error_handler import save_exception_to_file

log = logging.getLogger(__name__)


def run():
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


if __name__ == '__main__':
    run()
