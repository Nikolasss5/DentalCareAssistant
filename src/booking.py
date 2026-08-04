from html import escape

from config import ADMIN_CHAT_ID
from keyboards import (
    services_keyboard,
    cancel_inline_keyboard,
    main_menu_keyboard,
    admin_booking_actions_keyboard,
    phone_request_keyboard,
    remove_reply_keyboard,
)
from sheets import append_booking_request
from texts import (
    normalize_language,
    booking_intro_text,
    ask_name_text,
    ask_phone_text,
    ask_comment_text,
    booking_done_text,
    booking_cancelled_text,
)

booking_sessions = {}


SERVICES = {
    "composite": {
        "internal": "Композитные реставрации",
        "uk": "Композитні реставрації",
        "ru": "Композитные реставрации",
    },
    "caries": {
        "internal": "Лечение кариеса / пломба",
        "uk": "Лікування карієсу / пломба",
        "ru": "Лечение кариеса / пломба",
    },
    "root_canal": {
        "internal": "Лечение канала",
        "uk": "Лікування каналу",
        "ru": "Лечение канала",
    },
    "zirconia_crown": {
        "internal": "Циркониевая коронка",
        "uk": "Цирконієва коронка",
        "ru": "Циркониевая коронка",
    },
    "whitening": {
        "internal": "Отбеливание",
        "uk": "Відбілювання",
        "ru": "Отбеливание",
    },
    "cleaning": {
        "internal": "Профессиональная чистка",
        "uk": "Професійна чистка",
        "ru": "Профессиональная чистка",
    },
    "consultation": {
        "internal": "Консультация",
        "uk": "Консультація",
        "ru": "Консультация",
    },
    "other": {
        "internal": "Другой вопрос",
        "uk": "Інше питання",
        "ru": "Другой вопрос",
    },
}


def start_booking(bot, message, language="uk"):
    chat_id = message.chat.id
    language = normalize_language(language)

    booking_sessions[chat_id] = {
        "step": "service",
        "language": language,
        "patient_chat_id": chat_id,
        "telegram_username": _get_username(message),
    }

    bot.send_message(
        chat_id,
        booking_intro_text(language),
        reply_markup=services_keyboard(language),
    )


def start_booking_from_callback(bot, call, language="uk"):
    chat_id = call.message.chat.id
    language = normalize_language(language)

    booking_sessions[chat_id] = {
        "step": "service",
        "language": language,
        "patient_chat_id": chat_id,
        "telegram_username": _get_username_from_call(call),
    }

    bot.answer_callback_query(call.id)

    bot.send_message(
        chat_id,
        booking_intro_text(language),
        reply_markup=services_keyboard(language),
    )


def handle_booking_callback(bot, call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "booking_cancel":
        session = booking_sessions.pop(chat_id, None)
        language = normalize_language(
            (session or {}).get("language", "uk")
        )

        bot.answer_callback_query(
            call.id,
            "Заявка отменена" if language == "ru" else "Заявку скасовано",
        )
        bot.send_message(
            chat_id,
            booking_cancelled_text(language),
            reply_markup=main_menu_keyboard(language),
        )
        return True

    if data.startswith("booking_service:"):
        session = booking_sessions.get(chat_id)

        if session and session.get("step") != "service":
            language = normalize_language(session.get("language"))
            bot.answer_callback_query(
                call.id,
                (
                    "Услуга уже выбрана"
                    if language == "ru"
                    else "Послугу вже обрано"
                ),
            )
            return True

        service_key = data.split(":", 1)[1]
        service = SERVICES.get(service_key, SERVICES["other"])

        if not session:
            session = {
                "language": "uk",
                "patient_chat_id": chat_id,
                "telegram_username": _get_username_from_call(call),
            }
            booking_sessions[chat_id] = session

        language = normalize_language(session.get("language"))
        session["procedure_key"] = service_key
        session["procedure_type"] = service["internal"]
        session["step"] = "name"

        bot.answer_callback_query(call.id, service[language])

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
            ask_name_text(language),
            reply_markup=cancel_inline_keyboard(language),
        )
        return True

    return False


def handle_booking_message(bot, message):
    chat_id = message.chat.id
    session = booking_sessions.get(chat_id)

    if not session:
        return False

    language = normalize_language(session.get("language"))
    text = (message.text or "").strip()

    if not text:
        bot.send_message(
            chat_id,
            (
                "Пожалуйста, отправьте ответ текстом."
                if language == "ru"
                else "Будь ласка, надішліть відповідь текстом."
            ),
        )
        return True

    step = session.get("step")

    if step == "name":
        if len(text) < 2:
            bot.send_message(
                chat_id,
                (
                    "Имя выглядит слишком коротким. Напишите ещё раз."
                    if language == "ru"
                    else "Ім’я виглядає надто коротким. Напишіть ще раз."
                ),
            )
            return True

        session["patient_name"] = text
        session["step"] = "phone"

        share_hint = (
            "Нажмите кнопку <b>📱 Поделиться номером</b> "
            "или напишите номер вручную."
            if language == "ru"
            else
            "Натисніть кнопку <b>📱 Поділитися номером</b> "
            "або напишіть номер вручну."
        )

        bot.send_message(
            chat_id,
            f"{ask_phone_text(language)}\n\n{share_hint}",
            reply_markup=phone_request_keyboard(language),
        )
        return True

    if step == "phone":
        if len(text) < 7:
            bot.send_message(
                chat_id,
                (
                    "Номер выглядит слишком коротким. "
                    "Введите полный номер телефона."
                    if language == "ru"
                    else
                    "Номер виглядає надто коротким. "
                    "Введіть повний номер телефону."
                ),
            )
            return True

        _save_phone_and_ask_comment(
            bot=bot,
            chat_id=chat_id,
            session=session,
            phone=text,
        )
        return True

    if step == "comment":
        session["comment"] = "—" if text == "-" else text
        session["status"] = "new"

        _finish_booking(bot, message, session)
        booking_sessions.pop(chat_id, None)
        return True

    return False


def handle_booking_contact(bot, message):
    chat_id = message.chat.id
    session = booking_sessions.get(chat_id)

    if not session or session.get("step") != "phone":
        return False

    language = normalize_language(session.get("language"))
    contact = getattr(message, "contact", None)

    if not contact or not getattr(contact, "phone_number", None):
        bot.send_message(
            chat_id,
            (
                "Не удалось получить номер. Напишите его вручную."
                if language == "ru"
                else "Не вдалося отримати номер. Напишіть його вручну."
            ),
        )
        return True

    phone = str(contact.phone_number).strip()
    if phone and not phone.startswith("+"):
        phone = f"+{phone}"

    _save_phone_and_ask_comment(
        bot=bot,
        chat_id=chat_id,
        session=session,
        phone=phone,
    )
    return True


def _save_phone_and_ask_comment(bot, chat_id, session, phone):
    language = normalize_language(session.get("language"))
    session["phone"] = phone
    session["step"] = "comment"

    bot.send_message(
        chat_id,
        (
            "Номер сохранён ✅"
            if language == "ru"
            else "Номер збережено ✅"
        ),
        reply_markup=remove_reply_keyboard(),
    )

    bot.send_message(
        chat_id,
        ask_comment_text(language),
        reply_markup=cancel_inline_keyboard(language),
    )


def _finish_booking(bot, message, session):
    chat_id = message.chat.id
    language = normalize_language(session.get("language"))

    sheet_success, sheet_error, sheet_row = append_booking_request(session)

    bot.send_message(
        chat_id,
        booking_done_text(language),
        reply_markup=main_menu_keyboard(language),
    )

    _notify_admin_about_booking(
        bot=bot,
        session=session,
        sheet_success=sheet_success,
        sheet_error=sheet_error,
        sheet_row=sheet_row,
    )


def _notify_admin_about_booking(
    bot,
    session,
    sheet_success,
    sheet_error,
    sheet_row,
):
    if not ADMIN_CHAT_ID:
        print(
            "ADMIN_CHAT_ID is not configured. "
            "Booking request was not sent to admin."
        )
        print(session)
        return

    language = normalize_language(session.get("language"))
    language_name = "Русский" if language == "ru" else "Українська"

    sheet_status = (
        "✅ Сохранено в Google Sheets"
        if sheet_success
        else "⚠️ Не сохранено в Google Sheets"
    )

    if sheet_error:
        sheet_status += f"\nПричина: {escape(str(sheet_error))}"

    text = (
        "🆕 <b>Новая заявка на консультацию</b>\n\n"
        f"Пациент: <b>{escape(session.get('patient_name', ''))}</b>\n"
        f"Телефон: <b>{escape(session.get('phone', ''))}</b>\n"
        f"Услуга: {escape(session.get('procedure_type', ''))}\n"
        f"Комментарий: {escape(session.get('comment', ''))}\n"
        f"Язык: {language_name}\n"
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
    return f"@{username}" if username else "—"


def _get_username_from_call(call):
    username = getattr(call.from_user, "username", None)
    return f"@{username}" if username else "—"
