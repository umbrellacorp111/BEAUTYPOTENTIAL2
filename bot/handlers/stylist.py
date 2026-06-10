import uuid
import time
import logging
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from yookassa import Payment
from bot.config import config
from bot.states.user_states import UserState
from bot.keyboards.inline import (
    stylist_pro_info_keyboard, stylist_renew_keyboard, stylist_chat_keyboard,
)
from bot.db.queries import get_user, update_user, has_stylist_access, increment_stylist_free_used
from bot.texts.stylist import *
from bot.utils.ai_stylist import stylist_chat as ai_stylist_chat
from bot.utils.ai_analysis import _photo_to_base64

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "stylist_pro_info")
async def stylist_pro_info(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = await get_user(callback.from_user.id)
    if user and (user.godmode or (user.stylist_access_until and user.stylist_access_until > datetime.utcnow())):
        await state.set_state(UserState.stylist_chat)
        await state.update_data(stylist_messages=[])
        until_str = user.stylist_access_until.strftime("%d.%m.%Y %H:%M UTC")
        await callback.message.answer(
            STYLIST_PRO_ACTIVE.format(until=until_str) + STYLIST_PRO_WELCOME,
            reply_markup=stylist_chat_keyboard(),
        )
    elif user and (user.stylist_free_used or 0) < config.STYLIST_FREE_TRIAL_MESSAGES:
        used = user.stylist_free_used or 0
        remaining = config.STYLIST_FREE_TRIAL_MESSAGES - used
        await state.set_state(UserState.stylist_chat)
        await state.update_data(stylist_messages=[])
        await callback.message.answer(
            STYLIST_PRO_TRIAL.format(used=used, remaining=remaining),
            reply_markup=stylist_chat_keyboard(),
        )
    else:
        await callback.message.answer(
            STYLIST_PRO_INFO,
            reply_markup=stylist_pro_info_keyboard(),
        )


@router.callback_query(F.data == "stylist_pro_trial_start")
async def stylist_pro_trial_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("❌ Пользователь не найден.")
        return
    if (user.stylist_free_used or 0) >= config.STYLIST_FREE_TRIAL_MESSAGES:
        await callback.message.answer(
            STYLIST_PRO_TRIAL_EXHAUSTED,
            reply_markup=stylist_renew_keyboard(),
        )
        return
    used = user.stylist_free_used or 0
    remaining = config.STYLIST_FREE_TRIAL_MESSAGES - used
    await state.set_state(UserState.stylist_chat)
    await state.update_data(stylist_messages=[])
    await callback.message.answer(
        STYLIST_PRO_TRIAL.format(used=used, remaining=remaining),
        reply_markup=stylist_chat_keyboard(),
    )


@router.callback_query(F.data == "stylist_pro_buy")
async def stylist_pro_buy(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    pkg = config.STYLIST_PRO_PACKAGE

    try:
        idempotence_key = str(uuid.uuid4())
        payment_obj = Payment.create({
            "amount": {
                "value": f"{pkg['rub']}.00",
                "currency": "RUB",
            },
            "confirmation": {
                "type": "redirect",
                "return_url": config.YUKASSA_RETURN_URL,
            },
            "capture": True,
            "description": pkg["label"],
            "metadata": {
                "telegram_id": str(callback.from_user.id),
                "payload": f"stylist_pro_{callback.from_user.id}_{int(time.time())}",
            },
        }, idempotence_key)

        payment_id = payment_obj.id
        pay_url = payment_obj.confirmation.confirmation_url

        await state.update_data(stylist_payment_id=payment_id)

        rub = config.STYLIST_PRO_PACKAGE["rub"]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"💳 Оплатить {rub}₽", url=pay_url)],
            [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"stylist_check_{payment_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="stylist_pro_info")],
        ])
        await callback.message.answer(
            "💳 *Оплата ИИ-Стилист PRO*\n\n"
            "Нажми кнопку ниже для оплаты.\n"
            "После оплаты нажми «Я оплатил».",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Stylist PRO payment error: {e}", exc_info=True)
        await callback.message.answer("❌ Ошибка создания платежа. Попробуй позже.")


@router.callback_query(F.data.startswith("stylist_check_"))
async def stylist_pro_check_payment(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer("Проверяю оплату...")
    payment_id = callback.data.replace("stylist_check_", "")

    try:
        payment_obj = Payment.find_one(payment_id)
        if payment_obj.status == "succeeded":
            pkg = config.STYLIST_PRO_PACKAGE
            until = datetime.utcnow() + timedelta(days=pkg["days"])
            await update_user(callback.from_user.id, stylist_access_until=until)

            until_str = until.strftime("%d.%m.%Y %H:%M UTC")
            await callback.message.answer(
                STYLIST_PRO_PURCHASED.format(until=until_str),
                reply_markup=stylist_chat_keyboard(),
            )
            await callback.message.answer(STYLIST_PRO_WELCOME)
            await state.set_state(UserState.stylist_chat)
            await state.update_data(stylist_messages=[])
        elif payment_obj.status == "pending":
            await callback.message.answer("⏳ Оплата ещё не поступила. Подожди и попробуй снова.")
        else:
            await callback.message.answer("❌ Оплата не прошла. Попробуй создать новый платёж.")
    except Exception as e:
        logger.error(f"Stylist check error: {e}", exc_info=True)
        await callback.message.answer("❌ Ошибка проверки. Попробуй позже.")


async def _check_stylist_access(user) -> tuple[bool, str | None]:
    """Returns (has_access, blocked_message). If blocked_message is None, access granted."""
    if not user:
        return False, STYLIST_PRO_EXPIRED
    if user.godmode:
        return True, None
    if user.stylist_access_until and user.stylist_access_until > datetime.utcnow():
        return True, None
    used = user.stylist_free_used or 0
    if used < config.STYLIST_FREE_TRIAL_MESSAGES:
        return True, None
    return False, STYLIST_PRO_TRIAL_EXHAUSTED


@router.message(StateFilter(UserState.stylist_chat), F.text)
async def stylist_chat_text(message: Message, state: FSMContext, bot: Bot):
    user = await get_user(message.from_user.id)
    has_access, blocked_msg = await _check_stylist_access(user)
    if not has_access:
        if user:
            await update_user(message.from_user.id, stylist_access_until=None)
        await state.clear()
        await message.answer(blocked_msg, reply_markup=stylist_renew_keyboard())
        return

    data = await state.get_data()
    history = data.get("stylist_messages", [])
    history.append({"role": "user", "content": message.text})

    await message.answer("🤔 Думаю...")
    reply = await ai_stylist_chat(history)
    history.append({"role": "assistant", "content": reply})
    await state.update_data(stylist_messages=history)
    await message.answer(reply, reply_markup=stylist_chat_keyboard())

    if not user.godmode and not (user.stylist_access_until and user.stylist_access_until > datetime.utcnow()):
        await increment_stylist_free_used(message.from_user.id)


@router.message(StateFilter(UserState.stylist_chat), F.photo)
async def stylist_chat_photo(message: Message, state: FSMContext, bot: Bot):
    user = await get_user(message.from_user.id)
    has_access, blocked_msg = await _check_stylist_access(user)
    if not has_access:
        if user:
            await update_user(message.from_user.id, stylist_access_until=None)
        await state.clear()
        await message.answer(blocked_msg, reply_markup=stylist_renew_keyboard())
        return

    data = await state.get_data()
    history = data.get("stylist_messages", [])
    caption = message.caption or "Проанализируй этот образ"
    history.append({"role": "user", "content": caption})

    file_id = message.photo[-1].file_id
    photo_b64 = None
    try:
        photo_b64 = await _photo_to_base64(bot, file_id)
        logger.info(f"Stylist photo downloaded successfully, file_id={file_id}")
    except Exception as e:
        logger.error(f"Stylist photo download error: {e}", exc_info=True)
        await message.answer("⚠️ Не удалось загрузить фото. Попробуй отправить ещё раз.")
        return

    await message.answer("🤔 Анализирую образ...")
    reply = await ai_stylist_chat(history, photo_b64)
    history.append({"role": "assistant", "content": reply})
    await state.update_data(stylist_messages=history)
    await message.answer(reply, reply_markup=stylist_chat_keyboard())

    if not user.godmode and not (user.stylist_access_until and user.stylist_access_until > datetime.utcnow()):
        await increment_stylist_free_used(message.from_user.id)
