import telebot

from config import BOT_TOKEN
from reminders import send_due_reminders
from postcare import send_due_postcare
from recall import send_due_recalls

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


def main():
    print("Cron tasks started...")

    reminders_sent = send_due_reminders(bot)
    print(f"Reminders sent: {reminders_sent}")

    postcare_sent = send_due_postcare(bot)
    print(f"Postcare sent: {postcare_sent}")

    recalls_sent = send_due_recalls(bot)
    print(f"Recalls sent: {recalls_sent}")

    print("Cron tasks finished.")


if __name__ == "__main__":
    main()
