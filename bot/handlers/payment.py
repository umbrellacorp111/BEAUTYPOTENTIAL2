import time
import os
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from bot.config import config
from bot.states.user_states import UserState
from bot.texts.payment import *
from bot.texts.sales import CREDIT_HEADER
from bot.keyboards.inline import *
from bot.db.queries import update_user, get_user, add_credits

router = Router()


@router.callback_query(F.data.startswith("buy_"), StateFilter(UserState.credits_menu))
async def buy_package(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    idx_map = {"buy_1": 0, "buy_5": 1, "buy_15": 2}
    idx = idx_map.get(callback.data)
    if idx is None:
        return
    pkg = config.CREDIT_PACKAGES[idx]
    await state.update_data(package_index=idx)
    await state.set_state(UserState.payment_method)
    await callback.message.answer(
        f"Выбери способ оплаты:\n\n{pkg['label']}",
        reply_markup=payment_choice_keyboard(idx),
    )


@router.callback_query(F.data.startswith("pay_stars_"), StateFilter(UserState.payment_method))
async def pay_stars(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    idx = int(callback.data.split("_")[2])
    pkg = config.CREDIT_PACKAGES[idx]
    prices = [LabeledPrice(label=pkg["label"], amount=pkg["stars"])]
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Пакет кредитов",
        description=pkg["label"],
        payload=f"credits_{callback.from_user.id}_{int(time.time())}",
        provider_token="",
        currency="XTR",
        prices=prices,
    )
    await state.set_state(UserState.awaiting_payment)
    await state.update_data(payment_method="stars", package_index=idx)


@router.callback_query(F.data.startswith("pay_card_"), StateFilter(UserState.payment_method))
async def pay_card(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    idx = int(callback.data.split("_")[2])
    pkg = config.CREDIT_PACKAGES[idx]
    prices = [LabeledPrice(label=pkg["label"], amount=pkg["rub"] * 100)]
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Пакет кредитов",
        description=pkg["label"],
        payload=f"credits_{callback.from_user.id}_{int(time.time())}",
        provider_token=config.YUKASSA_PROVIDER_TOKEN,
        currency="RUB",
        prices=prices,
    )
    await state.set_state(UserState.awaiting_payment)
    await state.update_data(payment_method="card", package_index=idx)


@router.callback_query(F.data == "pay_back", StateFilter(UserState.payment_method))
async def pay_back(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = await get_user(callback.from_user.id)
    balance = user.credits if user else 0
    await state.set_state(UserState.credits_menu)
    await callback.message.answer(
        CREDIT_HEADER,
        reply_markup=credit_packages_keyboard(balance),
    )


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_q: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


@router.message(F.successful_payment)
async def payment_success(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("package_index", 0)
    pkg = config.CREDIT_PACKAGES[idx]
    credits = pkg["credits"]
    user = await add_credits(message.from_user.id, credits)
    balance = user.credits if user else 0
    payment = message.successful_payment
    method = "stars" if payment.currency == "XTR" else "card"
    await update_user(
        telegram_id=message.from_user.id,
        payment_method=method,
        payment_id=payment.provider_payment_charge_id or payment.telegram_payment_charge_id,
        payment_amount=payment.total_amount / (1 if payment.currency == "XTR" else 100),
    )
    if payment.currency == "XTR":
        await message.answer(
            PAYMENT_SUCCESS_STARS.format(stars=pkg["stars"], credits=credits, balance=balance)
        )
    else:
        await message.answer(
            PAYMENT_SUCCESS_RUB.format(rub=pkg["rub"], credits=credits, balance=balance)
        )
    if balance > 0 and await state.get_state() not in (UserState.result,):
        await state.set_state(UserState.credits_menu)
        from bot.texts.payment import USE_CREDIT_PROMPT
        await message.answer(
            USE_CREDIT_PROMPT.format(balance=balance),
            reply_markup=use_credit_keyboard(),
        )
    await save_order_file(message.from_user.id, pkg, credits)


async def save_order_file(telegram_id: int, pkg: dict, credits: int):
    orders_dir = os.path.join(config.DATA_DIR, "orders")
    os.makedirs(orders_dir, exist_ok=True)
    text = (
        f"Покупка кредитов\n"
        f"{'='*40}\n"
        f"Дата: {datetime.now()}\n"
        f"Telegram ID: {telegram_id}\n"
        f"Пакет: {pkg['label']}\n"
        f"Кредитов: {credits}\n"
        f"Сумма: {pkg.get('rub', pkg.get('stars'))}{'₽' if 'rub' in pkg else ' ★'}\n"
    )
    filepath = os.path.join(orders_dir, f"purchase_{telegram_id}_{int(time.time())}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
