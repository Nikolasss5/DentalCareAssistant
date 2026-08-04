import re
from html import escape

from config import ADMIN_CHAT_ID, CLINIC_NAME
from keyboards import (
    language_keyboard,
    main_menu_keyboard,
    admin_menu_keyboard,
    composite_actions_keyboard,
    prices_keyboard,
    photo_session_keyboard,
    back_to_menu_keyboard,
)
from texts import (
    normalize_language,
    choose_language_text,
    language_saved_text,
    start_text,
    contact_text,
    price_text,
    composite_sections,
    admin_contact_prompt_text,
    photo_request_text,
    photo_received_text,
    photo_session_finished_text,
    question_sent_text,
    clinic_reply_text,
    no_appointment_text,
    appointment_error_text,
    appointment_text,
    unknown_text,
)
from booking import (
    start_booking,
    start_booking_from_callback,
    handle_booking_message,
    handle_booking_contact,
    handle_booking_callback,
)
from reminders import send_due_reminders, handle_reminder_callback
from postcare import send_due_postcare, handle_postcare_callback
from recall import send_due_recalls, handle_recall_callback
from admin_appointments import (
    handle_admin_appointment_callback,
    handle_admin_appointment_message,
)
from visit_management import show_today_appointments, handle_visit_callback
from sheets import (
    get_admin_stats,
    get_user_language,
    set_user_language,
    get_latest_patient_appointment,
)

contact_sessions = {}


def register_handlers(bot):
    @bot.message_handler(commands=["start"])
    def handle_start(message):
        chat_id = message.chat.id
        language, _ = get_user_language(chat_id)

        if language not in {"uk", "ru"}:
            _show_language_selector(bot, chat_id)
            return

        _send_home(bot, chat_id, language)

    @bot.message_handler(commands=["language"])
    def handle_language(message):
        _show_language_selector(bot, message.chat.id)

    @bot.message_handler(commands=["admin"])
    def handle_admin(message):
        chat_id = message.chat.id

        if _is_admin_chat(chat_id):
            bot.send_message(
                chat_id,
                (
                    "🦷 <b>Панель администратора</b>\n\n"
                    f"Ваш Telegram chat_id:\n<code>{chat_id}</code>\n\n"
                    "Выберите нужное действие:"
                ),
                reply_markup=admin_menu_keyboard(),
            )
            return

        bot.send_message(
            chat_id,
            (
                "Ваш Telegram chat_id:\n\n"
                f"<code>{chat_id}</code>\n\n"
                "Этот раздел доступен только администратору."
            ),
        )

    @bot.message_handler(commands=["admin_help", "admin_menu"])
    def handle_admin_help(message):
        if not _is_admin_chat(message.chat.id):
            bot.send_message(
                message.chat.id,
                "⛔ Эта команда доступна только администратору.",
            )
            return

        _send_admin_help(bot, message.chat.id)

    @bot.message_handler(commands=["admin_stats"])
    def handle_admin_stats(message):
        if not _is_admin_chat(message.chat.id):
            bot.send_message(
                message.chat.id,
                "⛔ Эта команда доступна только администратору.",
            )
            return

        _send_admin_stats(bot, message.chat.id)

    @bot.message_handler(commands=["run_reminders"])
    def handle_run_reminders(message):
        if ADMIN_CHAT_ID and message.chat.id != ADMIN_CHAT_ID:
            bot.send_message(
                message.chat.id,
                "⛔ Эта команда доступна только администратору.",
            )
            return

        sent_count = send_due_reminders(bot)
        bot.send_message(
            message.chat.id,
            f"✅ Проверка напоминаний завершена.\n\nОтправлено: {sent_count}",
        )

    @bot.message_handler(commands=["run_postcare"])
    def handle_run_postcare(message):
        if ADMIN_CHAT_ID and message.chat.id != ADMIN_CHAT_ID:
            bot.send_message(
                message.chat.id,
                "⛔ Эта команда доступна только администратору.",
            )
            return

        sent_count = send_due_postcare(bot)
        bot.send_message(
            message.chat.id,
            f"✅ Проверка рекомендаций завершена.\n\nОтправлено: {sent_count}",
        )

    @bot.message_handler(commands=["run_recalls"])
    def handle_run_recalls(message):
        if ADMIN_CHAT_ID and message.chat.id != ADMIN_CHAT_ID:
            bot.send_message(
                message.chat.id,
                "⛔ Эта команда доступна только администратору.",
            )
            return

        sent_count = send_due_recalls(bot)
        bot.send_message(
            message.chat.id,
            f"✅ Проверка повторных визитов завершена.\n\nОтправлено: {sent_count}",
        )

    @bot.message_handler(commands=["admin_today"])
    def handle_admin_today(message):
        show_today_appointments(bot, message)

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call):
        data = call.data or ""
        chat_id = call.message.chat.id

        if data.startswith("language:"):
            contact_sessions.pop(chat_id, None)
            language = normalize_language(data.split(":", 1)[1])
            username = _get_username(call.from_user)

            set_user_language(
                patient_chat_id=chat_id,
                language=language,
                telegram_username=username,
            )

            bot.answer_callback_query(call.id)
            bot.send_message(chat_id, language_saved_text(language))
            _send_home(bot, chat_id, language)
            return

        if data == "menu_language":
            contact_sessions.pop(chat_id, None)
            bot.answer_callback_query(call.id)
            _show_language_selector(bot, chat_id)
            return

        language = _language_for(chat_id)

        if data == "menu_home":
            contact_sessions.pop(chat_id, None)
            bot.answer_callback_query(call.id)
            _send_home(bot, chat_id, language)
            return

        if data == "menu_prices":
            contact_sessions.pop(chat_id, None)
            bot.answer_callback_query(call.id)
            bot.send_message(
                chat_id,
                price_text(language),
                reply_markup=prices_keyboard(language),
            )
            return

        if data == "prices_composites":
            contact_sessions.pop(chat_id, None)
            bot.answer_callback_query(call.id)
            sections = composite_sections(language)

            for index, section in enumerate(sections):
                reply_markup = None
                if index == len(sections) - 1:
                    reply_markup = composite_actions_keyboard(language)

                bot.send_message(
                    chat_id,
                    section,
                    reply_markup=reply_markup,
                )
            return

        if data == "composite_send_photo":
            bot.answer_callback_query(call.id)
            contact_sessions[chat_id] = {
                "mode": "photos",
                "language": language,
                "photo_count": 0,
            }
            bot.send_message(
                chat_id,
                photo_request_text(language),
                reply_markup=photo_session_keyboard(language),
            )
            return

        if data == "menu_admin_contact":
            bot.answer_callback_query(call.id)
            contact_sessions[chat_id] = {
                "mode": "question",
                "language": language,
                "photo_count": 0,
            }
            bot.send_message(
                chat_id,
                admin_contact_prompt_text(language),
            )
            return

        if data == "contact_finish":
            bot.answer_callback_query(call.id)
            session = contact_sessions.pop(chat_id, None)

            if not session:
                _send_home(bot, chat_id, language)
                return

            session_language = normalize_language(
                session.get("language", language)
            )
            bot.send_message(
                chat_id,
                photo_session_finished_text(session_language),
                reply_markup=main_menu_keyboard(session_language),
            )
            return

        if data == "contact_cancel":
            bot.answer_callback_query(call.id)
            contact_sessions.pop(chat_id, None)
            _send_home(bot, chat_id, language)
            return

        if data == "menu_booking":
            contact_sessions.pop(chat_id, None)
            start_booking_from_callback(bot, call, language)
            return

        if data == "menu_my_appointment":
            contact_sessions.pop(chat_id, None)
            bot.answer_callback_query(call.id)
            _show_my_appointment(bot, chat_id, language)
            return

        if data == "menu_contacts":
            contact_sessions.pop(chat_id, None)
            bot.answer_callback_query(call.id)
            bot.send_message(
                chat_id,
                contact_text(language),
                reply_markup=back_to_menu_keyboard(language),
            )
            return

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

        bot.answer_callback_query(call.id)

    @bot.message_handler(content_types=["contact"])
    def handle_contact(message):
        if handle_booking_contact(bot, message):
            return

        language = _language_for(message.chat.id)
        bot.send_message(
            message.chat.id,
            unknown_text(language),
            reply_markup=main_menu_keyboard(language),
        )

    @bot.message_handler(content_types=["photo"])
    def handle_photo(message):
        chat_id = message.chat.id
        session = contact_sessions.get(chat_id)
        language = normalize_language(
            (session or {}).get("language", _language_for(chat_id))
        )

        if not session:
            bot.send_message(
                chat_id,
                unknown_text(language),
                reply_markup=main_menu_keyboard(language),
            )
            return

        _forward_photo_to_admin(bot, message, language)

        if session.get("mode") == "photos":
            session["photo_count"] = int(session.get("photo_count", 0)) + 1
            bot.send_message(
                chat_id,
                photo_received_text(language, session["photo_count"]),
                reply_markup=photo_session_keyboard(language),
            )
            return

        contact_sessions.pop(chat_id, None)
        bot.send_message(
            chat_id,
            question_sent_text(language),
            reply_markup=main_menu_keyboard(language),
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

        session = contact_sessions.get(chat_id)
        if session:
            language = normalize_language(session.get("language"))
            _forward_text_to_admin(bot, message, language)

            if session.get("mode") == "photos":
                bot.send_message(
                    chat_id,
                    (
                        "✅ Комментарий передан. Можете отправить фото "
                        "или нажать <b>✅ Готово</b>."
                        if language == "ru"
                        else
                        "✅ Коментар передано. Можете надіслати фото "
                        "або натиснути <b>✅ Готово</b>."
                    ),
                    reply_markup=photo_session_keyboard(language),
                )
                return

            contact_sessions.pop(chat_id, None)
            bot.send_message(
                chat_id,
                question_sent_text(language),
                reply_markup=main_menu_keyboard(language),
            )
            return

        language, _ = get_user_language(chat_id)
        if language not in {"uk", "ru"} and not _is_admin_chat(chat_id):
            _show_language_selector(bot, chat_id)
            return

        language = normalize_language(language)

        booking_labels = {
            "📅 Записатися на консультацію",
            "📅 Записаться на консультацию",
        }
        appointment_labels = {"📋 Мій запис", "📋 Моя запись"}
        contact_labels = {
            "💬 Зв’язатися з адміністратором",
            "💬 Связаться с администратором",
        }

        if text in booking_labels:
            start_booking(bot, message, language)
            return

        if text in appointment_labels:
            _show_my_appointment(bot, chat_id, language)
            return

        if text in contact_labels:
            contact_sessions[chat_id] = {
                "mode": "question",
                "language": language,
                "photo_count": 0,
            }
            bot.send_message(
                chat_id,
                admin_contact_prompt_text(language),
            )
            return

        bot.send_message(
            chat_id,
            unknown_text(language),
            reply_markup=main_menu_keyboard(language),
        )


def _show_language_selector(bot, chat_id):
    bot.send_message(
        chat_id,
        choose_language_text(),
        reply_markup=language_keyboard(),
    )


def _send_home(bot, chat_id, language):
    language = normalize_language(language)
    bot.send_message(
        chat_id,
        start_text(language),
        reply_markup=main_menu_keyboard(language),
    )


def _language_for(chat_id):
    language, _ = get_user_language(chat_id)
    return normalize_language(language)


def _show_my_appointment(bot, chat_id, language):
    appointment, error = get_latest_patient_appointment(chat_id)

    if error:
        bot.send_message(
            chat_id,
            appointment_error_text(language),
            reply_markup=main_menu_keyboard(language),
        )
        return

    if not appointment:
        bot.send_message(
            chat_id,
            no_appointment_text(language),
            reply_markup=main_menu_keyboard(language),
        )
        return

    bot.send_message(
        chat_id,
        appointment_text(language, appointment),
        reply_markup=main_menu_keyboard(language),
    )


def _handle_admin_reply_to_patient(bot, message):
    if not _is_admin_chat(message.chat.id):
        return False

    replied_message = getattr(message, "reply_to_message", None)
    if replied_message is None:
        return False

    replied_payload = (
        getattr(replied_message, "text", None)
        or getattr(replied_message, "caption", None)
        or ""
    ).strip()

    allowed_markers = {
        "Новое обращение пациента",
        "Нове питання пацієнта",
        "Новое фото пациента",
    }

    if not any(marker in replied_payload for marker in allowed_markers):
        return False

    match = re.search(r"chat_id:\s*(\d+)", replied_payload)
    if not match:
        bot.send_message(
            message.chat.id,
            (
                "⚠️ Не удалось определить пациента.\n\n"
                "Ответьте именно на уведомление с обращением пациента."
            ),
        )
        return True

    reply_text = (message.text or "").strip()
    if not reply_text:
        bot.send_message(
            message.chat.id,
            "⚠️ Ответ не может быть пустым.",
        )
        return True

    patient_chat_id = int(match.group(1))
    language = _language_for(patient_chat_id)

    try:
        bot.send_message(
            patient_chat_id,
            clinic_reply_text(language, escape(reply_text)),
            reply_markup=main_menu_keyboard(language),
        )
    except Exception as error:
        print(
            f"Failed to send admin reply to patient "
            f"{patient_chat_id}: {error}"
        )
        bot.send_message(
            message.chat.id,
            (
                "⚠️ Не удалось отправить ответ пациенту.\n\n"
                "Возможно, пациент заблокировал бота "
                "или Telegram временно недоступен."
            ),
        )
        return True

    bot.send_message(
        message.chat.id,
        "✅ Ответ отправлен пациенту.",
    )
    return True


def _forward_text_to_admin(bot, message, language):
    chat_id = message.chat.id
    question = (message.text or "").strip()

    if not ADMIN_CHAT_ID:
        print(
            "ADMIN_CHAT_ID is not configured. "
            "Patient message was not sent to admin."
        )
        print(question)
        return

    admin_text = _admin_patient_header(
        message=message,
        language=language,
        title="💬 <b>Новое обращение пациента</b>",
    )
    admin_text += (
        f"\n\nСообщение:\n{escape(question)}\n\n"
        "↩️ <i>Чтобы ответить пациенту, "
        "ответьте на это сообщение.</i>"
    )

    bot.send_message(ADMIN_CHAT_ID, admin_text)


def _forward_photo_to_admin(bot, message, language):
    if not ADMIN_CHAT_ID:
        print(
            "ADMIN_CHAT_ID is not configured. "
            "Patient photo was not sent to admin."
        )
        return

    caption = _admin_patient_header(
        message=message,
        language=language,
        title="📸 <b>Новое фото пациента</b>",
    )

    patient_caption = (message.caption or "").strip()
    if patient_caption:
        caption += f"\n\nКомментарий:\n{escape(patient_caption)}"

    caption += (
        "\n\n↩️ <i>Чтобы ответить пациенту, "
        "ответьте на это фото.</i>"
    )

    photo = message.photo[-1]
    bot.send_photo(
        ADMIN_CHAT_ID,
        photo.file_id,
        caption=caption,
    )


def _admin_patient_header(message, language, title):
    chat_id = message.chat.id
    username = _get_username(message.from_user)
    first_name = getattr(message.from_user, "first_name", "") or ""
    last_name = getattr(message.from_user, "last_name", "") or ""
    full_name = f"{first_name} {last_name}".strip() or "—"
    language_name = "Русский" if language == "ru" else "Українська"

    return (
        f"{title}\n\n"
        f"Клиника: {escape(CLINIC_NAME)}\n"
        f"Пациент: {escape(full_name)}\n"
        f"Язык: {language_name}\n"
        f"Telegram: {escape(username)}\n"
        f"chat_id: <code>{chat_id}</code>"
    )


def _get_username(user):
    username = getattr(user, "username", None)
    return f"@{username}" if username else "—"


def _is_admin_chat(chat_id):
    return bool(ADMIN_CHAT_ID) and chat_id == ADMIN_CHAT_ID


def _send_admin_help(bot, chat_id):
    text = (
        "ℹ️ <b>Команды администратора</b>\n\n"
        "/admin — открыть панель администратора\n"
        "/admin_today — записи на сегодня\n"
        "/admin_stats — краткая статистика\n"
        "/run_reminders — вручную проверить напоминания\n"
        "/run_postcare — проверить рекомендации после визита\n"
        "/run_recalls — проверить повторные визиты\n\n"
        "Чтобы ответить пациенту, используйте функцию "
        "<b>Ответить</b> на сообщении или фотографии с его обращением."
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
                "⚠️ Не удалось получить статистику.\n\n"
                f"Причина: {escape(str(error))}"
            ),
            reply_markup=admin_menu_keyboard(),
        )
        return

    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"Дата: <b>{escape(str(stats.get('today', '')))}</b>\n\n"
        "<b>Сегодня</b>\n"
        f"Заявок: <b>{stats.get('requests_today', 0)}</b>\n"
        f"Записей на сегодня: <b>{stats.get('appointments_today', 0)}</b>\n"
        f"Активных записей: <b>{stats.get('active_today', 0)}</b>\n"
        f"Завершённых визитов: <b>{stats.get('completed_today', 0)}</b>\n"
        f"No-show: <b>{stats.get('no_show_today', 0)}</b>\n\n"
        "<b>Заявки</b>\n"
        f"Всего: <b>{stats.get('booking_total', 0)}</b>\n"
        f"Новые: <b>{stats.get('booking_new', 0)}</b>\n"
        f"Подтверждены: <b>{stats.get('booking_confirmed', 0)}</b>\n"
        f"Отклонены: <b>{stats.get('booking_rejected', 0)}</b>\n\n"
        "<b>Записи</b>\n"
        f"Всего: <b>{stats.get('appointments_total', 0)}</b>\n"
        f"Подтверждены: <b>{stats.get('appointments_confirmed', 0)}</b>\n"
        f"Подтверждены пациентом: "
        f"<b>{stats.get('appointments_confirmed_by_patient', 0)}</b>\n"
        f"Завершены: <b>{stats.get('appointments_completed', 0)}</b>\n"
        f"Переносы: "
        f"<b>{stats.get('appointments_reschedule_requested', 0)}</b>\n"
        f"Отменены: <b>{stats.get('appointments_cancelled', 0)}</b>\n"
        f"No-show: <b>{stats.get('appointments_no_show', 0)}</b>\n\n"
        "<b>Автоматизация</b>\n"
        f"Post-care отправлено: <b>{stats.get('postcare_sent', 0)}</b>\n"
        f"Recall отправлено: <b>{stats.get('recall_sent', 0)}</b>"
    )

    bot.send_message(
        chat_id,
        text,
        reply_markup=admin_menu_keyboard(),
    )
