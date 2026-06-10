from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from bot.texts.welcome import WELCOME_TEXT
from bot.keyboards.inline import start_keyboard, credit_packages_keyboard, use_credit_keyboard
from bot.db.queries import get_user, create_user, get_pending_payment_by_user
from bot.states.user_states import UserState

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if not user:
        await create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        user = await get_user(message.from_user.id)

    # Восстановление: пользователь уже оплатил, но разбор не был выдан (рестарт бота)
    if user and user.status == "completed" and user.result_text:
        from bot.texts.result import FULL_REPORT_HEADER, FULL_REPORT_FOOTER
        from bot.keyboards.inline import after_report_keyboard
        name = user.name or ""
        full = FULL_REPORT_HEADER.format(name=name) + "\n" + user.result_text + "\n" + FULL_REPORT_FOOTER
        await state.set_state(UserState.result)
        await message.answer("🔄 Восстанавливаю твой разбор...\n\n" + full, reply_markup=after_report_keyboard())
        return

    await message.answer(WELCOME_TEXT, reply_markup=start_keyboard())


@router.callback_query(F.data == "start_survey")
async def start_survey(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = await get_user(callback.from_user.id)
    if user and user.free_used:
        balance = user.credits or 0
        if balance > 0:
            from bot.texts.payment import USE_CREDIT_PROMPT
            await state.set_state(UserState.credits_menu)
            await callback.message.answer(
                USE_CREDIT_PROMPT.format(balance=balance),
                reply_markup=use_credit_keyboard(),
            )
        else:
            await state.set_state(UserState.credits_menu)
            from bot.texts.sales import CREDIT_HEADER
            await callback.message.answer(
                "🔒 Бесплатный разбор уже использован.\n\n" + CREDIT_HEADER,
                reply_markup=credit_packages_keyboard(0),
            )
        return
    await state.set_state(UserState.name)
    from bot.texts.registration import NAME_PROMPT
    await callback.message.answer(NAME_PROMPT)


@router.callback_query(F.data == "go_home")
async def go_home(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    from bot.texts.welcome import WELCOME_TEXT
    await callback.message.answer(WELCOME_TEXT, reply_markup=start_keyboard())
