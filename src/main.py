from flask import Flask, request, jsonify
import telebot
from telebot.types import Update

from config import BOT_TOKEN, CRON_SECRET, PORT, WEBHOOK_SECRET, WEBHOOK_URL
from handlers import register_handlers
from reminders import send_due_reminders
from postcare import send_due_postcare
from recall import send_due_recalls

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
register_handlers(bot)

app = Flask(__name__)


@app.route("/", methods=["GET"])
def health_check():
    return "Dental Care Assistant is running 🦷", 200


@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
def telegram_webhook():
    if request.headers.get("content-type") != "application/json":
        return "Unsupported Media Type", 415

    json_string = request.get_data().decode("utf-8")
    update = Update.de_json(json_string)

    if update is None:
        return "Bad Request", 400

    bot.process_new_updates([update])

    return "OK", 200


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

    print(f"Cron endpoint executed: {result}")

    return jsonify(result), 200


def setup_webhook():
    if not WEBHOOK_URL:
        print("WEBHOOK_URL is empty. Webhook was not set.")
        return

    if not WEBHOOK_SECRET:
        print("WEBHOOK_SECRET is empty. Webhook was not set.")
        return

    webhook_url = f"{WEBHOOK_URL}/webhook/{WEBHOOK_SECRET}"

    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)

    print(f"Webhook set to: {webhook_url}")


if __name__ == "__main__":
    print("Dental Care Assistant webhook server is starting...")

    setup_webhook()

    app.run(
        host="0.0.0.0",
        port=PORT,
    )
