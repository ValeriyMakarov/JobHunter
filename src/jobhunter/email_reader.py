import imaplib
import logging
import re
from datetime import datetime, timedelta
from email import message_from_bytes
from email.utils import parsedate_to_datetime
from time import sleep, monotonic

log = logging.getLogger(__name__)


def parse_pin(text: str) -> str | None:
    result = re.search(r"verification code (\d{6})", text)
    if result:
        return result[1]


def get_linkedin_pin(
        login: str, password: str, wait: int = 120, message_offset_time: int = 30
) -> str | None:
    delay = 5
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    today = datetime.now().astimezone()
    deadline = monotonic() + wait
    email_filter = f'unseen FROM :security-noreply@linkedin.com SINCE {today.strftime("%d-%b-%Y")}'

    log.debug(f"Waiting for email with PIN. Filter={email_filter}")

    try:
        mail.login(login, password)
        mail.select("INBOX")

        ids = []
        while monotonic() <= deadline:
            # Get email ids and check if new message came
            mail.noop()
            status, search_results = mail.search(
                None, email_filter
            )
            if status != 'OK':
                error_text = f"Unexpected result while reading emails list: {status=}"
                log.error(error_text)
                raise ValueError(error_text)
            new_ids_list = search_results[0].split()
            if not new_ids_list or ids and new_ids_list and new_ids_list[-1] == ids[-1]:
                sleep(delay)
                continue
            ids = new_ids_list

            # Get last message headers in text
            status, raw_msg_data = mail.fetch(ids[-1], "BODY.PEEK[HEADER]")
            if status != 'OK' or not raw_msg_data:
                error_text = f"Unexpected result while fetching email: {status}"
                log.error(error_text)
                raise ValueError(error_text)
            _, raw_msg = raw_msg_data[0]
            msg = message_from_bytes(raw_msg)

            # Check if last message income time is expected
            date = parsedate_to_datetime(msg["Date"]).astimezone()
            if date < today - timedelta(seconds=message_offset_time):
                sleep(delay)
                continue

            pin = parse_pin(msg["Subject"])
            if pin:
                return pin
            sleep(delay)
    finally:
        mail.logout()
