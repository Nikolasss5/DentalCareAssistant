import hashlib
from datetime import datetime

import gspread
import pytz
from oauth2client.service_account import ServiceAccountCredentials

from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_ID, TIMEZONE

USERS_SHEET_NAME = "users"
REQUIRED_HEADERS = {
    "user_id",
    "telegram_chat_id",
    "telegram_username",
    "first_name",
    "last_name",
    "language",
    "phone",
    "first_seen_at",
    "last_seen_at",
    "status",
    "source",
    "notes",
}
SUPPORTED_LANGUAGES = {"uk", "ru"}

_language_cache = {}


def _now_string():
    timezone = pytz.timezone(TIMEZONE)
    return datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S")


def _client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        GOOGLE_CREDENTIALS_FILE,
        scope,
    )
    return gspread.authorize(credentials)


def _worksheet():
    if not GOOGLE_SHEET_ID:
        raise RuntimeError("GOOGLE_SHEET_ID is missing")

    spreadsheet = _client().open_by_key(GOOGLE_SHEET_ID)
    worksheet = spreadsheet.worksheet(USERS_SHEET_NAME)
    headers = worksheet.row_values(1)
    missing = sorted(REQUIRED_HEADERS.difference(headers))

    if missing:
        raise RuntimeError(
            "TEST users schema is missing required columns: " + ", ".join(missing)
        )

    return worksheet, headers


def _user_id(chat_id):
    digest = hashlib.sha256(str(chat_id).encode("utf-8")).hexdigest()[:8].upper()
    date_part = datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y%m%d")
    return f"USR-{date_part}-{digest}"


def get_user_language(patient_chat_id):
    chat_id = str(patient_chat_id).strip()

    if chat_id in _language_cache:
        return _language_cache[chat_id], None

    try:
        worksheet, _ = _worksheet()
        records = worksheet.get_all_records()

        for record in records:
            record_chat_id = str(record.get("telegram_chat_id", "")).strip()
            if record_chat_id != chat_id:
                continue

            language = str(record.get("language", "")).strip().lower()
            if language not in SUPPORTED_LANGUAGES:
                return None, None

            _language_cache[chat_id] = language
            return language, None

        return None, None
    except Exception as error:
        print(
            "DEV get_user_language failed: "
            f"{type(error).__name__}: {error}",
            flush=True,
        )
        return None, str(error)


def set_user_language(patient_chat_id, language, telegram_username=""):
    chat_id = str(patient_chat_id).strip()
    language = str(language).strip().lower()
    username = str(telegram_username or "").strip()

    if language not in SUPPORTED_LANGUAGES:
        return False, "Unsupported language"

    try:
        worksheet, headers = _worksheet()
        records = worksheet.get_all_records()
        now = _now_string()

        for row_number, record in enumerate(records, start=2):
            record_chat_id = str(record.get("telegram_chat_id", "")).strip()
            if record_chat_id != chat_id:
                continue

            updates = {
                "telegram_username": username,
                "language": language,
                "last_seen_at": now,
                "status": "active",
                "source": "telegram_bot",
            }
            for field_name, value in updates.items():
                column_number = headers.index(field_name) + 1
                worksheet.update_cell(row_number, column_number, value)

            _language_cache[chat_id] = language
            return True, None

        values = {
            "user_id": _user_id(chat_id),
            "telegram_chat_id": chat_id,
            "telegram_username": username,
            "first_name": "",
            "last_name": "",
            "language": language,
            "phone": "",
            "first_seen_at": now,
            "last_seen_at": now,
            "status": "active",
            "source": "telegram_bot",
            "notes": "DEV test user",
        }
        worksheet.append_row(
            [values.get(header, "") for header in headers],
            value_input_option="USER_ENTERED",
        )

        _language_cache[chat_id] = language
        return True, None
    except Exception as error:
        print(
            "DEV set_user_language failed: "
            f"{type(error).__name__}: {error}",
            flush=True,
        )
        return False, str(error)
