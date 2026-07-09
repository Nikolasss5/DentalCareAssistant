from flask import Flask, request
import telebot
from telebot.types import Update

from config import BOT_TOKEN, PORT, WEBHOOK_SECRET, WEBHOOK_URL
from handlers import register_handlers

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

    bot.process_new_updates([update])

    return "OK", 200


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
