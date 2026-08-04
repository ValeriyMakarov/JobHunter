import traceback
from datetime import datetime
from pathlib import Path

from jobhunter import paths


def save_exception_to_file() -> Path:
    paths.ERRORS_DIR.mkdir(exist_ok=True)
    error_file = paths.ERRORS_DIR / (
        f"error_{datetime.now():%Y%b%d%H%M%S}.error.log"
    )

    with error_file.open("w", encoding="utf-8") as file:
        traceback.print_exc(file=file)

    return error_file
