from html import escape

from config import ADMIN_CHAT_ID, CLINIC_NAME
from keyboards import main_menu_keyboard
from texts import (
    start_text,
    contact_text,
    AFTERCARE_TEXT,
    ASK_QUESTION_TEXT,
    QUESTION_SENT_TEXT,
    UNKNOWN_TEXT,
)
from booking import (
    start_booking,
    start_booking_from_callback,
    handle_booking_message,
    handle_booking_callback,
)
from appointments import show_my_appointment
from reminders import send_due_reminders, handle_reminder_callback
from postcare import send_due_postcare, handle_postcare_callback
from recall import send_due_recalls, handle_recall_callback
from admin_appointments import (
    handle_admin_appointment_callback,
    handle_admin_appointment_message,
)
from visit_management import show_today_appointments, handle_visit_callback

question_sessions = set()


def register_handlers(bot):
    @bot.message_handler(commands=["start"])
    def handle_start(message):
        bot.send_message(
            message.chat.id,
            start_text(),
            reply_markup=main_menu_keyboard(),
        )

    @bot.message_handler(commands=["admin"])
    def handle_admin(message):
        bot.send_message(
            message.chat.id,
            (
                "Ваш Telegram chat_id:\n\n"
                f"<code>{message.chat.id}</code>\n\n"
                "Скопіюйте це число і вставте в .env у поле ADMIN_CHAT_ID."
            ),
        )

    @bot.message_handler(commands=["run_reminders"])
    def handle_run_reminders(message):
        if ADMIN_CHAT_ID and message.chat.id != ADMIN_CHAT_ID:
            bot.send_message(message.chat.id, "⛔ Ця команда доступна тільки адміну.")
            return

        sent_count = send_due_reminders(bot)

        bot.send_message(
            message.chat.id,
            f"✅ Перевірка нагадувань завершена.\n\nНадіслано: {sent_count}",
        )

    @bot.message_handler(commands=["run_postcare"])
    def handle_run_postcare(message):
        if ADMIN_CHAT_ID and message.chat.id != ADMIN_CHAT_ID:
            bot.send_message(message.chat.id, "⛔ Ця команда доступна тільки адміну.")
            return

        sent_count = send_due_postcare(bot)

        bot.send_message(
            message.chat.id,
            f"✅ Перевірка post-care завершена.\n\nНадіслано: {sent_count}",
        )

    @bot.message_handler(commands=["run_recalls"])
    def handle_run_recalls(message):
        if ADMIN_CHAT_ID and message.chat.id != ADMIN_CHAT_ID:
            bot.send_message(message.chat.id, "⛔ Ця команда доступна тільки адміну.")
            return

        sent_count = send_due_recalls(bot)

        bot.send_message(
            message.chat.id,
            f"✅ Перевірка recall-нагадувань завершена.\n\nНадіслано: {sent_count}",
        )

    @bot.message_handler(commands=["admin_today"])
    def handle_admin_today(message):
        show_today_appointments(bot, message)

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call):
        if handle_booking_callback(bot, call):
            return

        if handle_reminder_callback(bot, call):
            return

        if handle_postcare_callback(bot, call):
            return

        if handle_recall_callback(bot, call):
            return

        if handle_admin_appointment_callback(bot, call):
            return

        if handle_visit_callback(bot, call):
            return

        data = call.data
        chat_id = call.message.chat.id

        if data == "menu_booking":
            start_booking_from_callback(bot, call)
            return

        if data == "menu_my_appointment":
            bot.answer_callback_query(call.id)
            show_my_appointment(bot, call.message)
            return

        if data == "menu_question":
            bot.answer_callback_query(call.id)
            question_sessions.add(chat_id)
            bot.send_message(
                chat_id,
                ASK_QUESTION_TEXT,
            )
            return

        if data == "menu_aftercare":
            bot.answer_callback_query(call.id)
            bot.send_message(
                chat_id,
                AFTERCARE_TEXT,
                reply_markup=main_menu_keyboard(),
            )
            return

        if data == "menu_contacts":
            bot.answer_callback_query(call.id)
            bot.send_message(
                chat_id,
                contact_text(),
                reply_markup=main_menu_keyboard(),
            )
            return

        bot.answer_callback_query(call.id)

    @bot.message_handler(content_types=["text"])
    def handle_text(message):
        chat_id = message.chat.id
        text = (message.text or "").strip()

        if handle_admin_appointment_message(bot, message):
            return

        if handle_booking_message(bot, message):
            return

        if chat_id in question_sessions:
            question_sessions.remove(chat_id)
            _forward_question_to_admin(bot, message)
            return

        if text in {"📅 Записатися", "🗓 Записатися на прийом"}:
            start_booking(bot, message)
            return

        if text == "📋 Мій запис":
            show_my_appointment(bot, message)
            return

        if text in {"💬 Поставити питання", "❓ Поставити питання"}:
            question_sessions.add(chat_id)
            bot.send_message(
                chat_id,
                ASK_QUESTION_TEXT,
            )
            return

        if text in {"🦷 Рекомендації", "🦷 Рекомендації після процедури"}:
            bot.send_message(
                chat_id,
                AFTERCARE_TEXT,
                reply_markup=main_menu_keyboard(),
            )
            return

        if text in {"📞 Контакти клініки", "📍 Контакти клініки"}:
            bot.send_message(
                chat_id,
                contact_text(),
                reply_markup=main_menu_keyboard(),
            )
            return

        bot.send_message(
            chat_id,
            UNKNOWN_TEXT,
            reply_markup=main_menu_keyboard(),
        )


def _forward_question_to_admin(bot, message):
    chat_id = message.chat.id
    question = (message.text or "").strip()

    bot.send_message(
        chat_id,
        QUESTION_SENT_TEXT,
        reply_markup=main_menu_keyboard(),
    )

    if not ADMIN_CHAT_ID:
        print(
            "ADMIN_CHAT_ID is not configured. Patient question was not sent to admin."
        )
        print(question)
        return

    username = getattr(message.from_user, "username", None)
    username_text = f"@{username}" if username else "—"

    admin_text = (
        f"❓ <b>Нове питання пацієнта</b>\n\n"
        f"Клініка: {escape(CLINIC_NAME)}\n"
        f"Telegram: {escape(username_text)}\n"
        f"chat_id: <code>{chat_id}</code>\n\n"
        f"Питання:\n{escape(question)}"
    )

    bot.send_message(ADMIN_CHAT_ID, admin_text)
