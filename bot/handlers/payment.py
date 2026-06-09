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
from bot.utils.ai_analysis import full_report
from bot.handlers.photos import save_report_file
from bot.texts.result import FULL_REPORT_HEADER, FULL_REPORT_FOOTER

router = Router()


@router.callback_query(F.data.startswith("buy_"), StateFilter(UserState.credits_menu))
async def buy_package(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    idx_map = {"buy_1": 0, "buy_5": 1, "buy_100": 2}
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


@router.callback_query(F.data == "buy_stylist", StateFilter(UserState.credits_menu))
async def buy_stylist(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    pkg = config.STYLIST_PACKAGE
    await state.update_data(package_index=3, is_stylist=True)
    await state.set_state(UserState.payment_method)
    await callback.message.answer(
        f"Выбери способ оплаты:\n\n{pkg['label']}",
        reply_markup=payment_choice_keyboard(3),
    )


@router.callback_query(F.data.startswith("pay_stars_"), StateFilter(UserState.payment_method))
async def pay_stars(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    idx = int(callback.data.split("_")[2])
    if idx == 3:
        pkg = config.STYLIST_PACKAGE
        title = "Персональный анализ от стилиста"
    else:
        pkg = config.CREDIT_PACKAGES[idx]
        title = "Пакет кредитов"
    prices = [LabeledPrice(label=pkg["label"], amount=pkg["stars"])]
    payload_prefix = "stylist" if idx == 3 else "credits"
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=title,
        description=pkg["label"],
        payload=f"{payload_prefix}_{callback.from_user.id}_{int(time.time())}",
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
    if idx == 3:
        pkg = config.STYLIST_PACKAGE
        title = "Персональный анализ от стилиста"
    else:
        pkg = config.CREDIT_PACKAGES[idx]
        title = "Пакет кредитов"
    prices = [LabeledPrice(label=pkg["label"], amount=pkg["rub"] * 100)]
    payload_prefix = "stylist" if idx == 3 else "credits"
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=title,
        description=pkg["label"],
        payload=f"{payload_prefix}_{callback.from_user.id}_{int(time.time())}",
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
    payment = message.successful_payment
    method = "stars" if payment.currency == "XTR" else "card"

    if data.get("is_stylist"):
        pkg = config.STYLIST_PACKAGE
        await update_user(
            telegram_id=message.from_user.id,
            payment_method=method,
            payment_id=payment.provider_payment_charge_id or payment.telegram_payment_charge_id,
            payment_amount=payment.total_amount / (1 if payment.currency == "XTR" else 100),
        )
        currency = "★" if payment.currency == "XTR" else "₽"
        amount = pkg["stars"] if payment.currency == "XTR" else pkg["rub"]
        await message.answer(
            f"✅ Оплачено {amount} {currency}\n\n"
            f"👔 Готовлю персональный разбор от стилиста..."
        )
        name = data.get("name", "")
        age = data.get("age", 25)
        goals = data.get("selected_goals", [])
        photo_ids = data.get("photo_ids", [])
        dialogue_msgs = data.get("dialogue_messages", [])
        report = await full_report(
            message.bot, photo_ids, name, age, goals, dialogue_history=dialogue_msgs
        )
        await update_user(message.from_user.id, result_text=report, status="completed")
        await save_report_file(message.from_user.id, report)
        full = FULL_REPORT_HEADER.format(name=name) + "\n" + report + "\n" + FULL_REPORT_FOOTER
        await state.set_state(UserState.result)
        await message.answer(full, reply_markup=after_report_keyboard())
        await save_order_file(message.from_user.id, pkg, 0)
        return

    pkg = config.CREDIT_PACKAGES[idx]
    credits = pkg["credits"]
    user = await add_credits(message.from_user.id, credits)
    balance = user.credits if user else 0
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
    is_stylist = pkg.get("is_stylist", False)
    title = "Персональный анализ от стилиста" if is_stylist else "Покупка кредитов"
    text = (
        f"{title}\n"
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
