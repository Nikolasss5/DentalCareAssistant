from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)


def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        InlineKeyboardButton(
            "🗓 Записатися на прийом",
            callback_data="menu_booking",
        ),
        InlineKeyboardButton(
            "📋 Мій запис",
            callback_data="menu_my_appointment",
        ),
        InlineKeyboardButton(
            "❓ Поставити питання",
            callback_data="menu_question",
        ),
        InlineKeyboardButton(
            "🦷 Рекомендації після процедури",
            callback_data="menu_aftercare",
        ),
        InlineKeyboardButton(
            "📍 Контакти клініки",
            callback_data="menu_contacts",
        ),
    )

    return keyboard


def services_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        InlineKeyboardButton(
            "🦷 Консультація",
            callback_data="booking_service:consultation",
        ),
        InlineKeyboardButton(
            "🪥 Професійна чистка",
            callback_data="booking_service:cleaning",
        ),
        InlineKeyboardButton(
            "🛠 Лікування зуба / карієсу",
            callback_data="booking_service:treatment",
        ),
        InlineKeyboardButton(
            "🦷 Видалення зуба",
            callback_data="booking_service:extraction",
        ),
        InlineKeyboardButton(
            "🔩 Імплантація",
            callback_data="booking_service:implant",
        ),
        InlineKeyboardButton(
            "😁 Ортодонтія / брекети",
            callback_data="booking_service:orthodontics",
        ),
        InlineKeyboardButton(
            "❔ Інше питання",
            callback_data="booking_service:other",
        ),
        InlineKeyboardButton(
            "❌ Скасувати",
            callback_data="booking_cancel",
        ),
    )

    return keyboard


def cancel_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            "❌ Скасувати",
            callback_data="booking_cancel",
        )
    )
    return keyboard


def phone_request_keyboard():
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    keyboard.add(
        KeyboardButton(
            "📱 Поділитися номером",
            request_contact=True,
        )
    )

    return keyboard


def remove_reply_keyboard():
    return ReplyKeyboardRemove()


def reminder_actions_keyboard(row_number):
    keyboard = InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        InlineKeyboardButton(
            "✅ Підтвердити візит",
            callback_data=f"reminder_confirm:{row_number}",
        ),
        InlineKeyboardButton(
            "🔄 Перенести запис",
            callback_data=f"reminder_reschedule:{row_number}",
        ),
        InlineKeyboardButton(
            "❌ Скасувати",
            callback_data=f"reminder_cancel:{row_number}",
        ),
    )

    return keyboard


def postcare_actions_keyboard(row_number):
    keyboard = InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        InlineKeyboardButton(
            "✅ Все зрозуміло",
            callback_data=f"postcare_ok:{row_number}",
        ),
        InlineKeyboardButton(
            "💬 Потрібна консультація",
            callback_data=f"postcare_help:{row_number}",
        ),
    )

    return keyboard


def recall_actions_keyboard(row_number):
    keyboard = InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        InlineKeyboardButton(
            "🗓 Так, хочу записатися",
            callback_data=f"recall_book:{row_number}",
        ),
        InlineKeyboardButton(
            "❓ Поставити питання",
            callback_data=f"recall_question:{row_number}",
        ),
        InlineKeyboardButton(
            "⏳ Не зараз",
            callback_data=f"recall_later:{row_number}",
        ),
    )

    return keyboard


def admin_booking_actions_keyboard(booking_row_number):
    keyboard = InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        InlineKeyboardButton(
            "✅ Підтвердити запис",
            callback_data=f"admin_confirm_booking:{booking_row_number}",
        ),
        InlineKeyboardButton(
            "❌ Відхилити заявку",
            callback_data=f"admin_reject_booking:{booking_row_number}",
        ),
    )

    return keyboard


def admin_visit_actions_keyboard(row_number):
    keyboard = InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        InlineKeyboardButton(
            "✅ Візит завершено",
            callback_data=f"visit_completed:{row_number}",
        ),
        InlineKeyboardButton(
            "🚫 No-show",
            callback_data=f"visit_no_show:{row_number}",
        ),
        InlineKeyboardButton(
            "🔄 Перенести запис",
            callback_data=f"visit_reschedule:{row_number}",
        ),
        InlineKeyboardButton(
            "❌ Скасувати",
            callback_data=f"visit_cancel:{row_number}",
        ),
    )

    return keyboard


def admin_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        InlineKeyboardButton(
            "📋 Записи на сьогодні",
            callback_data="admin_menu_today",
        ),
        InlineKeyboardButton(
            "📊 Статистика",
            callback_data="admin_menu_stats",
        ),
        InlineKeyboardButton(
            "ℹ️ Команди адміна",
            callback_data="admin_menu_help",
        ),
    )

    return keyboard

