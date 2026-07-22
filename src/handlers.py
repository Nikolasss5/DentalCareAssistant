import re
from html import escape

from config import ADMIN_CHAT_ID, CLINIC_NAME
from keyboards import main_menu_keyboard, admin_menu_keyboard
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
    handle_booking_contact,
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
from sheets import get_admin_stats

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
        chat_id = message.chat.id

        if _is_admin_chat(chat_id):
            bot.send_message(
                chat_id,
                (
                    "🦷 <b>Адмін-панель клініки</b>\n\n"
                    f"Ваш Telegram chat_id:\n<code>{chat_id}</code>\n\n"
                    "Оберіть потрібну дію нижче або скористайтесь командами:"
                ),
                reply_markup=admin_menu_keyboard(),
            )
            return

        bot.send_message(
            chat_id,
            (
                "Ваш Telegram chat_id:\n\n"
                f"<code>{chat_id}</code>\n\n"
                "Скопіюйте це число і вставте в .env у поле ADMIN_CHAT_ID."
            ),
        )

    @bot.message_handler(commands=["admin_help", "admin_menu"])
    def handle_admin_help(message):
        if not _is_admin_chat(message.chat.id):
            bot.send_message(message.chat.id, "⛔ Ця команда доступна тільки адміну.")
            return

        _send_admin_help(bot, message.chat.id)

    @bot.message_handler(commands=["admin_stats"])
    def handle_admin_stats(message):
        if not _is_admin_chat(message.chat.id):
            bot.send_message(message.chat.id, "⛔ Ця команда доступна тільки адміну.")
            return

        _send_admin_stats(bot, message.chat.id)

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

        if data == "admin_menu_today":
            bot.answer_callback_query(call.id)
            show_today_appointments(bot, call.message)
            return

        if data == "admin_menu_stats":
            bot.answer_callback_query(call.id)
            _send_admin_stats(bot, chat_id)
            return

        if data == "admin_menu_help":
            bot.answer_callback_query(call.id)
            _send_admin_help(bot, chat_id)
            return

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

    @bot.message_handler(content_types=["contact"])
    def handle_contact(message):
        if handle_booking_contact(bot, message):
            return

        bot.send_message(
            message.chat.id,
            "Дякуємо. Щоб записатися на прийом, скористайтесь меню нижче.",
            reply_markup=main_menu_keyboard(),
        )

    @bot.message_handler(content_types=["text"])
    def handle_text(message):
        chat_id = message.chat.id
        text = (message.text or "").strip()

        if _handle_admin_reply_to_patient(bot, message):
            return

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



def _handle_admin_reply_to_patient(bot, message):
    if not _is_admin_chat(message.chat.id):
        return False

    replied_message = getattr(message, "reply_to_message", None)
    if replied_message is None:
        return False

    replied_text = (getattr(replied_message, "text", None) or "").strip()
    if "Нове питання пацієнта" not in replied_text:
        return False

    match = re.search(r"chat_id:\\s*(\\d+)", replied_text)
    if not match:
        bot.send_message(
            message.chat.id,
            (
                "⚠️ Не вдалося визначити пацієнта.\n\n"
                "Відповідайте саме на повідомлення з питанням пацієнта."
            ),
        )
        return True

    reply_text = (message.text or "").strip()
    if not reply_text:
        bot.send_message(
            message.chat.id,
            "⚠️ Відповідь не може бути порожньою.",
        )
        return True

    patient_chat_id = int(match.group(1))

    try:
        bot.send_message(
            patient_chat_id,
            (
                "💬 <b>Відповідь клініки</b>\n\n"
                f"{escape(reply_text)}"
            ),
            reply_markup=main_menu_keyboard(),
        )
    except Exception as error:
        print(
            f"Failed to send admin reply to patient "
            f"{patient_chat_id}: {error}"
        )
        bot.send_message(
            message.chat.id,
            (
                "⚠️ Не вдалося надіслати відповідь пацієнту.\n\n"
                "Можливо, пацієнт заблокував бота "
                "або Telegram тимчасово недоступний."
            ),
        )
        return True

    bot.send_message(
        message.chat.id,
        "✅ Відповідь надіслано пацієнту.",
    )
    return True


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
        f"Питання:\n{escape(question)}\n\n"
        "↩️ <i>Щоб відповісти пацієнту, "
        "дайте відповідь на це повідомлення.</i>"
    )

    bot.send_message(ADMIN_CHAT_ID, admin_text)


def _is_admin_chat(chat_id):
    return bool(ADMIN_CHAT_ID) and chat_id == ADMIN_CHAT_ID


def _send_admin_help(bot, chat_id):
    text = (
        "ℹ️ <b>Команди адміна</b>\n\n"
        "/admin — відкрити адмін-панель\n"
        "/admin_today — записи на сьогодні\n"
        "/admin_stats — коротка статистика\n"
        "/run_reminders — вручну перевірити нагадування\n"
        "/run_postcare — вручну перевірити рекомендації після процедури\n"
        "/run_recalls — вручну перевірити recall-нагадування\n\n"
        "Щоб відповісти пацієнту, використайте функцію "
        "<b>Відповісти</b> на повідомленні з його питанням.\n\n"
        "У щоденній роботі найчастіше потрібні: <b>записи на сьогодні</b> "
        "та <b>статистика</b>."
    )

    bot.send_message(
        chat_id,
        text,
        reply_markup=admin_menu_keyboard(),
    )


def _send_admin_stats(bot, chat_id):
    stats, error = get_admin_stats()

    if error or not stats:
        bot.send_message(
            chat_id,
            (
                "⚠️ Не вдалося отримати статистику.\n\n"
                f"Причина: {escape(str(error))}"
            ),
            reply_markup=admin_menu_keyboard(),
        )
        return

    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"Дата: <b>{escape(str(stats.get('today', '')))}</b>\n\n"
        "<b>Сьогодні</b>\n"
        f"Заявок: <b>{stats.get('requests_today', 0)}</b>\n"
        f"Записів на сьогодні: <b>{stats.get('appointments_today', 0)}</b>\n"
        f"Активних записів: <b>{stats.get('active_today', 0)}</b>\n"
        f"Завершених візитів: <b>{stats.get('completed_today', 0)}</b>\n"
        f"No-show: <b>{stats.get('no_show_today', 0)}</b>\n\n"
        "<b>Заявки</b>\n"
        f"Всього: <b>{stats.get('booking_total', 0)}</b>\n"
        f"Нові: <b>{stats.get('booking_new', 0)}</b>\n"
        f"Підтверджено: <b>{stats.get('booking_confirmed', 0)}</b>\n"
        f"Відхилено: <b>{stats.get('booking_rejected', 0)}</b>\n\n"
        "<b>Записи</b>\n"
        f"Всього: <b>{stats.get('appointments_total', 0)}</b>\n"
        f"Підтверджені: <b>{stats.get('appointments_confirmed', 0)}</b>\n"
        f"Підтверджені пацієнтом: <b>{stats.get('appointments_confirmed_by_patient', 0)}</b>\n"
        f"Завершені: <b>{stats.get('appointments_completed', 0)}</b>\n"
        f"Перенесення: <b>{stats.get('appointments_reschedule_requested', 0)}</b>\n"
        f"Скасовані: <b>{stats.get('appointments_cancelled', 0)}</b>\n"
        f"No-show: <b>{stats.get('appointments_no_show', 0)}</b>\n\n"
        "<b>Автоматизація</b>\n"
        f"Post-care надіслано: <b>{stats.get('postcare_sent', 0)}</b>\n"
        f"Recall надіслано: <b>{stats.get('recall_sent', 0)}</b>"
    )

    bot.send_message(
        chat_id,
        text,
        reply_markup=admin_menu_keyboard(),
    )

