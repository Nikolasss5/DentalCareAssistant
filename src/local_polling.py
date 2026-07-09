import telebot

from config import BOT_TOKEN
from handlers import register_handlers

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

register_handlers(bot)


if __name__ == "__main__":
    print("Dental Care Assistant is running locally with polling...")

    bot.remove_webhook()

    bot.infinity_polling(skip_pending=True)
