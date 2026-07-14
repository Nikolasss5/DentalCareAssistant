from html import escape

from config import ADMIN_CHAT_ID
from keyboards import (
    services_keyboard,
    cancel_inline_keyboard,
    main_menu_keyboard,
    admin_booking_actions_keyboard,
)
from sheets import append_booking_request
from texts import (
    BOOKING_INTRO_TEXT,
    ASK_NAME_TEXT,
    ASK_PHONE_TEXT,
    ASK_COMMENT_TEXT,
    BOOKING_DONE_TEXT,
    BOOKING_CANCELLED_TEXT,
)

booking_sessions = {}


SERVICES = {
    "consultation": "Консультація",
    "cleaning": "Професійна чистка",
    "treatment": "Лікування зуба",
    "extraction": "Видалення зуба",
    "implant": "Імплантація",
    "orthodontics": "Ортодонтія / брекети",
    "other": "Інше питання",
}


def start_booking(bot, message):
    chat_id = message.chat.id

    booking_sessions[chat_id] = {
        "step": "service",
        "patient_chat_id": chat_id,
        "telegram_username": _get_username(message),
    }

    bot.send_message(
        chat_id,
        BOOKING_INTRO_TEXT,
        reply_markup=services_keyboard(),
    )


def start_booking_from_callback(bot, call):
    chat_id = call.message.chat.id

    booking_sessions[chat_id] = {
        "step": "service",
        "patient_chat_id": chat_id,
        "telegram_username": _get_username_from_call(call),
    }

    bot.answer_callback_query(call.id)

    bot.send_message(
        chat_id,
        BOOKING_INTRO_TEXT,
        reply_markup=services_keyboard(),
    )


def handle_booking_callback(bot, call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "booking_cancel":
        booking_sessions.pop(chat_id, None)

        bot.answer_callback_query(call.id, "Заявку скасовано")
        bot.send_message(
            chat_id,
            BOOKING_CANCELLED_TEXT,
            reply_markup=main_menu_keyboard(),
        )
        return True

    if data.startswith("booking_service:"):
        session = booking_sessions.get(chat_id)

        if session and session.get("step") != "service":
            bot.answer_callback_query(call.id, "Послугу вже обрано")
            return True

        service_key = data.split(":", 1)[1]
        service_name = SERVICES.get(service_key, "Інше питання")

        if not session:
            session = {
                "patient_chat_id": chat_id,
                "telegram_username": _get_username_from_call(call),
            }
            booking_sessions[chat_id] = session

        session["procedure_type"] = service_name
        session["step"] = "name"

        bot.answer_callback_query(call.id, service_name)

        try:
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=None,
            )
        except Exception:
            pass

        bot.send_message(
            chat_id,
            ASK_NAME_TEXT,
            reply_markup=cancel_inline_keyboard(),
        )
        return True

    return False


def handle_booking_message(bot, message):
    chat_id = message.chat.id
    session = booking_sessions.get(chat_id)

    if not session:
        return False

    text = (message.text or "").strip()

    if not text:
        bot.send_message(chat_id, "Будь ласка, напишіть відповідь текстом.")
        return True

    step = session.get("step")

    if step == "name":
        if len(text) < 2:
            bot.send_message(
                chat_id,
                "Ім’я виглядає занадто коротким. Напишіть, будь ласка, ще раз.",
            )
            return True

        session["patient_name"] = text
        session["step"] = "phone"

        bot.send_message(
            chat_id,
            ASK_PHONE_TEXT,
            reply_markup=cancel_inline_keyboard(),
        )
        return True

    if step == "phone":
        if len(text) < 7:
            bot.send_message(
                chat_id,
                "Номер виглядає занадто коротким. Напишіть, будь ласка, повний номер телефону.",
            )
            return True

        session["phone"] = text
        session["step"] = "comment"

        bot.send_message(
            chat_id,
            ASK_COMMENT_TEXT,
            reply_markup=cancel_inline_keyboard(),
        )
        return True

    if step == "comment":
        comment = text
        if text == "-":
            comment = "—"

        session["comment"] = comment
        session["status"] = "new"

        _finish_booking(bot, message, session)

        booking_sessions.pop(chat_id, None)
        return True

    return False


def _finish_booking(bot, message, session):
    chat_id = message.chat.id

    sheet_success, sheet_error, sheet_row = append_booking_request(session)

    bot.send_message(
        chat_id,
        BOOKING_DONE_TEXT,
        reply_markup=main_menu_keyboard(),
    )

    _notify_admin_about_booking(
        bot=bot,
        session=session,
        sheet_success=sheet_success,
        sheet_error=sheet_error,
        sheet_row=sheet_row,
    )


def _notify_admin_about_booking(bot, session, sheet_success, sheet_error, sheet_row):
    if not ADMIN_CHAT_ID:
        print("ADMIN_CHAT_ID is not configured. Booking request was not sent to admin.")
        print(session)
        return

    sheet_status = (
        "✅ Збережено в Google Sheets"
        if sheet_success
        else "⚠️ Не збережено в Google Sheets"
    )

    if sheet_error:
        sheet_status += f"\nПричина: {escape(sheet_error)}"

    text = (
        "🆕 <b>Нова заявка на запис</b>\n\n"
        f"Пацієнт: <b>{escape(session.get('patient_name', ''))}</b>\n"
        f"Телефон: <b>{escape(session.get('phone', ''))}</b>\n"
        f"Послуга: {escape(session.get('procedure_type', ''))}\n"
        f"Коментар: {escape(session.get('comment', ''))}\n"
        f"Telegram: {escape(session.get('telegram_username', '—'))}\n"
        f"chat_id: <code>{session.get('patient_chat_id', '')}</code>\n\n"
        f"{sheet_status}"
    )

    reply_markup = None

    if sheet_success and sheet_row:
        reply_markup = admin_booking_actions_keyboard(sheet_row)

    bot.send_message(
        ADMIN_CHAT_ID,
        text,
        reply_markup=reply_markup,
    )


def _get_username(message):
    username = getattr(message.from_user, "username", None)
    if username:
        return f"@{username}"

    return "—"


def _get_username_from_call(call):
    username = getattr(call.from_user, "username", None)
    if username:
        return f"@{username}"

    return "—"
