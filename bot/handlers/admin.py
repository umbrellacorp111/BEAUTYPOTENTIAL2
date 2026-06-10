import os
import logging
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.filters.admin import AdminFilter, AdminCbFilter
from bot.states.user_states import AdminState
from bot.keyboards.inline import (
    admin_menu_keyboard, admin_apps_list_keyboard, admin_app_detail_keyboard,
    admin_godmode_keyboard,
)
from bot.db.queries import (
    get_all_users, get_user_by_id, get_stylist_applications,
    get_stylist_application, get_total_users, get_total_payments,
    get_total_applications, get_applications_count_by_status,
    get_active_subscriptions_count, get_recent_users,
    update_stylist_application_status, set_godmode, get_user,
)
from bot.config import config

logger = logging.getLogger(__name__)

router = Router()


# ──────────────────────────────────────────────
# /admin
# ──────────────────────────────────────────────

@router.message(Command("admin"), AdminFilter())
async def admin_panel(message: Message):
    await message.answer(
        "🛠 Админ-панель\n\nВыберите раздел:",
        reply_markup=admin_menu_keyboard(),
    )


@router.message(Command("admin"))
async def admin_no_access(message: Message):
    await message.answer("⛔ У вас нет доступа к этой команде.")


# ──────────────────────────────────────────────
# Callback router
# ──────────────────────────────────────────────

@router.callback_query(AdminCbFilter(), F.data == "admin_back_menu")
async def admin_back_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "🛠 Админ-панель\n\nВыберите раздел:",
        reply_markup=admin_menu_keyboard(),
    )


@router.callback_query(AdminCbFilter(), F.data == "admin_close")
async def admin_close(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()


# ──────────────────────────────────────────────
# Заявки стилиста
# ──────────────────────────────────────────────

@router.callback_query(AdminCbFilter(), F.data == "admin_apps")
async def admin_show_apps(callback: CallbackQuery):
    await callback.answer()
    apps = await get_stylist_applications()
    active = [a for a in apps if a.status in ("pending", "in_progress")]
    if not active:
        await callback.message.edit_text(
            "📋 Нет активных заявок.",
            reply_markup=admin_menu_keyboard(),
        )
        return
    await callback.message.edit_text(
        f"📋 Активные заявки ({len(active)}):",
        reply_markup=admin_apps_list_keyboard(active),
    )


@router.callback_query(AdminCbFilter(), F.data.startswith("admin_app_"))
async def admin_view_app(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    parts = callback.data.split("_")
    app_id = int(parts[-1])
    app = await get_stylist_application(app_id)
    if not app:
        await callback.message.edit_text("❌ Заявка не найдена.")
        return

    photo_status = "✅ есть" if app.last_photo_id else "❌ отсутствует"
    created = app.created_at.strftime("%d.%m.%Y %H:%M") if app.created_at else "—"
    paid = app.payment_date.strftime("%d.%m.%Y %H:%M") if app.payment_date else "—"
    goals_list = (app.goals or [])
    goals_str = ", ".join(g.replace("goal_", "").capitalize() for g in goals_list) if goals_list else "—"
    photo_ids = app.photo_ids or []
    photo_count = len(photo_ids)
    analysis_preview = (app.analysis_text or "—")[:200]
    if app.analysis_text and len(app.analysis_text) > 200:
        analysis_preview += "..."

    text = (
        f"🧾 Заявка #{app.id}\n\n"
        f"👤 Имя в боте: {app.name or '—'}\n"
        f"👤 Telegram: {app.first_name or '—'}\n"
        f"🆔 User ID: {app.telegram_id}\n"
        f"📎 Username: @{app.username or '—'}\n"
        f"🎂 Возраст: {app.age or '—'}\n"
        f"🎯 Цели: {goals_str}\n"
        f"📅 Создана: {created}\n"
        f"📅 Оплачена: {paid}\n"
        f"📌 Статус: {app.status}\n"
        f"📄 Анализ: {analysis_preview}\n"
        f"📸 Фото: {photo_status} ({photo_count} шт.)"
    )

    await callback.message.edit_text(text, reply_markup=admin_app_detail_keyboard(app))

    if photo_ids:
        for pid in photo_ids:
            try:
                await callback.message.answer_photo(photo=pid)
            except Exception as e:
                logger.warning(f"Cannot send photo {pid} for app #{app.id}: {e}")


# ──────────────────────────────────────────────
# Управление статусами заявок
# ──────────────────────────────────────────────

async def _notify_user(bot: Bot, telegram_id: int, text: str):
    try:
        await bot.send_message(telegram_id, text)
    except Exception as e:
        logger.warning(f"Cannot notify user {telegram_id}: {e}")


@router.callback_query(AdminCbFilter(), F.data.startswith("admin_app_take_"))
async def admin_take_app(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    app_id = int(callback.data.replace("admin_app_take_", ""))
    app = await update_stylist_application_status(app_id, "in_progress")
    if not app:
        await callback.message.answer("❌ Заявка не найдена.")
        return
    await _notify_user(
        bot, app.telegram_id,
        "👨‍🎨 Ваш разбор уже находится в работе.\n\n"
        "Стилист приступил к изучению вашего запроса."
    )
    await callback.message.edit_text(
        f"✅ Статус заявки #{app.id} изменён на «in_progress».\n"
        f"Пользователь уведомлён.",
        reply_markup=admin_menu_keyboard(),
    )


@router.callback_query(AdminCbFilter(), F.data.startswith("admin_app_complete_"))
async def admin_complete_app(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    app_id = int(callback.data.replace("admin_app_complete_", ""))
    app = await update_stylist_application_status(app_id, "completed")
    if not app:
        await callback.message.answer("❌ Заявка не найдена.")
        return
    await _notify_user(
        bot, app.telegram_id,
        "✅ Ваш персональный разбор готов.\n\n"
        "Стилист скоро свяжется с вами или уже отправил рекомендации."
    )
    await callback.message.edit_text(
        f"✅ Статус заявки #{app.id} изменён на «completed».\n"
        f"Пользователь уведомлён.",
        reply_markup=admin_menu_keyboard(),
    )


@router.callback_query(AdminCbFilter(), F.data.startswith("admin_app_delete_"))
async def admin_delete_app(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    app_id = int(callback.data.replace("admin_app_delete_", ""))
    app = await get_stylist_application(app_id)
    if not app:
        await callback.message.answer("❌ Заявка не найдена.")
        return
    app = await update_stylist_application_status(app_id, "deleted")
    await callback.message.edit_text(
        f"🗑 Заявка #{app.id} удалена.",
        reply_markup=admin_menu_keyboard(),
    )


# ──────────────────────────────────────────────
# Статистика
# ──────────────────────────────────────────────

@router.callback_query(AdminCbFilter(), F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    await callback.answer()
    total_users = await get_total_users()
    total_payments = await get_total_payments()
    total_apps = await get_total_applications()
    pending_apps = await get_applications_count_by_status("pending")
    completed_apps = await get_applications_count_by_status("completed")
    active_subs = await get_active_subscriptions_count()

    text = (
        "📊 Статистика\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"💳 Всего оплат: {total_payments}\n"
        f"📋 Всего заявок: {total_apps}\n"
        f"⏳ Pending заявок: {pending_apps}\n"
        f"✅ Completed заявок: {completed_apps}\n"
        f"🤖 Активных ИИ-Стилист PRO: {active_subs}"
    )
    await callback.message.edit_text(text, reply_markup=admin_menu_keyboard())


# ──────────────────────────────────────────────
# Пользователи
# ──────────────────────────────────────────────

@router.callback_query(AdminCbFilter(), F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    await callback.answer()
    total_users = await get_total_users()
    recent = await get_recent_users(5)

    text = f"👥 Пользователи\n\nВсего: {total_users}\n\nПоследние регистрации:\n"
    for u in recent:
        date = u.created_at.strftime("%d.%m.%Y %H:%M") if u.created_at else "—"
        name = u.first_name or "—"
        username = f"@{u.username}" if u.username else "—"
        text += f"  🆔 {u.telegram_id} | {name} | {username} | {date}\n"
    text += "\n🔍 Поиск: отправьте User ID в ответ на это сообщение."

    await callback.message.edit_text(text, reply_markup=admin_menu_keyboard())


@router.message(Command("find_user"), AdminFilter())
async def admin_find_user(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /find_user <telegram_id>")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("❌ Некорректный ID.")
        return
    from bot.db.queries import get_user
    user = await get_user(uid)
    if not user:
        await message.answer("❌ Пользователь не найден.")
        return
    created = user.created_at.strftime("%d.%m.%Y %H:%M") if user.created_at else "—"
    updated = user.updated_at.strftime("%d.%m.%Y %H:%M") if user.updated_at else "—"
    text = (
        f"👤 Пользователь\n\n"
        f"🆔 Telegram ID: {user.telegram_id}\n"
        f"📎 Username: @{user.username or '—'}\n"
        f"👤 Имя: {user.first_name or '—'}\n"
        f"📝 Статус: {user.status}\n"
        f"💰 Кредиты: {user.credits or 0}\n"
        f"👑 Godmode: {'да' if user.godmode else 'нет'}\n"
        f"🔓 Бесплатный использован: {'да' if user.free_used else 'нет'}\n"
        f"🤖 Стилист PRO до: {user.stylist_access_until.strftime('%d.%m.%Y') if user.stylist_access_until else '—'}\n"
        f"💳 Оплата: {user.payment_method or '—'} | {user.payment_amount or '—'}₽\n"
        f"📅 Создан: {created}\n"
        f"📅 Обновлён: {updated}"
    )
    await message.answer(text)


# ──────────────────────────────────────────────
# Godmode
# ──────────────────────────────────────────────


@router.callback_query(AdminCbFilter(), F.data == "admin_godmode")
async def admin_godmode_info(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminState.godmode_waiting)
    await callback.message.edit_text(
        "👑 *Godmode*\n\n"
        "Когда godmode включён — пользователю всё бесплатно.\n"
        "Кредиты не тратятся, доступ к стилисту PRO открыт.\n\n"
        "Отправь *Telegram ID* пользователя:",
        parse_mode="Markdown",
        reply_markup=admin_godmode_keyboard(),
    )


@router.message(AdminFilter(), AdminState.godmode_waiting, F.text.regex(r"^\d+$"))
async def admin_godmode_process(message: Message, state: FSMContext):
    uid = int(message.text.strip())
    user = await get_user(uid)
    if not user:
        await message.answer("❌ Пользователь не найден.")
        await state.clear()
        return
    new_state = not user.godmode
    await set_godmode(uid, new_state)
    status = "✅ Включён" if new_state else "❌ Выключен"
    await message.answer(
        f"👑 Godmode для пользователя {uid} ({user.first_name or '—'}):\n"
        f"Статус: {status}"
    )
    await state.clear()


@router.message(AdminFilter(), AdminState.godmode_waiting)
async def admin_godmode_invalid(message: Message, state: FSMContext):
    await message.answer("❌ Отправь только числовой ID пользователя.")
    await state.clear()
    await message.answer(
        "🛠 Админ-панель\n\nВыберите раздел:",
        reply_markup=admin_menu_keyboard(),
    )
