import json
import os
import uuid
from datetime import datetime

import gspread
import pytz

from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_ID, TIMEZONE

CONSULTATION_REQUESTS_SHEET_NAME = "consultation_requests"
CONSULTATION_REQUESTS_HEADERS = [
    "request_id",
    "created_at",
    "patient_id",
    "telegram_chat_id",
    "full_name",
    "phone",
    "telegram_username",
    "language",
    "service_code",
    "preferred_datetime_comment",
    "patient_comment",
    "status",
    "assigned_admin",
    "taken_in_work_at",
    "appointment_id",
    "source",
    "updated_at",
]


def _now_string():
    timezone = pytz.timezone(TIMEZONE)
    return datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S")


def _credentials_path():
    configured = str(GOOGLE_CREDENTIALS_FILE or "").strip()
    candidates = [
        configured,
        f"/etc/secrets/{os.path.basename(configured)}" if configured else "",
        "/etc/secrets/google_credentials.json",
        "google_credentials.json",
    ]

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate

    raise FileNotFoundError("Google credentials file was not found")


def _get_client():
    path = _credentials_path()
    with open(path, "r", encoding="utf-8") as credentials_file:
        credentials_info = json.load(credentials_file)
    return gspread.service_account_from_dict(credentials_info)


def _request_id():
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"REQ-{timestamp}-{suffix}"


def append_consultation_request(data):
    """Save one consultation request using the current Operations schema.

    Returns:
        tuple: (success, error_message, row_number)
    """
    if not GOOGLE_SHEET_ID:
        return False, "GOOGLE_SHEET_ID is empty", None

    try:
        print("DEV consultation persistence stage=open_spreadsheet", flush=True)
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        print("DEV consultation persistence stage=open_worksheet", flush=True)
        worksheet = spreadsheet.worksheet(CONSULTATION_REQUESTS_SHEET_NAME)
        headers = worksheet.row_values(1)

        if headers != CONSULTATION_REQUESTS_HEADERS:
            return (
                False,
                "consultation_requests headers do not match the expected DEV schema",
                None,
            )

        now = _now_string()
        row = [
            _request_id(),
            now,
            "",
            str(data.get("patient_chat_id", "")).strip(),
            str(data.get("patient_name", "")).strip(),
            str(data.get("phone", "")).strip(),
            str(data.get("telegram_username", "")).strip(),
            str(data.get("language", "")).strip(),
            str(data.get("procedure_key", "")).strip(),
            "",
            str(data.get("comment", "")).strip(),
            str(data.get("status", "new")).strip() or "new",
            "",
            "",
            "",
            "telegram_bot_dev",
            now,
        ]

        row_number = len(worksheet.get_all_values()) + 1
        print(
            f"DEV consultation persistence stage=append_row row={row_number}",
            flush=True,
        )
        worksheet.append_row(row, value_input_option="USER_ENTERED")

        print(
            f"DEV consultation persistence success row={row_number}",
            flush=True,
        )
        return True, None, row_number

    except Exception as error:
        print(
            "DEV consultation persistence failed: "
            f"{type(error).__name__}: {error!r}",
            flush=True,
        )
        return False, f"{type(error).__name__}: {error}", None
