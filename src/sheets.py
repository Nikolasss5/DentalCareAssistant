import os
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_ID

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


def _sheets_configured():
    return bool(GOOGLE_SHEET_ID) and os.path.exists(GOOGLE_CREDENTIALS_FILE)


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
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
