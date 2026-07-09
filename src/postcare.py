from html import escape

from config import ADMIN_CHAT_ID, CLINIC_NAME
from keyboards import main_menu_keyboard, postcare_actions_keyboard
from sheets import (
    get_completed_appointments_pending_postcare,
    get_postcare_rule_by_procedure,
    update_appointment_field,
    get_appointment_by_row,
)


def send_due_postcare(bot):
    """
    Sends procedure-based postcare instructions for completed appointments.
    """
    appointments, error = get_completed_appointments_pending_postcare()

    if error:
        print(f"Postcare error: {error}")
        return 0

    sent_count = 0

    for appointment in appointments:
        row_number = appointment.get("_row_number")
        procedure_type = appointment.get("procedure_type", "")

        postcare_rule, rule_error = get_postcare_rule_by_procedure(procedure_type)

        if rule_error:
            print(f"Postcare rule error: {rule_error}")
            continue

        if not postcare_rule:
            print(f"No postcare rule found for procedure: {procedure_type}")
            continue

        patient_chat_id = appointment.get("patient_chat_id")
        if not patient_chat_id:
            continue

        postcare_text = postcare_rule.get("postcare_text", "")

        if not postcare_text:
            continue

        text = (
            f"🦷 <b>Рекомендації після візиту</b>\n\n"
            f"{escape(str(appointment.get('patient_name', '')))}, "
            f"дякуємо за візит у <b>{escape(CLINIC_NAME)}</b>.\n\n"
            f"<b>Процедура:</b> {escape(str(procedure_type))}\n\n"
            f"{escape(str(postcare_text))}\n\n"
            "Якщо щось турбує — натисніть кнопку нижче."
        )

        bot.send_message(
            int(patient_chat_id),
            text,
            reply_markup=postcare_actions_keyboard(row_number),
        )

        update_appointment_field(row_number, "postcare_sent", "yes")

        sent_count += 1

    return sent_count


def handle_postcare_callback(bot, call):
    data = call.data

    if not data.startswith("postcare_"):
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

    if action == "postcare_ok":
        bot.answer_callback_query(call.id, "Дякуємо")
        _remove_postcare_buttons(bot, call)

        bot.send_message(
            chat_id,
            "✅ Дякуємо! Якщо з’являться питання — ви завжди можете написати клініці.",
            reply_markup=main_menu_keyboard(),
        )
        return True

    if action == "postcare_help":
        bot.answer_callback_query(call.id, "Передано адміністратору")
        _remove_postcare_buttons(bot, call)

        bot.send_message(
            chat_id,
            (
                "💬 Ми передали адміністратору, що вам потрібна консультація.\n\n"
                "Клініка зв’яжеться з вами або відповість у Telegram."
            ),
            reply_markup=main_menu_keyboard(),
        )

        _notify_admin_about_postcare_help(bot, appointment)
        return True

    bot.answer_callback_query(call.id)
    return True


def _notify_admin_about_postcare_help(bot, appointment):
    if not ADMIN_CHAT_ID:
        print("ADMIN_CHAT_ID is not configured. Postcare help was not sent to admin.")
        return

    text = (
        "⚠️ <b>Пацієнту потрібна консультація після процедури</b>\n\n"
        f"Ім’я: <b>{escape(str(appointment.get('patient_name', '')))}</b>\n"
        f"Телефон: <b>{escape(str(appointment.get('phone', '')))}</b>\n"
        f"Процедура: {escape(str(appointment.get('procedure_type', '')))}\n"
        f"Дата візиту: <b>{escape(str(appointment.get('appointment_date', '')))}</b>\n"
        f"Час: <b>{escape(str(appointment.get('appointment_time', '')))}</b>\n"
        f"chat_id: <code>{escape(str(appointment.get('patient_chat_id', '')))}</code>"
    )

    bot.send_message(ADMIN_CHAT_ID, text)


def _remove_postcare_buttons(bot, call):
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None,
        )
    except Exception:
        pass
