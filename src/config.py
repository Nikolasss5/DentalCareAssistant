import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

ADMIN_CHAT_ID_RAW = os.getenv("ADMIN_CHAT_ID", "").strip()

CLINIC_NAME = os.getenv("CLINIC_NAME", "Dental Care Clinic").strip()
CLINIC_PHONE = os.getenv("CLINIC_PHONE", "+380 XX XXX XX XX").strip()
CLINIC_ADDRESS = os.getenv("CLINIC_ADDRESS", "Kyiv, Ukraine").strip()
CLINIC_WORKING_HOURS = os.getenv("CLINIC_WORKING_HOURS", "Mon-Fri 09:00-19:00").strip()
CLINIC_INSTAGRAM = os.getenv("CLINIC_INSTAGRAM", "").strip()
TIMEZONE = os.getenv("TIMEZONE", "Europe/Kyiv").strip()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip().rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
PORT_RAW = os.getenv("PORT", "10000").strip()


def _parse_port():
    try:
        return int(PORT_RAW)
    except ValueError:
        return 10000


PORT = _parse_port()

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "").strip()
GOOGLE_CREDENTIALS_FILE = os.getenv(
    "GOOGLE_CREDENTIALS_FILE", "google_credentials.json"
).strip()


def _parse_admin_chat_id():
    if not ADMIN_CHAT_ID_RAW:
        return None

    try:
        return int(ADMIN_CHAT_ID_RAW)
    except ValueError:
        return None


ADMIN_CHAT_ID = _parse_admin_chat_id()


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Add BOT_TOKEN to your .env file.")
