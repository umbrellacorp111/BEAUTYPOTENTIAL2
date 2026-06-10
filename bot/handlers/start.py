from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from bot.texts.welcome import WELCOME_TEXT
from bot.keyboards.inline import start_keyboard, credit_packages_keyboard, use_credit_keyboard, after_report_keyboard, analyses_list_keyboard
from bot.db.queries import get_user, create_user, get_pending_payment_by_user, get_user_analyses, get_saved_analysis
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
    await message.answer(WELCOME_TEXT, reply_markup=start_keyboard())


@router.callback_query(F.data == "my_analyses")
async def my_analyses(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    analyses = await get_user_analyses(callback.from_user.id)
    if not analyses:
        await callback.message.answer(
            "📂 У вас пока нет сохранённых разборов.",
            reply_markup=start_keyboard(),
        )
        return

    if len(analyses) == 1:
        a = analyses[0]
        await state.set_state(UserState.result)
        await callback.message.answer(a.report_text, reply_markup=after_report_keyboard())
        return

    await callback.message.answer(
        "📂 Ваши разборы:",
        reply_markup=analyses_list_keyboard(analyses),
    )


@router.callback_query(F.data.startswith("view_analysis_"))
async def view_analysis(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    analysis_id = int(callback.data.replace("view_analysis_", ""))
    a = await get_saved_analysis(analysis_id)
    if not a:
        await callback.message.answer("❌ Разбор не найден.")
        return
    await state.set_state(UserState.result)
    await callback.message.answer(a.report_text, reply_markup=after_report_keyboard())


@router.callback_query(F.data == "start_survey")
async def start_survey(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = await get_user(callback.from_user.id)
    if user and user.free_used and not user.godmode:
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
