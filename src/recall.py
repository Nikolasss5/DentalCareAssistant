from datetime import datetime, timedelta
from html import escape

import pytz

from config import ADMIN_CHAT_ID, CLINIC_NAME, TIMEZONE
from keyboards import main_menu_keyboard, recall_actions_keyboard
from sheets import (
    get_completed_appointments_pending_recall,
    get_postcare_rule_by_procedure,
    update_appointment_field,
    get_appointment_by_row,
)


def send_due_recalls(bot):
    """
    Sends recall reminders for completed appointments.

    Logic:
    - appointment status must be completed
    - recall_sent must be empty
    - procedure_type must have recall_after_days in postcare sheet
    - appointment_date + recall_after_days must be today or earlier
    """
    appointments, error = get_completed_appointments_pending_recall()

    if error:
        print(f"Recall error: {error}")
        return 0

    timezone = pytz.timezone(TIMEZONE)
    today = datetime.now(timezone).date()

    sent_count = 0

    for appointment in appointments:
        row_number = appointment.get("_row_number")
        procedure_type = appointment.get("procedure_type", "")

        appointment_date = _parse_appointment_date(
            appointment.get("appointment_date", "")
        )
        if not appointment_date:
            continue

        postcare_rule, rule_error = get_postcare_rule_by_procedure(procedure_type)

        if rule_error:
            print(f"Recall rule error: {rule_error}")
            continue

        if not postcare_rule:
            print(f"No recall rule found for procedure: {procedure_type}")
            continue

        recall_after_days = _safe_int(postcare_rule.get("recall_after_days", ""))

        if recall_after_days is None:
            print(f"Invalid recall_after_days for procedure: {procedure_type}")
            continue

        recall_date = appointment_date + timedelta(days=recall_after_days)

        if today < recall_date:
            continue

        patient_chat_id = appointment.get("patient_chat_id")

        if not patient_chat_id:
            continue

        _send_patient_recall(
            bot=bot,
            appointment=appointment,
            row_number=row_number,
            recall_after_days=recall_after_days,
        )

        update_appointment_field(row_number, "recall_sent", "yes")

        sent_count += 1

    return sent_count


def handle_recall_callback(bot, call):
    data = call.data

    if not data.startswith("recall_"):
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

    if action == "recall_book":
        bot.answer_callback_query(call.id, "Передано адміністратору")
        _remove_recall_buttons(bot, call)

        bot.send_message(
            chat_id,
            (
                "🗓 Дякуємо! Ми передали адміністратору, що ви хочете записатися.\n\n"
                "Клініка зв’яжеться з вами для уточнення зручної дати та часу."
            ),
            reply_markup=main_menu_keyboard(),
        )

        _notify_admin_about_recall_action(
            bot=bot,
            appointment=appointment,
            action_text="🗓 Пацієнт хоче записатися на повторний візит",
        )
        return True

    if action == "recall_question":
        bot.answer_callback_query(call.id, "Передано адміністратору")
        _remove_recall_buttons(bot, call)

        bot.send_message(
            chat_id,
            (
                "💬 Дякуємо! Ми передали адміністратору, що у вас є питання.\n\n"
                "Клініка зв’яжеться з вами або відповість у Telegram."
            ),
            reply_markup=main_menu_keyboard(),
        )

        _notify_admin_about_recall_action(
            bot=bot,
            appointment=appointment,
            action_text="💬 Пацієнт має питання після recall-нагадування",
        )
        return True

    if action == "recall_later":
        bot.answer_callback_query(call.id, "Добре")
        _remove_recall_buttons(bot, call)

        bot.send_message(
            chat_id,
            (
                "⏳ Добре, не турбуємо.\n\n"
                "Якщо захочете записатися пізніше — скористайтесь кнопкою "
                "<b>🗓 Записатися на прийом</b> у меню."
            ),
            reply_markup=main_menu_keyboard(),
        )
        return True

    bot.answer_callback_query(call.id)
    return True


def _send_patient_recall(bot, appointment, row_number, recall_after_days):
    patient_chat_id = appointment.get("patient_chat_id")
    name = appointment.get("patient_name", "")
    procedure_type = appointment.get("procedure_type", "")
    appointment_date = appointment.get("appointment_date", "")

    text = (
        "🔔 <b>Нагадування про повторний візит</b>\n\n"
        f"{escape(str(name))}, як ваші зубки? 🦷\n\n"
        f"Після процедури <b>{escape(str(procedure_type))}</b> минув рекомендований період "
        f"для контрольного огляду або повторного звернення.\n\n"
        f"Клініка: <b>{escape(CLINIC_NAME)}</b>\n"
        f"Дата попереднього візиту: <b>{escape(str(appointment_date))}</b>\n"
        f"Рекомендований інтервал: {escape(str(recall_after_days))} днів\n\n"
        "Бажаєте, щоб адміністратор допоміг підібрати зручний час?"
    )

    bot.send_message(
        int(patient_chat_id),
        text,
        reply_markup=recall_actions_keyboard(row_number),
    )


def _notify_admin_about_recall_action(bot, appointment, action_text):
    if not ADMIN_CHAT_ID:
        print("ADMIN_CHAT_ID is not configured. Recall action was not sent to admin.")
        return

    text = (
        f"{action_text}\n\n"
        f"Ім’я: <b>{escape(str(appointment.get('patient_name', '')))}</b>\n"
        f"Телефон: <b>{escape(str(appointment.get('phone', '')))}</b>\n"
        f"Попередня процедура: {escape(str(appointment.get('procedure_type', '')))}\n"
        f"Дата попереднього візиту: <b>{escape(str(appointment.get('appointment_date', '')))}</b>\n"
        f"Час: <b>{escape(str(appointment.get('appointment_time', '')))}</b>\n"
        f"chat_id: <code>{escape(str(appointment.get('patient_chat_id', '')))}</code>"
    )

    bot.send_message(ADMIN_CHAT_ID, text)


def _parse_appointment_date(value):
    raw_value = str(value).strip()

    if not raw_value:
        return None

    possible_formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
    ]

    for date_format in possible_formats:
        try:
            return datetime.strptime(raw_value, date_format).date()
        except ValueError:
            continue

    return None


def _safe_int(value):
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _remove_recall_buttons(bot, call):
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None,
        )
    except Exception:
        pass
