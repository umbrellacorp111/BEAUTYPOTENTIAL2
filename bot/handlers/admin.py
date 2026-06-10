import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.filters.admin import AdminFilter
from bot.keyboards.inline import *
from bot.db.queries import get_all_users, get_user_by_id, get_status_counts, get_stylist_applications
from bot.config import config

router = Router()


@router.message(Command("admin"), AdminFilter())
async def admin_start(message: Message):
    counts = await get_status_counts()
    text = "🔐 Админ-панель\n\n"
    for k, v in counts.items():
        text += f"{k}: {v}\n"
    text += f"\nЗаказы: {config.DATA_DIR}/orders/"
    text += f"\nОтчёты: {config.DATA_DIR}/reports/"
    await message.answer(text)


@router.message(Command("orders"), AdminFilter())
async def admin_orders(message: Message):
    orders_dir = os.path.join(config.DATA_DIR, "orders")
    if not os.path.isdir(orders_dir):
        await message.answer("Папка orders не найдена.")
        return
    files = sorted(os.listdir(orders_dir), reverse=True)[:10]
    if not files:
        await message.answer("Нет заказов.")
        return
    for fname in files:
        fpath = os.path.join(orders_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        await message.answer(f"<b>{fname}</b>\n<pre>{content}</pre>")


@router.message(Command("stylist_apps"), AdminFilter())
async def admin_stylist_apps(message: Message):
    apps = await get_stylist_applications()
    if not apps:
        await message.answer("Нет заявок на разбор от стилиста.")
        return
    for app in apps:
        photo_status = "✅ есть" if app.last_photo_id else "❌ нет"
        text = (
            f"🧾 Заявка #{app.id}\n"
            f"👤 {app.first_name or '—'} (@{app.username or '—'})\n"
            f"📅 {app.payment_date.strftime('%d.%m.%Y %H:%M')}\n"
            f"📸 Фото: {photo_status}\n"
            f"📋 Статус: {app.status}\n"
            f"🆔 {app.telegram_id}"
        )
        await message.answer(text)
