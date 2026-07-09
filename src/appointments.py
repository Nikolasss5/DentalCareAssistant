from html import escape

from keyboards import main_menu_keyboard
from sheets import get_latest_patient_appointment


def show_my_appointment(bot, message):
    chat_id = message.chat.id

    appointment, error = get_latest_patient_appointment(chat_id)

    if error:
        bot.send_message(
            chat_id,
            (
                "⚠️ Не вдалося перевірити ваш запис.\n\n"
                "Спробуйте, будь ласка, пізніше або зверніться до адміністратора клініки."
            ),
            reply_markup=main_menu_keyboard(),
        )
        return

    if not appointment:
        bot.send_message(
            chat_id,
            (
                "📋 <b>Мій запис</b>\n\n"
                "Наразі я не бачу підтвердженого запису.\n\n"
                "Якщо ви вже залишили заявку — адміністратор клініки скоро зв’яжеться з вами "
                "для підтвердження дати та часу."
            ),
            reply_markup=main_menu_keyboard(),
        )
        return

    text = (
        "📋 <b>Ваш запис</b>\n\n"
        f"Ім’я: <b>{escape(str(appointment.get('patient_name', '')))}</b>\n"
        f"Телефон: {escape(str(appointment.get('phone', '')))}\n"
        f"Процедура: {escape(str(appointment.get('procedure_type', '')))}\n"
        f"Дата: <b>{escape(str(appointment.get('appointment_date', '')))}</b>\n"
        f"Час: <b>{escape(str(appointment.get('appointment_time', '')))}</b>\n"
        f"Статус: {escape(str(appointment.get('status', '')))}\n\n"
        "Якщо потрібно перенести або скасувати запис — напишіть клініці через кнопку "
        "<b>💬 Поставити питання</b>."
    )

    bot.send_message(
        chat_id,
        text,
        reply_markup=main_menu_keyboard(),
    )
