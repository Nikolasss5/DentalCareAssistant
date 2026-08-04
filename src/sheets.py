import os
from datetime import datetime

import gspread
import pytz
from oauth2client.service_account import ServiceAccountCredentials

from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_ID, TIMEZONE

BOOKING_REQUESTS_SHEET_NAME = "booking_requests"

BOOKING_REQUESTS_HEADERS = [
    "created_at",
    "patient_chat_id",
    "telegram_username",
    "patient_name",
    "phone",
    "procedure_type",
    "comment",
    "status",
]

APPOINTMENTS_SHEET_NAME = "appointments"

APPOINTMENTS_HEADERS = [
    "patient_chat_id",
    "patient_name",
    "phone",
    "procedure_type",
    "appointment_date",
    "appointment_time",
    "status",
    "reminder_24h_sent",
    "reminder_2h_sent",
    "postcare_sent",
    "recall_sent",
    "created_at",
    "updated_at",
]

POSTCARE_SHEET_NAME = "postcare"

POSTCARE_HEADERS = [
    "procedure_type",
    "postcare_text",
    "checkin_after_hours",
    "recall_after_days",
]


USERS_SHEET_NAME = "users"

USERS_HEADERS = [
    "patient_chat_id",
    "telegram_username",
    "language",
    "created_at",
    "updated_at",
]

LANGUAGE_STATS_SHEET_NAME = "language_stats"

LANGUAGE_STATS_HEADERS = [
    "patient_chat_id",
    "language",
    "first_selected_at",
    "updated_at",
]

_user_language_cache = {}


def _sheets_configured():
    return bool(GOOGLE_SHEET_ID) and os.path.exists(GOOGLE_CREDENTIALS_FILE)


def _now_string():
    timezone = pytz.timezone(TIMEZONE)
    return datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S")


def _get_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        GOOGLE_CREDENTIALS_FILE,
        scope,
    )

    return gspread.authorize(credentials)


def _get_or_create_worksheet(spreadsheet, sheet_name, headers):
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=sheet_name,
            rows=1000,
            cols=len(headers),
        )
        worksheet.append_row(headers)

    existing_headers = worksheet.row_values(1)

    if existing_headers != headers:
        worksheet.clear()
        worksheet.append_row(headers)

    return worksheet


def get_user_language(patient_chat_id):
    """
    Returns saved interface language for a Telegram user.

    Returns:
        tuple: (language: str | None, error_message: str | None)
    """
    cache_key = str(patient_chat_id).strip()

    if cache_key in _user_language_cache:
        return _user_language_cache[cache_key], None

    if not _sheets_configured():
        return None, "Google Sheets is not configured yet."

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        worksheet = _get_or_create_worksheet(
            spreadsheet,
            USERS_SHEET_NAME,
            USERS_HEADERS,
        )

        records = worksheet.get_all_records()

        for record in records:
            record_chat_id = str(
                record.get("patient_chat_id", "")
            ).strip()

            if record_chat_id != cache_key:
                continue

            language = str(record.get("language", "")).strip().lower()
            if language not in {"uk", "ru"}:
                return None, None

            _user_language_cache[cache_key] = language
            return language, None

        return None, None

    except Exception as error:
        return None, str(error)


def set_user_language(patient_chat_id, language, telegram_username=""):
    """
    Creates or updates a Telegram user's interface language.

    Returns:
        tuple: (success: bool, error_message: str | None)
    """
    cache_key = str(patient_chat_id).strip()
    language = str(language).strip().lower()

    if language not in {"uk", "ru"}:
        return False, "Unsupported language."

    _user_language_cache[cache_key] = language

    if not _sheets_configured():
        return False, "Google Sheets is not configured yet."

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        worksheet = _get_or_create_worksheet(
            spreadsheet,
            USERS_SHEET_NAME,
            USERS_HEADERS,
        )

        headers = worksheet.row_values(1)
        records = worksheet.get_all_records()
        now = _now_string()

        _upsert_language_stat(
            spreadsheet=spreadsheet,
            patient_chat_id=cache_key,
            language=language,
            now=now,
        )

        for row_number, record in enumerate(records, start=2):
            record_chat_id = str(
                record.get("patient_chat_id", "")
            ).strip()

            if record_chat_id != cache_key:
                continue

            values = {
                "telegram_username": telegram_username,
                "language": language,
                "updated_at": now,
            }

            for field_name, value in values.items():
                if field_name not in headers:
                    continue
                column_number = headers.index(field_name) + 1
                worksheet.update_cell(row_number, column_number, value)

            return True, None

        worksheet.append_row(
            [
                cache_key,
                telegram_username,
                language,
                now,
                now,
            ],
            value_input_option="USER_ENTERED",
        )
        return True, None

    except Exception as error:
        return False, str(error)



def _upsert_language_stat(
    spreadsheet,
    patient_chat_id,
    language,
    now,
):
    """
    Stores one current language choice per unique Telegram user.
    This worksheet is intentionally separate from admin statistics.
    """
    worksheet = _get_or_create_worksheet(
        spreadsheet,
        LANGUAGE_STATS_SHEET_NAME,
        LANGUAGE_STATS_HEADERS,
    )

    headers = worksheet.row_values(1)
    records = worksheet.get_all_records()
    chat_id_value = str(patient_chat_id).strip()

    for row_number, record in enumerate(records, start=2):
        record_chat_id = str(
            record.get("patient_chat_id", "")
        ).strip()

        if record_chat_id != chat_id_value:
            continue

        values = {
            "language": language,
            "updated_at": now,
        }

        for field_name, value in values.items():
            if field_name not in headers:
                continue
            column_number = headers.index(field_name) + 1
            worksheet.update_cell(row_number, column_number, value)

        return

    worksheet.append_row(
        [
            chat_id_value,
            language,
            now,
            now,
        ],
        value_input_option="USER_ENTERED",
    )


def append_booking_request(data):
    """
    Saves booking request to Google Sheets.

    Returns:
        tuple: (success: bool, error_message: str | None, row_number: int | None)
    """
    if not _sheets_configured():
        return False, "Google Sheets is not configured yet.", None

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        worksheet = _get_or_create_worksheet(
            spreadsheet,
            BOOKING_REQUESTS_SHEET_NAME,
            BOOKING_REQUESTS_HEADERS,
        )

        row_number = len(worksheet.get_all_values()) + 1

        row = [
            _now_string(),
            data.get("patient_chat_id", ""),
            data.get("telegram_username", ""),
            data.get("patient_name", ""),
            data.get("phone", ""),
            data.get("procedure_type", ""),
            data.get("comment", ""),
            data.get("status", "new"),
        ]

        worksheet.append_row(row, value_input_option="USER_ENTERED")

        return True, None, row_number

    except Exception as error:
        return False, str(error), None


def get_latest_patient_appointment(patient_chat_id):
    """
    Finds latest confirmed appointment for patient by Telegram chat_id.

    Returns:
        tuple: (appointment: dict | None, error_message: str | None)
    """
    if not _sheets_configured():
        return None, "Google Sheets is not configured yet."

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        worksheet = _get_or_create_worksheet(
            spreadsheet,
            APPOINTMENTS_SHEET_NAME,
            APPOINTMENTS_HEADERS,
        )

        records = worksheet.get_all_records()

        patient_chat_id = str(patient_chat_id)

        active_statuses = {
            "confirmed",
            "confirmed_by_patient",
            "reschedule_requested",
        }

        for record in reversed(records):
            record_chat_id = str(record.get("patient_chat_id", "")).strip()
            status = str(record.get("status", "")).strip().lower()

            if record_chat_id == patient_chat_id and status in active_statuses:
                return record, None

        return None, None

    except Exception as error:
        return None, str(error)


def get_upcoming_confirmed_appointments():
    """
    Returns confirmed appointments with their Google Sheets row number.
    """
    if not _sheets_configured():
        return [], "Google Sheets is not configured yet."

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        worksheet = _get_or_create_worksheet(
            spreadsheet,
            APPOINTMENTS_SHEET_NAME,
            APPOINTMENTS_HEADERS,
        )

        records = worksheet.get_all_records()

        appointments = []

        for index, record in enumerate(records, start=2):
            status = str(record.get("status", "")).strip().lower()

            if status == "confirmed":
                record["_row_number"] = index
                appointments.append(record)

        return appointments, None

    except Exception as error:
        return [], str(error)


def update_appointment_field(row_number, field_name, value):
    """
    Updates one field in appointments sheet by row number and column name.
    """
    if not _sheets_configured():
        return False, "Google Sheets is not configured yet."

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        worksheet = _get_or_create_worksheet(
            spreadsheet,
            APPOINTMENTS_SHEET_NAME,
            APPOINTMENTS_HEADERS,
        )

        headers = worksheet.row_values(1)

        if field_name not in headers:
            return False, f"Column '{field_name}' not found."

        column_number = headers.index(field_name) + 1

        worksheet.update_cell(row_number, column_number, value)

        return True, None

    except Exception as error:
        return False, str(error)


def get_appointment_by_row(row_number):
    """
    Gets appointment from appointments sheet by row number.
    """
    if not _sheets_configured():
        return None, "Google Sheets is not configured yet."

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        worksheet = _get_or_create_worksheet(
            spreadsheet,
            APPOINTMENTS_SHEET_NAME,
            APPOINTMENTS_HEADERS,
        )

        headers = worksheet.row_values(1)
        row_values = worksheet.row_values(row_number)

        if not row_values:
            return None, "Appointment row is empty."

        appointment = {}

        for index, header in enumerate(headers):
            appointment[header] = row_values[index] if index < len(row_values) else ""

        appointment["_row_number"] = row_number

        return appointment, None

    except Exception as error:
        return None, str(error)


def get_completed_appointments_pending_postcare():
    """
    Returns completed appointments where postcare was not sent yet.
    """
    if not _sheets_configured():
        return [], "Google Sheets is not configured yet."

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        worksheet = _get_or_create_worksheet(
            spreadsheet,
            APPOINTMENTS_SHEET_NAME,
            APPOINTMENTS_HEADERS,
        )

        records = worksheet.get_all_records()

        appointments = []

        for index, record in enumerate(records, start=2):
            status = str(record.get("status", "")).strip().lower()
            postcare_sent = str(record.get("postcare_sent", "")).strip().lower()

            if status == "completed" and postcare_sent != "yes":
                record["_row_number"] = index
                appointments.append(record)

        return appointments, None

    except Exception as error:
        return [], str(error)


def get_postcare_rule_by_procedure(procedure_type):
    """
    Finds postcare rule by procedure_type.
    """
    if not _sheets_configured():
        return None, "Google Sheets is not configured yet."

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        worksheet = _get_or_create_worksheet(
            spreadsheet,
            POSTCARE_SHEET_NAME,
            POSTCARE_HEADERS,
        )

        records = worksheet.get_all_records()

        target_procedure = str(procedure_type).strip().lower()

        for record in records:
            current_procedure = str(record.get("procedure_type", "")).strip().lower()

            if current_procedure == target_procedure:
                return record, None

        return None, None

    except Exception as error:
        return None, str(error)


def get_completed_appointments_pending_recall():
    """
    Returns completed appointments where recall was not sent yet.
    """
    if not _sheets_configured():
        return [], "Google Sheets is not configured yet."

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        worksheet = _get_or_create_worksheet(
            spreadsheet,
            APPOINTMENTS_SHEET_NAME,
            APPOINTMENTS_HEADERS,
        )

        records = worksheet.get_all_records()

        appointments = []

        for index, record in enumerate(records, start=2):
            status = str(record.get("status", "")).strip().lower()
            recall_sent = str(record.get("recall_sent", "")).strip().lower()

            if status == "completed" and recall_sent != "yes":
                record["_row_number"] = index
                appointments.append(record)

        return appointments, None

    except Exception as error:
        return [], str(error)


def get_booking_request_by_row(row_number):
    """
    Gets booking request from booking_requests sheet by row number.
    """
    if not _sheets_configured():
        return None, "Google Sheets is not configured yet."

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        worksheet = _get_or_create_worksheet(
            spreadsheet,
            BOOKING_REQUESTS_SHEET_NAME,
            BOOKING_REQUESTS_HEADERS,
        )

        headers = worksheet.row_values(1)
        row_values = worksheet.row_values(row_number)

        if not row_values:
            return None, "Booking request row is empty."

        booking_request = {}

        for index, header in enumerate(headers):
            booking_request[header] = (
                row_values[index] if index < len(row_values) else ""
            )

        booking_request["_row_number"] = row_number

        return booking_request, None

    except Exception as error:
        return None, str(error)


def update_booking_request_status(row_number, status):
    """
    Updates status in booking_requests sheet.
    """
    if not _sheets_configured():
        return False, "Google Sheets is not configured yet."

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        worksheet = _get_or_create_worksheet(
            spreadsheet,
            BOOKING_REQUESTS_SHEET_NAME,
            BOOKING_REQUESTS_HEADERS,
        )

        headers = worksheet.row_values(1)

        if "status" not in headers:
            return False, "Column 'status' not found."

        column_number = headers.index("status") + 1

        worksheet.update_cell(row_number, column_number, status)

        return True, None

    except Exception as error:
        return False, str(error)


def append_appointment(data):
    """
    Creates confirmed appointment in appointments sheet.
    """
    if not _sheets_configured():
        return False, "Google Sheets is not configured yet."

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        worksheet = _get_or_create_worksheet(
            spreadsheet,
            APPOINTMENTS_SHEET_NAME,
            APPOINTMENTS_HEADERS,
        )

        now = _now_string()

        row = [
            data.get("patient_chat_id", ""),
            data.get("patient_name", ""),
            data.get("phone", ""),
            data.get("procedure_type", ""),
            data.get("appointment_date", ""),
            data.get("appointment_time", ""),
            data.get("status", "confirmed"),
            "",
            "",
            "",
            "",
            now,
            now,
        ]

        worksheet.append_row(row, value_input_option="USER_ENTERED")

        return True, None

    except Exception as error:
        return False, str(error)


def get_appointments_by_date(appointment_date):
    """
    Returns active appointments for selected date.
    """
    if not _sheets_configured():
        return [], "Google Sheets is not configured yet."

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        worksheet = _get_or_create_worksheet(
            spreadsheet,
            APPOINTMENTS_SHEET_NAME,
            APPOINTMENTS_HEADERS,
        )

        records = worksheet.get_all_records()

        active_statuses = {
            "confirmed",
            "confirmed_by_patient",
        }

        appointments = []

        for index, record in enumerate(records, start=2):
            record_date = str(record.get("appointment_date", "")).strip()
            status = str(record.get("status", "")).strip().lower()

            if record_date == appointment_date and status in active_statuses:
                record["_row_number"] = index
                appointments.append(record)

        return appointments, None

    except Exception as error:
        return [], str(error)


def get_admin_stats():
    """
    Returns simple admin statistics for demo and daily control.
    """
    if not _sheets_configured():
        return None, "Google Sheets is not configured yet."

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        booking_worksheet = _get_or_create_worksheet(
            spreadsheet,
            BOOKING_REQUESTS_SHEET_NAME,
            BOOKING_REQUESTS_HEADERS,
        )
        appointments_worksheet = _get_or_create_worksheet(
            spreadsheet,
            APPOINTMENTS_SHEET_NAME,
            APPOINTMENTS_HEADERS,
        )

        booking_records = booking_worksheet.get_all_records()
        appointment_records = appointments_worksheet.get_all_records()

        timezone = pytz.timezone(TIMEZONE)
        now = datetime.now(timezone)
        today_iso = now.strftime("%Y-%m-%d")
        today_dot = now.strftime("%d.%m.%Y")

        booking_status_counts = {}
        for record in booking_records:
            status = str(record.get("status", "")).strip().lower() or "empty"
            booking_status_counts[status] = booking_status_counts.get(status, 0) + 1

        appointment_status_counts = {}
        for record in appointment_records:
            status = str(record.get("status", "")).strip().lower() or "empty"
            appointment_status_counts[status] = appointment_status_counts.get(status, 0) + 1

        requests_today = sum(
            1
            for record in booking_records
            if _matches_today(record.get("created_at", ""), today_iso, today_dot)
        )

        appointments_today = [
            record
            for record in appointment_records
            if _matches_today(record.get("appointment_date", ""), today_iso, today_dot)
        ]

        active_statuses = {
            "confirmed",
            "confirmed_by_patient",
            "reschedule_requested",
        }

        active_today = sum(
            1
            for record in appointments_today
            if str(record.get("status", "")).strip().lower() in active_statuses
        )

        completed_today = sum(
            1
            for record in appointments_today
            if str(record.get("status", "")).strip().lower() == "completed"
        )

        no_show_today = sum(
            1
            for record in appointments_today
            if str(record.get("status", "")).strip().lower() == "no_show"
        )

        stats = {
            "today": today_iso,
            "requests_today": requests_today,
            "appointments_today": len(appointments_today),
            "active_today": active_today,
            "completed_today": completed_today,
            "no_show_today": no_show_today,
            "booking_total": len(booking_records),
            "booking_new": booking_status_counts.get("new", 0),
            "booking_confirmation_started": booking_status_counts.get(
                "confirmation_started", 0
            ),
            "booking_confirmed": booking_status_counts.get("confirmed", 0),
            "booking_rejected": booking_status_counts.get("rejected", 0),
            "appointments_total": len(appointment_records),
            "appointments_confirmed": appointment_status_counts.get("confirmed", 0),
            "appointments_confirmed_by_patient": appointment_status_counts.get(
                "confirmed_by_patient", 0
            ),
            "appointments_completed": appointment_status_counts.get("completed", 0),
            "appointments_reschedule_requested": appointment_status_counts.get(
                "reschedule_requested", 0
            ),
            "appointments_cancelled": appointment_status_counts.get("cancelled", 0),
            "appointments_no_show": appointment_status_counts.get("no_show", 0),
            "postcare_sent": sum(
                1
                for record in appointment_records
                if str(record.get("postcare_sent", "")).strip().lower() == "yes"
            ),
            "recall_sent": sum(
                1
                for record in appointment_records
                if str(record.get("recall_sent", "")).strip().lower() == "yes"
            ),
        }

        return stats, None

    except Exception as error:
        return None, str(error)


def _matches_today(value, today_iso, today_dot):
    raw_value = str(value).strip()

    if not raw_value:
        return False

    return raw_value.startswith(today_iso) or raw_value.startswith(today_dot)

