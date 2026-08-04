from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)


def _lang(language):
    return "ru" if str(language).strip().lower() == "ru" else "uk"


def language_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            "Українська 🇺🇦",
            callback_data="language:uk",
        ),
        InlineKeyboardButton(
            "Русский 🇷🇺",
            callback_data="language:ru",
        ),
    )
    return keyboard


def main_menu_keyboard(language="uk"):
    language = _lang(language)
    keyboard = InlineKeyboardMarkup(row_width=1)

    if language == "ru":
        buttons = [
            ("💳 Цены на услуги", "menu_prices"),
            ("📅 Записаться на консультацию", "menu_booking"),
            ("📋 Моя запись", "menu_my_appointment"),
            ("💬 Связаться с администратором", "menu_admin_contact"),
            ("📍 Контакты", "menu_contacts"),
            ("🌐 Изменить язык", "menu_language"),
        ]
    else:
        buttons = [
            ("💳 Ціни на послуги", "menu_prices"),
            ("📅 Записатися на консультацію", "menu_booking"),
            ("📋 Мій запис", "menu_my_appointment"),
            ("💬 Зв’язатися з адміністратором", "menu_admin_contact"),
            ("📍 Контакти", "menu_contacts"),
            ("🌐 Змінити мову", "menu_language"),
        ]

    for label, callback_data in buttons:
        keyboard.add(
            InlineKeyboardButton(label, callback_data=callback_data)
        )

    return keyboard


def services_keyboard(language="uk"):
    language = _lang(language)
    keyboard = InlineKeyboardMarkup(row_width=1)

    labels = {
        "uk": [
            ("🦷 Композитні реставрації", "composite"),
            ("🦷 Лікування карієсу / пломба", "caries"),
            ("🦷 Лікування каналу", "root_canal"),
            ("🦷 Цирконієва коронка", "zirconia_crown"),
            ("✨ Відбілювання", "whitening"),
            ("🪥 Професійна чистка", "cleaning"),
            ("👨‍⚕️ Консультація", "consultation"),
            ("❔ Інше питання", "other"),
        ],
        "ru": [
            ("🦷 Композитные реставрации", "composite"),
            ("🦷 Лечение кариеса / пломба", "caries"),
            ("🦷 Лечение канала", "root_canal"),
            ("🦷 Циркониевая коронка", "zirconia_crown"),
            ("✨ Отбеливание", "whitening"),
            ("🪥 Профессиональная чистка", "cleaning"),
            ("👨‍⚕️ Консультация", "consultation"),
            ("❔ Другой вопрос", "other"),
        ],
    }

    for label, service_key in labels[language]:
        keyboard.add(
            InlineKeyboardButton(
                label,
                callback_data=f"booking_service:{service_key}",
            )
        )

    cancel_label = "❌ Отменить" if language == "ru" else "❌ Скасувати"
    keyboard.add(
        InlineKeyboardButton(
            cancel_label,
            callback_data="booking_cancel",
        )
    )
    return keyboard



def prices_keyboard(language="uk"):
    language = _lang(language)
    keyboard = InlineKeyboardMarkup(row_width=1)

    if language == "ru":
        buttons = [
            (
                "🦷 Подробнее о композитных реставрациях",
                "prices_composites",
            ),
            ("📅 Записаться на консультацию", "menu_booking"),
            ("⬅️ Главное меню", "menu_home"),
        ]
    else:
        buttons = [
            (
                "🦷 Детальніше про композитні реставрації",
                "prices_composites",
            ),
            ("📅 Записатися на консультацію", "menu_booking"),
            ("⬅️ Головне меню", "menu_home"),
        ]

    for label, callback_data in buttons:
        keyboard.add(InlineKeyboardButton(label, callback_data=callback_data))

    return keyboard


def composite_actions_keyboard(language="uk"):
    language = _lang(language)
    keyboard = InlineKeyboardMarkup(row_width=1)

    if language == "ru":
        buttons = [
            ("📸 Отправить фотографии", "composite_send_photo"),
            ("📅 Записаться на консультацию", "menu_booking"),
            ("💬 Задать вопрос администратору", "menu_admin_contact"),
            ("⬅️ Главное меню", "menu_home"),
        ]
    else:
        buttons = [
            ("📸 Надіслати фотографії", "composite_send_photo"),
            ("📅 Записатися на консультацію", "menu_booking"),
            ("💬 Запитати адміністратора", "menu_admin_contact"),
            ("⬅️ Головне меню", "menu_home"),
        ]

    for label, callback_data in buttons:
        keyboard.add(InlineKeyboardButton(label, callback_data=callback_data))
    return keyboard


def photo_session_keyboard(language="uk"):
    language = _lang(language)
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            "✅ Готово" if language == "ru" else "✅ Готово",
            callback_data="contact_finish",
        ),
        InlineKeyboardButton(
            "❌ Отменить" if language == "ru" else "❌ Скасувати",
            callback_data="contact_cancel",
        ),
    )
    return keyboard


def back_to_menu_keyboard(language="uk"):
    language = _lang(language)
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            "⬅️ Главное меню" if language == "ru" else "⬅️ Головне меню",
            callback_data="menu_home",
        )
    )
    return keyboard


def cancel_inline_keyboard(language="uk"):
    language = _lang(language)
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            "❌ Отменить" if language == "ru" else "❌ Скасувати",
            callback_data="booking_cancel",
        )
    )
    return keyboard


def phone_request_keyboard(language="uk"):
    language = _lang(language)
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    keyboard.add(
        KeyboardButton(
            (
                "📱 Поделиться номером"
                if language == "ru"
                else "📱 Поділитися номером"
            ),
            request_contact=True,
        )
    )
    return keyboard


def remove_reply_keyboard():
    return ReplyKeyboardRemove()


def reminder_actions_keyboard(row_number, language="uk"):
    language = _lang(language)
    keyboard = InlineKeyboardMarkup(row_width=1)

    if language == "ru":
        labels = [
            ("✅ Подтвердить визит", f"reminder_confirm:{row_number}"),
            ("🔄 Перенести запись", f"reminder_reschedule:{row_number}"),
            ("❌ Отменить", f"reminder_cancel:{row_number}"),
        ]
    else:
        labels = [
            ("✅ Підтвердити візит", f"reminder_confirm:{row_number}"),
            ("🔄 Перенести запис", f"reminder_reschedule:{row_number}"),
            ("❌ Скасувати", f"reminder_cancel:{row_number}"),
        ]

    for label, callback_data in labels:
        keyboard.add(InlineKeyboardButton(label, callback_data=callback_data))
    return keyboard


def postcare_actions_keyboard(row_number, language="uk"):
    language = _lang(language)
    keyboard = InlineKeyboardMarkup(row_width=1)

    if language == "ru":
        labels = [
            ("✅ Всё понятно", f"postcare_ok:{row_number}"),
            ("💬 Нужна консультация", f"postcare_help:{row_number}"),
        ]
    else:
        labels = [
            ("✅ Все зрозуміло", f"postcare_ok:{row_number}"),
            ("💬 Потрібна консультація", f"postcare_help:{row_number}"),
        ]

    for label, callback_data in labels:
        keyboard.add(InlineKeyboardButton(label, callback_data=callback_data))
    return keyboard


def recall_actions_keyboard(row_number, language="uk"):
    language = _lang(language)
    keyboard = InlineKeyboardMarkup(row_width=1)

    if language == "ru":
        labels = [
            ("🗓 Хочу записаться", f"recall_book:{row_number}"),
            ("❓ Задать вопрос", f"recall_question:{row_number}"),
            ("⏳ Не сейчас", f"recall_later:{row_number}"),
        ]
    else:
        labels = [
            ("🗓 Хочу записатися", f"recall_book:{row_number}"),
            ("❓ Поставити питання", f"recall_question:{row_number}"),
            ("⏳ Не зараз", f"recall_later:{row_number}"),
        ]

    for label, callback_data in labels:
        keyboard.add(InlineKeyboardButton(label, callback_data=callback_data))
    return keyboard


def admin_booking_actions_keyboard(booking_row_number):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            "✅ Подтвердить запись",
            callback_data=f"admin_confirm_booking:{booking_row_number}",
        ),
        InlineKeyboardButton(
            "❌ Отклонить заявку",
            callback_data=f"admin_reject_booking:{booking_row_number}",
        ),
    )
    return keyboard


def admin_visit_actions_keyboard(row_number):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            "✅ Визит завершён",
            callback_data=f"visit_completed:{row_number}",
        ),
        InlineKeyboardButton(
            "🚫 No-show",
            callback_data=f"visit_no_show:{row_number}",
        ),
        InlineKeyboardButton(
            "🔄 Перенести запись",
            callback_data=f"visit_reschedule:{row_number}",
        ),
        InlineKeyboardButton(
            "❌ Отменить",
            callback_data=f"visit_cancel:{row_number}",
        ),
    )
    return keyboard


def admin_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            "📋 Записи на сегодня",
            callback_data="admin_menu_today",
        ),
        InlineKeyboardButton(
            "📊 Статистика",
            callback_data="admin_menu_stats",
        ),
        InlineKeyboardButton(
            "ℹ️ Команды администратора",
            callback_data="admin_menu_help",
        ),
    )
    return keyboard
