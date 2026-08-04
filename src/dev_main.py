from flask import Flask, jsonify, request
import telebot
from telebot.types import Update

import sheets
from config import BOT_TOKEN, CRON_SECRET, PORT, WEBHOOK_SECRET, WEBHOOK_URL
from dev_booking_persistence import append_consultation_request
from dev_user_persistence import (
    get_user_language as dev_get_user_language,
    set_user_language as dev_set_user_language,
)

# Patch only the DEV runtime. Production entrypoint remains unchanged.
sheets.get_user_language = dev_get_user_language
sheets.set_user_language = dev_set_user_language
sheets.append_booking_request = append_consultation_request

import handlers  # noqa: E402
import booking  # noqa: E402
from postcare import send_due_postcare  # noqa: E402
from recall import send_due_recalls  # noqa: E402
from reminders import send_due_reminders  # noqa: E402

handlers.get_user_language = dev_get_user_language
booking.append_booking_request = append_consultation_request


def _strict_set_user_language(*args, **kwargs):
    success, error = dev_set_user_language(*args, **kwargs)
    if not success:
        raise RuntimeError(error or "Language was not saved")
    return True, None


handlers.set_user_language = _strict_set_user_language

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
handlers.register_handlers(bot)

app = Flask(__name__)


@app.route("/", methods=["GET"])
def health_check():
    return "Dental Care Assistant DEV is running 🦷🧪", 200


@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
def telegram_webhook():
    if request.headers.get("content-type") != "application/json":
        return "Unsupported Media Type", 415

    try:
        json_string = request.get_data().decode("utf-8")
        update = Update.de_json(json_string)

        if update is None:
            return "Bad Request", 400

        bot.process_new_updates([update])
        return "OK", 200
    except Exception as error:
        print(
            f"DEV webhook processing failed: {type(error).__name__}: {error}",
            flush=True,
        )
        return "Internal Server Error", 500


@app.route(f"/cron/{CRON_SECRET}", methods=["GET", "POST"])
def run_cron_tasks():
    if not CRON_SECRET:
        return jsonify({"ok": False, "error": "CRON_SECRET is empty"}), 500

    reminders_sent = send_due_reminders(bot)
    postcare_sent = send_due_postcare(bot)
    recalls_sent = send_due_recalls(bot)

    result = {
        "ok": True,
        "reminders_sent": reminders_sent,
        "postcare_sent": postcare_sent,
        "recalls_sent": recalls_sent,
    }
    print(f"DEV cron endpoint executed: {result}", flush=True)
    return jsonify(result), 200


def setup_webhook():
    if not WEBHOOK_URL:
        print("WEBHOOK_URL is empty. Webhook was not set.", flush=True)
        return

    if not WEBHOOK_SECRET:
        print("WEBHOOK_SECRET is empty. Webhook was not set.", flush=True)
        return

    webhook_url = f"{WEBHOOK_URL}/webhook/{WEBHOOK_SECRET}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    print("DEV webhook configured successfully.", flush=True)


if __name__ == "__main__":
    print("Dental Care Assistant DEV server is starting...", flush=True)
    setup_webhook()
    app.run(host="0.0.0.0", port=PORT)
