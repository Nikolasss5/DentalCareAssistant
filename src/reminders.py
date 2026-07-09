from datetime import datetime, timedelta
from html import escape

import pytz

from config import ADMIN_CHAT_ID, CLINIC_NAME, TIMEZONE
from keyboards import reminder_actions_keyboard, main_menu_keyboard
from sheets import (
    get_upcoming_confirmed_appointments,
    update_appointment_field,
    get_appointment_by_row,
)


def send_due_reminders(bot):
    """
    Sends reminders for confirmed appointments.

    Logic:
    - if appointment is within 2 hours -> send 2h reminder
    - else if appointment is within 24 hours -> send 24h reminder
    """
    appointments, error = get_upcoming_confirmed_appointments()

    if error:
        print(f"Reminder error: {error}")
        return 0

    timezone = pytz.timezone(TIMEZONE)
    now = datetime.now(timezone)

    sent_count = 0

    for appointment in appointments:
        appointment_dt = _parse_appointment_datetime(appointment, timezone)

        if not appointment_dt:
            continue

        time_left = appointment_dt - now

        if time_left <= timedelta(0):
            continue

        row_number = appointment.get("_row_number")

        reminder_2h_sent = str(appointment.get("reminder_2h_sent", "")).strip().lower()
        reminder_24h_sent = (
            str(appointment.get("reminder_24h_sent", "")).strip().lower()
        )

        if time_left <= timedelta(hours=2) and reminder_2h_sent != "yes":
            _send_patient_reminder(
                bot=bot,
                appointment=appointment,
                row_number=row_number,
                reminder_type="2h",
            )
            update_appointment_field(row_number, "reminder_2h_sent", "yes")
            sent_count += 1
            continue

        if time_left <= timedelta(hours=24) and reminder_24h_sent != "yes":
            _send_patient_reminder(
                bot=bot,
                appointment=appointment,
                row_number=row_number,
                reminder_type="24h",
            )
            update_appointment_field(row_number, "reminder_24h_sent", "yes")
            sent_count += 1

    return sent_count


def handle_reminder_callback(bot, call):
    data = call.data

    if not data.startswith("reminder_"):
        return False

    action, row_number_raw = data.split(":", 1)

    try:
        row_number = int(row_number_raw)
    except ValueError:
        bot.answer_callback_query(call.id, "Помилка запису")
        return True

    appointment, error = get_appointment_by_row(row_number)

    if error or not appointment:
        bot.answer_callback_query(call.id, "Запис не знайдено")
        return True

    chat_id = call.message.chat.id

    if action == "reminder_confirm":
        update_appointment_field(row_number, "status", "confirmed_by_patient")

        bot.answer_callback_query(call.id, "Візит підтверджено")
        _remove_reminder_buttons(bot, call)

        bot.send_message(
            chat_id,
            "✅ Дякуємо! Ваш візит підтверджено.\n\nЧекаємо на вас у клініці 🦷",
            reply_markup=main_menu_keyboard(),
        )

        _notify_admin_about_patient_action(
            bot=bot,
            appointment=appointment,
            action_text="✅ Пацієнт підтвердив візит",
        )
        return True

    if action == "reminder_reschedule":
        update_appointment_field(row_number, "status", "reschedule_requested")

        bot.answer_callback_query(call.id, "Запит на перенесення передано")
        _remove_reminder_buttons(bot, call)
        bot.send_message(
            chat_id,
            (
                "🔄 Дякуємо. Ми передали адміністратору, що ви хочете перенести запис.\n\n"
                "Клініка зв’яжеться з вами для уточнення нового часу."
            ),
            reply_markup=main_menu_keyboard(),
        )

        _notify_admin_about_patient_action(
            bot=bot,
            appointment=appointment,
            action_text="🔄 Пацієнт хоче перенести запис",
        )
        return True

    if action == "reminder_cancel":
        update_appointment_field(row_number, "status", "cancelled")

        bot.answer_callback_query(call.id, "Запис скасовано")
        _remove_reminder_buttons(bot, call)
        bot.send_message(
            chat_id,
            (
                "❌ Ми передали адміністратору, що ви хочете скасувати запис.\n\n"
                "Якщо це помилка — напишіть клініці через кнопку 💬 Поставити питання."
            ),
            reply_markup=main_menu_keyboard(),
        )

        _notify_admin_about_patient_action(
            bot=bot,
            appointment=appointment,
            action_text="❌ Пацієнт хоче скасувати запис",
        )
        return True

    bot.answer_callback_query(call.id)
    return True


def _send_patient_reminder(bot, appointment, row_number, reminder_type):
    patient_chat_id = appointment.get("patient_chat_id")

    if not patient_chat_id:
        return

    name = appointment.get("patient_name", "")
    procedure = appointment.get("procedure_type", "")
    appointment_date = appointment.get("appointment_date", "")
    appointment_time = appointment.get("appointment_time", "")

    if reminder_type == "2h":
        title = "⏰ Нагадування про візит"
        intro = "Ваш візит вже скоро — приблизно через 2 години."
    else:
        title = "📅 Нагадування про візит"
        intro = "Нагадуємо, що у вас запланований візит до клініки."

    text = (
        f"{title}\n\n"
        f"{escape(str(name))}, {intro}\n\n"
        f"Клініка: <b>{escape(CLINIC_NAME)}</b>\n"
        f"Процедура: {escape(str(procedure))}\n"
        f"Дата: <b>{escape(str(appointment_date))}</b>\n"
        f"Час: <b>{escape(str(appointment_time))}</b>\n\n"
        "Підтвердіть, будь ласка, ваш візит:"
    )

    bot.send_message(
        int(patient_chat_id),
        text,
        reply_markup=reminder_actions_keyboard(row_number),
    )


def _notify_admin_about_patient_action(bot, appointment, action_text):
    if not ADMIN_CHAT_ID:
        print("ADMIN_CHAT_ID is not configured. Reminder action was not sent to admin.")
        return

    text = (
        f"{action_text}\n\n"
        f"Ім’я: <b>{escape(str(appointment.get('patient_name', '')))}</b>\n"
        f"Телефон: <b>{escape(str(appointment.get('phone', '')))}</b>\n"
        f"Процедура: {escape(str(appointment.get('procedure_type', '')))}\n"
        f"Дата: <b>{escape(str(appointment.get('appointment_date', '')))}</b>\n"
        f"Час: <b>{escape(str(appointment.get('appointment_time', '')))}</b>\n"
        f"chat_id: <code>{escape(str(appointment.get('patient_chat_id', '')))}</code>"
    )

    bot.send_message(ADMIN_CHAT_ID, text)


def _parse_appointment_datetime(appointment, timezone):
    appointment_date = str(appointment.get("appointment_date", "")).strip()
    appointment_time = str(appointment.get("appointment_time", "")).strip()

    if not appointment_date or not appointment_time:
        return None

    possible_formats = [
        "%Y-%m-%d %H:%M",
        "%d.%m.%Y %H:%M",
    ]

    raw_value = f"{appointment_date} {appointment_time}"

    for date_format in possible_formats:
        try:
            naive_dt = datetime.strptime(raw_value, date_format)
            return timezone.localize(naive_dt)
        except ValueError:
            continue

    return None


def _remove_reminder_buttons(bot, call):
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None,
        )
    except Exception:
        pass
