from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from bot.filters.admin import AdminFilter
from bot.keyboards.inline import *
from bot.db.queries import get_all_users, get_users_by_status, get_status_counts, get_user_by_id, get_user, update_user
from bot.config import config

router = Router()


@router.message(Command("admin"), AdminFilter())
async def admin_start(message: Message):
    counts = await get_status_counts()
    text = (
        "🔐 Админ-панель\n\n"
        f"📊 Заявок всего: {counts.get('total', 0)}\n"
        f"🆕 Новых: {counts.get('new', 0)}\n"
        f"⏳ Ожидают оплату: {counts.get('awaiting_payment', 0)}\n"
        f"✅ Оплачено: {counts.get('paid', 0)}\n"
        f"🔧 В работе: {counts.get('in_progress', 0)}\n"
        f"✅ Завершено: {counts.get('completed', 0)}"
    )
    await message.answer(text, reply_markup=admin_main_keyboard())


@router.callback_query(F.data == "admin_back", AdminFilter())
async def admin_back(callback: CallbackQuery):
    await callback.answer()
    await admin_start(callback.message)


@router.callback_query(F.data == "admin_stats", AdminFilter())
async def admin_stats(callback: CallbackQuery):
    await callback.answer()
    await admin_start(callback.message)


@router.callback_query(F.data == "admin_list", AdminFilter())
async def admin_list(callback: CallbackQuery):
    await callback.answer()
    users = await get_all_users()
    if not users:
        await callback.message.answer("Нет заявок.", reply_markup=admin_back_keyboard())
        return
    status_emoji = {
        "new": "🆕", "awaiting_payment": "⏳", "paid": "✅",
        "in_progress": "🔧", "completed": "✅", "cancelled": "❌",
    }
    lines = ["📋 Все заявки:\n"]
    builder = InlineKeyboardBuilder()
    for u in users[:20]:
        emoji = status_emoji.get(u.status, "❓")
        lines.append(f"{emoji} #{u.id} — {u.name or '—'} ({u.age or '—'}) — {u.status}")
        builder.button(text=f"{emoji} #{u.id} {u.name or '—'}", callback_data=f"admin_open_{u.id}")
    builder.button(text="🔙 Назад", callback_data="admin_back")
    builder.adjust(1)
    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "..."
    await callback.message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "admin_new", AdminFilter())
async def admin_new(callback: CallbackQuery):
    await callback.answer()
    users = await get_users_by_status("paid")
    if not users:
        await callback.message.answer("Нет оплаченных заявок.", reply_markup=admin_back_keyboard())
        return
    builder = InlineKeyboardBuilder()
    lines = ["🆕 Оплаченные заявки (ждут обработки):\n"]
    for u in users[:20]:
        lines.append(f"#{u.id} — {u.name or '—'} ({u.age or '—'})")
        builder.button(text=f"#{u.id} {u.name or '—'}", callback_data=f"admin_open_{u.id}")
    builder.button(text="🔙 Назад", callback_data="admin_back")
    builder.adjust(1)
    await callback.message.answer("\n".join(lines), reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("admin_open_"), AdminFilter())
async def admin_open(callback: CallbackQuery):
    await callback.answer()
    user_id = int(callback.data.split("_")[2])
    user = await get_user_by_id(user_id)
    if not user:
        await callback.message.answer("Заявка не найдена.")
        return
    goals_str = ", ".join(user.goals) if user.goals else "—"
    status_emoji = {
        "new": "🆕", "awaiting_payment": "⏳", "paid": "✅",
        "in_progress": "🔧", "completed": "✅", "cancelled": "❌",
    }
    emoji = status_emoji.get(user.status, "❓")
    text = (
        f"📋 Заявка #{user.id}\n\n"
        f"👤 Имя: {user.name or '—'}\n"
        f"🎂 Возраст: {user.age or '—'}\n"
        f"🎯 Цели: {goals_str}\n"
        f"📸 Фото: {len(user.photo_ids) if user.photo_ids else 0} шт.\n"
        f"🏷 Статус: {emoji} {user.status}\n"
        f"💳 Оплата: {user.payment_method or '—'} | {user.payment_amount or '—'}₽\n"
        f"📅 Создана: {user.created_at}\n"
        f"📅 Обновлена: {user.updated_at}"
    )
    await callback.message.answer(text, reply_markup=admin_application_keyboard(user.id))


@router.callback_query(F.data.startswith("admin_show_photo_"), AdminFilter())
async def admin_show_photo(callback: CallbackQuery):
    await callback.answer()
    user_id = int(callback.data.split("_")[3])
    user = await get_user_by_id(user_id)
    if not user or not user.photo_ids:
        await callback.message.answer("Нет фото.")
        return
    from aiogram.types import InputMediaPhoto
    media = []
    for fid in user.photo_ids:
        media.append(InputMediaPhoto(media=fid))
        if len(media) == 10:
            break
    if media:
        await callback.message.answer_media_group(media)
    else:
        await callback.message.answer("Нет фото.")


@router.callback_query(F.data.startswith("admin_work_"), AdminFilter())
async def admin_work(callback: CallbackQuery):
    await callback.answer()
    user_id = int(callback.data.split("_")[2])
    await update_user_by_id_direct(user_id, status="in_progress")
    await callback.message.answer(f"Статус заявки #{user_id} изменён на «В работе».")


@router.callback_query(F.data.startswith("admin_cancel_"), AdminFilter())
async def admin_cancel_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = int(callback.data.split("_")[2])
    await state.set_state("admin_cancel_reason")
    await state.update_data(cancel_user_id=user_id)
    await callback.message.answer(f"Напиши причину отмены для заявки #{user_id}:")


@router.message(StateFilter("admin_cancel_reason"), AdminFilter())
async def admin_cancel_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("cancel_user_id")
    if not user_id:
        return
    reason = message.text.strip()
    user = await get_user_by_id(user_id)
    await update_user_by_id_direct(user_id, status="cancelled")
    if user:
        await message.bot.send_message(
            user.telegram_id,
            f"❌ К сожалению, твоя заявка #{user.id} отменена.\nПричина: {reason}",
        )
    await message.answer(f"Заявка #{user_id} отменена. Пользователь уведомлён.")
    await state.clear()


@router.callback_query(F.data.startswith("admin_result_"), AdminFilter())
async def admin_result_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = int(callback.data.split("_")[2])
    await state.set_state("admin_result_input")
    await state.update_data(result_user_id=user_id)
    await callback.message.answer(
        f"Отправь результат для заявки #{user_id}.\n\n"
        f"Можно отправить:\n"
        f"1. Текстовое сообщение (разбор)\n"
        f"2. PDF-файл (опционально)\n"
        f"3. Или и то, и другое"
    )


@router.message(StateFilter("admin_result_input"), AdminFilter())
async def admin_result_receive(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("result_user_id")
    if not user_id:
        return
    user = await get_user_by_id(user_id)
    if not user:
        await message.answer("Заявка не найдена.")
        return

    result_text = message.text or message.caption or ""
    result_file_id = None
    if message.document:
        result_file_id = message.document.file_id
    elif message.photo:
        result_file_id = message.photo[-1].file_id

    await update_user(
        telegram_id=user.telegram_id,
        result_text=result_text,
        result_file_id=result_file_id,
        status="completed",
    )

    await message.answer(f"✅ Результат для заявки #{user_id} отправлен пользователю.\nСтатус: Завершена ✅")

    from bot.handlers.result import send_result
    await send_result(message, user)

    await state.clear()


async def update_user_by_id_direct(user_id: int, **kwargs):
    from sqlalchemy import update
    from bot.db.session import async_session
    from bot.db.models import User
    async with async_session() as session:
        stmt = update(User).where(User.id == user_id).values(**kwargs)
        await session.execute(stmt)
        await session.commit()
