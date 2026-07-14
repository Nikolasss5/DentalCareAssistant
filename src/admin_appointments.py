from datetime import datetime
from html import escape

from config import ADMIN_CHAT_ID, CLINIC_NAME
from keyboards import main_menu_keyboard
from sheets import (
    get_booking_request_by_row,
    update_booking_request_status,
    append_appointment,
)

admin_appointment_sessions = {}


def handle_admin_appointment_callback(bot, call):
    data = call.data

    if not data.startswith("admin_"):
        return False

    admin_chat_id = call.message.chat.id

    if ADMIN_CHAT_ID and admin_chat_id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "Ця дія доступна тільки адміну")
        return True

    if data.startswith("admin_confirm_booking:"):
        row_number = _extract_row_number(data)

        if not row_number:
            bot.answer_callback_query(call.id, "Помилка заявки")
            return True

        booking_request, error = get_booking_request_by_row(row_number)

        if error or not booking_request:
            bot.answer_callback_query(call.id, "Заявку не знайдено")
            return True

        admin_appointment_sessions[admin_chat_id] = {
            "step": "date",
            "booking_row_number": row_number,
            "booking_request": booking_request,
        }

        update_booking_request_status(row_number, "confirmation_started")

        bot.answer_callback_query(call.id, "Підтвердження запису")

        _remove_admin_buttons(bot, call)

        bot.send_message(
            admin_chat_id,
            (
                "✅ <b>Підтвердження запису</b>\n\n"
                f"Пацієнт: <b>{escape(str(booking_request.get('patient_name', '')))}</b>\n"
                f"Послуга: {escape(str(booking_request.get('procedure_type', '')))}\n\n"
                "Введіть дату візиту у форматі:\n\n"
                "<code>2026-07-10</code>\n\n"
                "Щоб скасувати процес, напишіть /cancel"
            ),
        )
        return True

    if data.startswith("admin_reject_booking:"):
        row_number = _extract_row_number(data)

        if not row_number:
            bot.answer_callback_query(call.id, "Помилка заявки")
            return True

        booking_request, error = get_booking_request_by_row(row_number)

        if error or not booking_request:
            bot.answer_callback_query(call.id, "Заявку не знайдено")
            return True

        update_booking_request_status(row_number, "rejected")

        bot.answer_callback_query(call.id, "Заявку відхилено")
        _remove_admin_buttons(bot, call)

        bot.send_message(
            admin_chat_id,
            (
                "❌ Заявку відхилено.\n\n"
                f"Пацієнт: <b>{escape(str(booking_request.get('patient_name', '')))}</b>\n"
                f"Телефон: {escape(str(booking_request.get('phone', '')))}"
            ),
        )

        _notify_patient_booking_rejected(bot, booking_request)

        return True

    return False


def handle_admin_appointment_message(bot, message):
    admin_chat_id = message.chat.id

    session = admin_appointment_sessions.get(admin_chat_id)

    if not session:
        return False

    if ADMIN_CHAT_ID and admin_chat_id != ADMIN_CHAT_ID:
        return False

    text = (message.text or "").strip()

    if text == "/cancel":
        admin_appointment_sessions.pop(admin_chat_id, None)
        bot.send_message(
            admin_chat_id,
            "❌ Підтвердження запису скасовано.",
            reply_markup=main_menu_keyboard(),
        )
        return True

    step = session.get("step")

    if step == "date":
        if not _is_valid_date(text):
            bot.send_message(
                admin_chat_id,
                (
                    "Дата має бути у форматі:\n\n"
                    "<code>2026-07-10</code>\n\n"
                    "Спробуйте ще раз або напишіть /cancel"
                ),
            )
            return True

        session["appointment_date"] = text
        session["step"] = "time"

        bot.send_message(
            admin_chat_id,
            (
                "Добре. Тепер введіть час візиту у форматі:\n\n"
                "<code>14:30</code>\n\n"
                "Спробуйте ще раз або напишіть /cancel"
            ),
        )
        return True

    if step == "time":
        if not _is_valid_time(text):
            bot.send_message(
                admin_chat_id,
                (
                    "Час має бути у форматі:\n\n"
                    "<code>14:30</code>\n\n"
                    "Спробуйте ще раз або напишіть /cancel"
                ),
            )
            return True

        session["appointment_time"] = text

        _finish_admin_appointment_confirmation(bot, admin_chat_id, session)

        admin_appointment_sessions.pop(admin_chat_id, None)
        return True

    return False


def _finish_admin_appointment_confirmation(bot, admin_chat_id, session):
    booking_request = session.get("booking_request", {})
    booking_row_number = session.get("booking_row_number")

    appointment_data = {
        "patient_chat_id": booking_request.get("patient_chat_id", ""),
        "patient_name": booking_request.get("patient_name", ""),
        "phone": booking_request.get("phone", ""),
        "procedure_type": booking_request.get("procedure_type", ""),
        "appointment_date": session.get("appointment_date", ""),
        "appointment_time": session.get("appointment_time", ""),
        "status": "confirmed",
    }

    success, error = append_appointment(appointment_data)

    if not success:
        bot.send_message(
            admin_chat_id,
            (
                "⚠️ Не вдалося створити запис у Google Sheets.\n\n"
                f"Причина: {escape(str(error))}"
            ),
        )
        return

    if booking_row_number:
        update_booking_request_status(booking_row_number, "confirmed")

    admin_text = (
        "✅ <b>Запис успішно підтверджено</b>\n\n"
        f"Пацієнт: <b>{escape(str(appointment_data.get('patient_name', '')))}</b>\n"
        f"Телефон: {escape(str(appointment_data.get('phone', '')))}\n"
        f"Процедура: {escape(str(appointment_data.get('procedure_type', '')))}\n"
        f"Дата: <b>{escape(str(appointment_data.get('appointment_date', '')))}</b>\n"
        f"Час: <b>{escape(str(appointment_data.get('appointment_time', '')))}</b>"
    )

    bot.send_message(admin_chat_id, admin_text)

    _notify_patient_booking_confirmed(bot, appointment_data)


def _notify_patient_booking_confirmed(bot, appointment_data):
    patient_chat_id = appointment_data.get("patient_chat_id")

    if not patient_chat_id:
        return

    text = (
        "✅ <b>Ваш запис підтверджено</b>\n\n"
        f"Клініка: <b>{escape(CLINIC_NAME)}</b>\n"
        f"Процедура: {escape(str(appointment_data.get('procedure_type', '')))}\n"
        f"Дата: <b>{escape(str(appointment_data.get('appointment_date', '')))}</b>\n"
        f"Час: <b>{escape(str(appointment_data.get('appointment_time', '')))}</b>\n\n"
        "Ми нагадаємо вам про візит заздалегідь 🦷\n\nДо зустрічі!"
    )

    try:
        bot.send_message(
            int(patient_chat_id),
            text,
            reply_markup=main_menu_keyboard(),
        )
    except Exception as error:
        print(f"Could not notify patient about confirmed booking: {error}")


def _notify_patient_booking_rejected(bot, booking_request):
    patient_chat_id = booking_request.get("patient_chat_id")

    if not patient_chat_id:
        return

    text = (
        "❌ <b>Вашу заявку не підтверджено</b>\n\n"
        "Будь ласка, зв’яжіться з клінікою або залиште нову заявку через меню бота."
    )

    try:
        bot.send_message(
            int(patient_chat_id),
            text,
            reply_markup=main_menu_keyboard(),
        )
    except Exception as error:
        print(f"Could not notify patient about rejected booking: {error}")


def _extract_row_number(data):
    try:
        return int(data.split(":", 1)[1])
    except (ValueError, IndexError):
        return None


def _is_valid_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _is_valid_time(value):
    try:
        datetime.strptime(value, "%H:%M")
        return True
    except ValueError:
        return False


def _remove_admin_buttons(bot, call):
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None,
        )
    except Exception:
        pass
