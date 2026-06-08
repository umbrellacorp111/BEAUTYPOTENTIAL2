import time
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from bot.config import config
from bot.states.user_states import UserState
from bot.texts.payment import *
from bot.keyboards.inline import *
from bot.db.queries import update_user, get_user

router = Router()


@router.callback_query(F.data == "pay_stars", StateFilter(UserState.payment_method))
async def pay_stars(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    data = await state.get_data()
    prices = [LabeledPrice(label="Разбор внешности", amount=config.STARS_PRICE)]
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Персональный разбор внешности",
        description="Анализ внешности по 12 параметрам + план действий",
        payload=f"user_{callback.from_user.id}_{int(time.time())}",
        provider_token="",
        currency="XTR",
        prices=prices,
    )
    await state.set_state(UserState.awaiting_payment)
    await state.update_data(payment_method="stars")
    await update_user(callback.from_user.id, status="awaiting_payment", payment_method="stars")


@router.callback_query(F.data == "pay_yukassa", StateFilter(UserState.payment_method))
async def pay_yukassa(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    prices = [LabeledPrice(label="Разбор внешности", amount=config.RUB_PRICE * 100)]
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Персональный разбор внешности",
        description="Анализ внешности по 12 параметрам + план действий",
        payload=f"user_{callback.from_user.id}_{int(time.time())}",
        provider_token=config.YUKASSA_PROVIDER_TOKEN,
        currency="RUB",
        prices=prices,
    )


@router.callback_query(F.data == "pay_back", StateFilter(UserState.payment_method))
async def pay_back(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    from bot.texts.sales import SALES_TEXT
    await callback.message.answer(SALES_TEXT)
    await callback.message.answer(
        "Выбери способ оплаты:", reply_markup=payment_choice_keyboard()
    )


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_q: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


@router.message(F.successful_payment)
async def payment_success(message: Message, state: FSMContext):
    await state.set_state(UserState.paid)
    payment = message.successful_payment
    method = "stars" if payment.currency == "XTR" else "yukassa"
    amount = payment.total_amount / (1 if payment.currency == "XTR" else 100)

    await update_user(
        telegram_id=message.from_user.id,
        status="paid",
        payment_method=method,
        payment_id=payment.provider_payment_charge_id or payment.telegram_payment_charge_id,
        payment_amount=amount,
    )

    data = await state.get_data()
    name = data.get("name", "")

    await message.answer(
        PAYMENT_SUCCESS_TEXT.format(name=name, support=config.SUPPORT_USERNAME)
    )

    user = await get_user(message.from_user.id)
    await notify_admin(message.bot, user)


async def notify_admin(bot: Bot, user):
    chat_id = config.ADMIN_CHAT_ID
    if not chat_id:
        return
    goals_str = ", ".join(user.goals) if user.goals else "—"
    text = (
        f"🆕 НОВАЯ ЗАЯВКА #{user.id}\n\n"
        f"👤 {user.name} | {user.age} лет\n"
        f"🎯 Цели: {goals_str}\n"
        f"💳 Оплачено: {user.payment_amount}₽\n\n"
        f"📸 Фото:"
    )
    await bot.send_message(chat_id, text)
    if user.photo_ids:
        media = []
        for i, fid in enumerate(user.photo_ids):
            from aiogram.types import InputMediaPhoto
            media.append(InputMediaPhoto(media=fid))
            if len(media) == 10:
                break
        if media:
            await bot.send_media_group(chat_id, media)
    from bot.keyboards.inline import admin_application_keyboard
    await bot.send_message(
        chat_id,
        f"👇 Заявка #{user.id}",
        reply_markup=admin_application_keyboard(user.id),
    )


@router.callback_query(F.data == "yukassa_check")
async def yukassa_check(callback: CallbackQuery):
    await callback.answer("Проверка платежа...", show_alert=True)
    user = await get_user(callback.from_user.id)
    if user and user.status == "paid":
        await callback.message.answer("✅ Платёж уже подтверждён!")
    else:
        from bot.texts.payment import AWAITING_RESULT_TEXT
        await callback.message.answer("⏳ Платёж ещё обрабатывается. Попробуй через минуту.")


@router.message(StateFilter(UserState.paid, UserState.awaiting_payment))
async def awaiting_message(message: Message):
    from bot.texts.payment import AWAITING_RESULT_TEXT
    await message.answer(AWAITING_RESULT_TEXT)
