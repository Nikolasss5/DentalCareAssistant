from datetime import datetime
from html import escape

import pytz

from config import ADMIN_CHAT_ID, CLINIC_NAME, TIMEZONE
from keyboards import admin_visit_actions_keyboard, main_menu_keyboard
from postcare import send_due_postcare
from sheets import (
    get_appointments_by_date,
    get_appointment_by_row,
    update_appointment_field,
)


def show_today_appointments(bot, message):
    admin_chat_id = message.chat.id

    if ADMIN_CHAT_ID and admin_chat_id != ADMIN_CHAT_ID:
        bot.send_message(admin_chat_id, "⛔ Ця команда доступна тільки адміну.")
        return

    timezone = pytz.timezone(TIMEZONE)
    today = datetime.now(timezone).strftime("%Y-%m-%d")

    appointments, error = get_appointments_by_date(today)

    if error:
        bot.send_message(
            admin_chat_id,
            (
                "⚠️ Не вдалося отримати записи на сьогодні.\n\n"
                f"Причина: {escape(str(error))}"
            ),
        )
        return

    if not appointments:
        bot.send_message(
            admin_chat_id,
            f"📋 На сьогодні ({today}) активних записів немає.",
        )
        return

    bot.send_message(
        admin_chat_id,
        f"📋 <b>Записи на сьогодні</b>\n\nДата: <b>{today}</b>\nЗнайдено: {len(appointments)}",
    )

    for appointment in appointments:
        row_number = appointment.get("_row_number")

        text = (
            "🦷 <b>Запис пацієнта</b>\n\n"
            f"Ім’я: <b>{escape(str(appointment.get('patient_name', '')))}</b>\n"
            f"Телефон: {escape(str(appointment.get('phone', '')))}\n"
            f"Процедура: {escape(str(appointment.get('procedure_type', '')))}\n"
            f"Дата: <b>{escape(str(appointment.get('appointment_date', '')))}</b>\n"
            f"Час: <b>{escape(str(appointment.get('appointment_time', '')))}</b>\n"
            f"Статус: {escape(str(appointment.get('status', '')))}\n"
            f"chat_id: <code>{escape(str(appointment.get('patient_chat_id', '')))}</code>"
        )

        bot.send_message(
            admin_chat_id,
            text,
            reply_markup=admin_visit_actions_keyboard(row_number),
        )


def handle_visit_callback(bot, call):
    data = call.data

    if not data.startswith("visit_"):
        return False

    admin_chat_id = call.message.chat.id

    if ADMIN_CHAT_ID and admin_chat_id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "Ця дія доступна тільки адміну")
        return True

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

    if action == "visit_completed":
        _update_visit_status(row_number, "completed")

        bot.answer_callback_query(call.id, "Візит завершено")
        _remove_visit_buttons(bot, call)

        bot.send_message(
            admin_chat_id,
            (
                "✅ <b>Візит позначено як завершений</b>\n\n"
                f"Пацієнт: <b>{escape(str(appointment.get('patient_name', '')))}</b>\n"
                f"Процедура: {escape(str(appointment.get('procedure_type', '')))}\n\n"
                "Зараз перевіряю рекомендації після процедури..."
            ),
        )

        sent_count = send_due_postcare(bot)

        bot.send_message(
            admin_chat_id,
            f"🦷 Рекомендації після процедури перевірено.\n\nНадіслано повідомлень: {sent_count}",
        )

        return True

    if action == "visit_no_show":
        _update_visit_status(row_number, "no_show")

        bot.answer_callback_query(call.id, "Позначено як no-show")
        _remove_visit_buttons(bot, call)

        bot.send_message(
            admin_chat_id,
            (
                "🚫 <b>Візит позначено як no-show</b>\n\n"
                f"Пацієнт: <b>{escape(str(appointment.get('patient_name', '')))}</b>\n"
                f"Телефон: {escape(str(appointment.get('phone', '')))}\n"
                f"Дата: {escape(str(appointment.get('appointment_date', '')))}\n"
                f"Час: {escape(str(appointment.get('appointment_time', '')))}"
            ),
        )

        return True

    if action == "visit_reschedule":
        _update_visit_status(row_number, "reschedule_requested")

        bot.answer_callback_query(call.id, "Позначено як перенесення")
        _remove_visit_buttons(bot, call)

        bot.send_message(
            admin_chat_id,
            (
                "🔄 <b>Запис позначено як такий, що потребує перенесення</b>\n\n"
                f"Пацієнт: <b>{escape(str(appointment.get('patient_name', '')))}</b>\n"
                f"Телефон: {escape(str(appointment.get('phone', '')))}"
            ),
        )

        _notify_patient(
            bot,
            appointment,
            (
                "🔄 <b>Ваш запис потребує уточнення</b>\n\n"
                "Адміністратор клініки зв’яжеться з вами для перенесення або уточнення зручного часу."
            ),
        )

        return True

    if action == "visit_cancel":
        _update_visit_status(row_number, "cancelled")

        bot.answer_callback_query(call.id, "Запис скасовано")
        _remove_visit_buttons(bot, call)

        bot.send_message(
            admin_chat_id,
            (
                "❌ <b>Запис скасовано</b>\n\n"
                f"Пацієнт: <b>{escape(str(appointment.get('patient_name', '')))}</b>\n"
                f"Телефон: {escape(str(appointment.get('phone', '')))}"
            ),
        )

        _notify_patient(
            bot,
            appointment,
            (
                "❌ <b>Ваш запис скасовано</b>\n\n"
                "Якщо це помилка або ви хочете записатися повторно — скористайтесь меню бота."
            ),
        )

        return True

    bot.answer_callback_query(call.id)
    return True


def _update_visit_status(row_number, status):
    update_appointment_field(row_number, "status", status)
    update_appointment_field(
        row_number,
        "updated_at",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def _notify_patient(bot, appointment, text):
    patient_chat_id = appointment.get("patient_chat_id")

    if not patient_chat_id:
        return

    try:
        bot.send_message(
            int(patient_chat_id),
            text,
            reply_markup=main_menu_keyboard(),
        )
    except Exception as error:
        print(f"Could not notify patient: {error}")


def _remove_visit_buttons(bot, call):
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None,
        )
    except Exception:
        pass
