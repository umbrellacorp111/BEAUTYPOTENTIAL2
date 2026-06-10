from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup


def start_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Начать разбор", callback_data="start_survey")
    builder.button(text="📂 Мои разборы", callback_data="my_analyses")
    builder.button(text="👗 ИИ-Стилист PRO", callback_data="stylist_pro_info")
    builder.adjust(1)
    return builder.as_markup()


def analyses_list_keyboard(analyses: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for a in analyses:
        date_str = a.created_at.strftime("%d.%m.%Y %H:%M")
        label = f"📄 Разбор #{a.id} от {date_str}"
        builder.button(text=label, callback_data=f"view_analysis_{a.id}")
    builder.button(text="🏠 В начало", callback_data="go_home")
    builder.adjust(1)
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
    builder.button(text="📷 Пропустить", callback_data="photo_skip")
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


def free_analysis_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔥 Открыть полный отчёт", callback_data="buy_full_report")
    return builder.as_markup()


def credit_packages_keyboard(balance: int) -> InlineKeyboardMarkup:
    from bot.config import config
    builder = InlineKeyboardBuilder()
    labels = [p["label"] for p in config.CREDIT_PACKAGES]
    callbacks = ["buy_1", "buy_5", "buy_100"]
    for label, cb in zip(labels, callbacks):
        builder.button(text=label, callback_data=cb)
    builder.button(
        text=config.STYLIST_PACKAGE["label"],
        callback_data="buy_stylist",
    )
    builder.adjust(1)
    return builder.as_markup()


def payment_choice_keyboard(package_index: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Картой (ЮКасса)", callback_data=f"pay_card_{package_index}")
    builder.button(text="🔙 Назад", callback_data="pay_back")
    builder.adjust(1)
    return builder.as_markup()


def use_credit_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, сделать разбор", callback_data="use_credit_yes")
    builder.button(text="🔙 Назад", callback_data="use_credit_no")
    builder.adjust(1)
    return builder.as_markup()


def after_report_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Новый разбор", callback_data="start_survey")
    builder.button(text="🏠 В начало", callback_data="go_home")
    builder.adjust(1)
    return builder.as_markup()


def stylist_pro_info_keyboard() -> InlineKeyboardMarkup:
    from bot.config import config
    rub = config.STYLIST_PRO_PACKAGE["rub"]
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💳 Купить за {rub}₽", callback_data="stylist_pro_buy")
    builder.button(text="🔙 Назад", callback_data="go_home")
    builder.adjust(1)
    return builder.as_markup()


def stylist_renew_keyboard() -> InlineKeyboardMarkup:
    from bot.config import config
    rub = config.STYLIST_PRO_PACKAGE["rub"]
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💳 Продлить за {rub}₽", callback_data="stylist_pro_buy")
    builder.button(text="🔙 Назад", callback_data="go_home")
    builder.adjust(1)
    return builder.as_markup()


def stylist_chat_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 В начало", callback_data="go_home")
    return builder.as_markup()


# ──────────────────────────────────────────────
# Admin panel keyboards
# ──────────────────────────────────────────────


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Заявки стилиста", callback_data="admin_apps")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="❌ Закрыть панель", callback_data="admin_close")
    builder.adjust(1)
    return builder.as_markup()


def admin_apps_list_keyboard(apps: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for app in apps:
        status_icon = "🕐" if app.status == "pending" else "🔧"
        label = f"{status_icon} Заявка #{app.id} — {app.first_name or '?'}"
        builder.button(text=label, callback_data=f"admin_app_{app.id}")
    builder.button(text="🔙 Назад", callback_data="admin_back_menu")
    builder.adjust(1)
    return builder.as_markup()


def admin_app_detail_keyboard(app: object) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if app.status == "pending":
        builder.button(text="▶ Взять в работу", callback_data=f"admin_app_take_{app.id}")
    if app.status == "in_progress":
        builder.button(text="✅ Завершить", callback_data=f"admin_app_complete_{app.id}")
    builder.button(text="🗑 Удалить", callback_data=f"admin_app_delete_{app.id}")
    builder.button(text="🔙 Назад", callback_data="admin_apps")
    builder.adjust(1)
    return builder.as_markup()
