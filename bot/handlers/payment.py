import time
import os
import uuid
import logging
from datetime import datetime
from aiohttp import web
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from yookassa import Configuration, Payment
from bot.config import config
from bot.states.user_states import UserState
from bot.texts.payment import *
from bot.texts.sales import CREDIT_HEADER
from bot.keyboards.inline import *
from bot.db.queries import (
    update_user, get_user, add_credits,
    create_pending_payment, get_pending_payment,
    complete_pending_payment, fail_pending_payment,
    create_stylist_application,
)
from bot.utils.ai_analysis import full_report
from bot.handlers.photos import save_report_file
from bot.texts.result import FULL_REPORT_HEADER, FULL_REPORT_FOOTER

logger = logging.getLogger(__name__)
router = Router()

# Настройка ЮКассы
Configuration.account_id = config.YUKASSA_SHOP_ID
Configuration.secret_key = config.YUKASSA_SECRET_KEY

# pending_payments dict УДАЛЁН — данные хранятся в таблице pending_payments (БД)


def _create_yukassa_payment(pkg: dict, payload_prefix: str, telegram_id: int) -> tuple[str, str]:
    """Создаёт платёж в ЮКассе, возвращает (payment_id, confirmation_url)"""
    idempotence_key = str(uuid.uuid4())
    payment = Payment.create({
        "amount": {
            "value": f"{pkg['rub']}.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": config.YUKASSA_RETURN_URL
        },
        "capture": True,
        "description": pkg["label"],
        "metadata": {
            "telegram_id": str(telegram_id),
            "payload": f"{payload_prefix}_{telegram_id}_{int(time.time())}"
        }
    }, idempotence_key)
    return payment.id, payment.confirmation.confirmation_url


@router.callback_query(F.data.in_({"buy_1", "buy_5", "buy_100"}), StateFilter(UserState.credits_menu))
async def buy_package(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    idx_map = {"buy_1": 0, "buy_5": 1, "buy_100": 2}
    idx = idx_map.get(callback.data)
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


@router.callback_query(F.data.startswith("pay_card_"), StateFilter(UserState.payment_method))
async def pay_card(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    idx = int(callback.data.split("_")[2])
    is_stylist = idx == 3
    pkg = config.STYLIST_PACKAGE if is_stylist else config.CREDIT_PACKAGES[idx]
    payload_prefix = "stylist" if is_stylist else "credits"

    try:
        payment_id, pay_url = _create_yukassa_payment(pkg, payload_prefix, callback.from_user.id)
    except Exception as e:
        logger.error(f"ЮКасса ошибка создания платежа: {e}", exc_info=True)
        await callback.message.answer("❌ Ошибка создания платежа. Попробуй позже.")
        return

    # Сохраняем данные платежа в БД (переживёт рестарт контейнера)
    state_data = await state.get_data()
    await create_pending_payment(
        payment_id=payment_id,
        telegram_id=callback.from_user.id,
        package_index=idx,
        is_stylist=is_stylist,
        state_data=state_data,
    )

    # Отправляем кнопку с ссылкой на оплату
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=pay_url)],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_payment_{payment_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="pay_back")],
    ])
    await callback.message.answer(
        f"💳 *{pkg['label']}*\n\n"
        f"Нажми кнопку ниже для оплаты.\n"
        f"После оплаты нажми «Я оплатил» для получения разбора.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(UserState.awaiting_payment)
    await state.update_data(payment_method="card", package_index=idx, payment_id=payment_id)


@router.callback_query(F.data.startswith("check_payment_"), StateFilter(UserState.awaiting_payment))
async def check_payment(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Ручная проверка платежа по нажатию 'Я оплатил'"""
    await callback.answer("Проверяю оплату...")
    payment_id = callback.data.replace("check_payment_", "")

    try:
        payment = Payment.find_one(payment_id)
        if payment.status == "succeeded":
            await callback.message.answer("✅ Оплата подтверждена!")
            # Загружаем данные из БД, а не из памяти
            data = await get_pending_payment(payment_id)
            if data and data.status == "pending":
                await _process_successful_payment(
                    bot=bot,
                    telegram_id=callback.from_user.id,
                    payment_id=payment_id,
                    amount=float(payment.amount.value),
                    package_index=data.package_index,
                    is_stylist=data.is_stylist,
                    state_data=data.state_data,
                    state=state,
                )
            else:
                # Платёж уже обработан (например, вебхуком) — восстанавливаем из БД пользователя
                user = await get_user(callback.from_user.id)
                if user and user.status == "completed" and user.result_text:
                    from bot.texts.result import FULL_REPORT_HEADER, FULL_REPORT_FOOTER
                    name = user.name or ""
                    full = FULL_REPORT_HEADER.format(name=name) + "\n" + user.result_text + "\n" + FULL_REPORT_FOOTER
                    await state.set_state(UserState.result)
                    await callback.message.answer(full, reply_markup=after_report_keyboard())
                else:
                    await callback.message.answer("✅ Платёж уже был обработан.")
        elif payment.status == "pending":
            await callback.message.answer("⏳ Оплата ещё не поступила. Подожди немного и попробуй снова.")
        else:
            await callback.message.answer("❌ Оплата не прошла. Попробуй создать новый платёж.")
    except Exception as e:
        logger.error(f"Ошибка проверки платежа {payment_id}: {e}", exc_info=True)
        await callback.message.answer("❌ Ошибка проверки. Попробуй позже.")


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


@router.callback_query(F.data == "pay_back", StateFilter(UserState.awaiting_payment))
async def pay_back_from_payment(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = await get_user(callback.from_user.id)
    balance = user.credits if user else 0
    await state.set_state(UserState.credits_menu)
    await callback.message.answer(
        CREDIT_HEADER,
        reply_markup=credit_packages_keyboard(balance),
    )


@router.callback_query(F.data == "pay_back")
async def pay_back_fallback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = await get_user(callback.from_user.id)
    balance = user.credits if user else 0
    await state.set_state(UserState.credits_menu)
    await callback.message.answer(
        CREDIT_HEADER,
        reply_markup=credit_packages_keyboard(balance),
    )


async def _process_successful_payment(
    bot: Bot,
    telegram_id: int,
    payment_id: str,
    amount: float,
    package_index: int,
    is_stylist: bool,
    state_data: dict,
    state: FSMContext | None = None,
):
    """Общая логика начисления после успешной оплаты"""
    if is_stylist:
        pkg = config.STYLIST_PACKAGE
        await update_user(
            telegram_id=telegram_id,
            payment_method="card",
            payment_id=payment_id,
            payment_amount=amount,
        )
        user = await get_user(telegram_id)
        photo_ids = state_data.get("photo_ids", [])
        last_photo_id = photo_ids[-1] if photo_ids else None
        analysis_text = state_data.get("free_analysis", {}).get("free_text", "")
        app = await create_stylist_application(
            telegram_id=telegram_id,
            username=user.username if user else None,
            first_name=user.first_name if user else None,
            name=state_data.get("name"),
            age=state_data.get("age"),
            goals=state_data.get("selected_goals", []),
            photo_ids=photo_ids,
            payment_date=datetime.utcnow(),
            last_photo_id=last_photo_id,
            analysis_text=analysis_text,
        )
        from bot.texts.stylist import STYLIST_APPLICATION_USER_NOTIFY, STYLIST_APPLICATION_ADMIN_NOTIFY
        await bot.send_message(
            telegram_id,
            STYLIST_APPLICATION_USER_NOTIFY.format(app_id=app.id),
        )
        await save_order_file(telegram_id, pkg, 0)
        admin_chat_id = config.ADMIN_CHAT_ID
        if admin_chat_id:
            await bot.send_message(
                admin_chat_id,
                STYLIST_APPLICATION_ADMIN_NOTIFY.format(
                    app_id=app.id,
                    first_name=user.first_name if user else "—",
                    user_id=telegram_id,
                    username=user.username if user else "—",
                    payment_date=app.payment_date.strftime("%d.%m.%Y %H:%M"),
                    photo_status="сохранено" if last_photo_id else "отсутствует",
                ),
            )
        await complete_pending_payment(payment_id)
    else:
        pkg = config.CREDIT_PACKAGES[package_index]
        credits = pkg["credits"]
        user = await add_credits(telegram_id, credits)
        balance = user.credits if user else 0
        await update_user(
            telegram_id=telegram_id,
            payment_method="card",
            payment_id=payment_id,
            payment_amount=amount,
        )
        await bot.send_message(
            telegram_id,
            PAYMENT_SUCCESS_RUB.format(rub=pkg["rub"], credits=credits, balance=balance)
        )
        if balance > 0:
            if state:
                await state.set_state(UserState.credits_menu)
            from bot.texts.payment import USE_CREDIT_PROMPT
            await bot.send_message(
                telegram_id,
                USE_CREDIT_PROMPT.format(balance=balance),
                reply_markup=use_credit_keyboard(),
            )
        await save_order_file(telegram_id, pkg, credits)
        # Отмечаем платёж выполненным и очищаем временные данные
        await complete_pending_payment(payment_id)


async def yukassa_webhook_handler(request: web.Request) -> web.Response:
    """Webhook от ЮКассы — вызывается автоматически после оплаты"""
    try:
        import json
        from yookassa.domain.notification import WebhookNotificationEventType, WebhookNotificationFactory
        body = await request.text()
        notification = WebhookNotificationFactory().create(json.loads(body))

        if notification.event != WebhookNotificationEventType.PAYMENT_SUCCEEDED:
            return web.Response(status=200)

        payment_obj = notification.object
        payment_id = payment_obj.id
        amount = float(payment_obj.amount.value)
        metadata = payment_obj.metadata or {}
        telegram_id = int(metadata.get("telegram_id", 0))

        if not telegram_id:
            logger.warning(f"Webhook: нет telegram_id в metadata для платежа {payment_id}")
            return web.Response(status=200)

        data = await get_pending_payment(payment_id)
        if not data or data.status != "pending":
            logger.warning(f"Webhook: платёж {payment_id} не найден в БД или уже обработан")
            return web.Response(status=200)

        bot: Bot = request.app["bot"]
        await _process_successful_payment(
            bot=bot,
            telegram_id=telegram_id,
            payment_id=payment_id,
            amount=amount,
            package_index=data.package_index,
            is_stylist=data.is_stylist,
            state_data=data.state_data,
        )
        return web.Response(status=200)

    except Exception as e:
        logger.error(f"Webhook ошибка: {e}", exc_info=True)
        return web.Response(status=200)


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
        f"Сумма: {pkg.get('rub')}₽\n"
    )
    filepath = os.path.join(orders_dir, f"purchase_{telegram_id}_{int(time.time())}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
