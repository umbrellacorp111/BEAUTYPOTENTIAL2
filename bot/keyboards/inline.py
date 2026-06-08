from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup


def start_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Начать разбор", callback_data="start_survey")
    return builder.as_markup()


def goals_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    goals = [
        ("Лицо / черты", "goal_face"),
        ("Стиль одежды", "goal_style"),
        ("Причёска", "goal_hair"),
        ("Форма тела / осанка", "goal_body"),
        ("Уверенность в себе", "goal_confidence"),
        ("Другое", "goal_other"),
    ]
    for text, cb in goals:
        builder.button(text=text, callback_data=cb)
    builder.button(text="✅ Готово", callback_data="goals_done")
    builder.adjust(1)
    return builder.as_markup()


def photo_skip_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📷 Пропустить доп. фото", callback_data="photo_skip")
    return builder.as_markup()


def photo_done_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Готово", callback_data="photo_done")
    return builder.as_markup()


def confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, всё верно", callback_data="confirm_yes")
    builder.button(text="✏️ Изменить данные", callback_data="confirm_edit")
    builder.adjust(1)
    return builder.as_markup()


def edit_choice_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Имя", callback_data="edit_name")
    builder.button(text="🎂 Возраст", callback_data="edit_age")
    builder.button(text="🎯 Цели", callback_data="edit_goals")
    builder.button(text="📸 Фото", callback_data="edit_photos")
    builder.button(text="🔙 Назад", callback_data="edit_back")
    builder.adjust(1)
    return builder.as_markup()


def payment_choice_keyboard(back: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Telegram Stars (299 ★)", callback_data="pay_stars")
    builder.button(text="💳 Банковская карта (1 199 ₽)", callback_data="pay_yukassa")
    if back:
        builder.button(text="🔙 Назад", callback_data="pay_back")
    builder.adjust(1)
    return builder.as_markup()


def yukassa_keyboard(payment_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Оплатить 1 199 ₽", url=payment_url)
    builder.button(text="✅ Я оплатил", callback_data="yukassa_check")
    builder.button(text="🔙 Назад", callback_data="pay_back")
    builder.adjust(1)
    return builder.as_markup()


def feedback_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📞 Да, хочу консультацию", callback_data="fb_consult")
    builder.button(text="🔄 Пройти разбор заново", callback_data="fb_retry")
    builder.button(text="✖️ Нет, спасибо", callback_data="fb_no")
    builder.adjust(1)
    return builder.as_markup()


def admin_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Список заявок", callback_data="admin_list")
    builder.button(text="🆕 Новые заявки", callback_data="admin_new")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.adjust(1)
    return builder.as_markup()


def admin_application_keyboard(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📸 Показать фото", callback_data=f"admin_show_photo_{user_id}")
    builder.button(text="✅ В работу", callback_data=f"admin_work_{user_id}")
    builder.button(text="❌ Отменить", callback_data=f"admin_cancel_{user_id}")
    builder.button(text="📤 Загрузить результат", callback_data=f"admin_result_{user_id}")
    builder.button(text="🔙 Назад", callback_data="admin_back_list")
    builder.adjust(1)
    return builder.as_markup()


def admin_back_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="admin_back")
    return builder.as_markup()
