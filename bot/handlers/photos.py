import os
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from bot.states.user_states import UserState
from bot.texts.registration import *
from bot.texts.sales import FREE_ANALYSIS_TEXT
from bot.keyboards.inline import *
from bot.db.queries import update_user, get_user
from bot.utils.ai_analysis import free_analysis, full_report, dialogue_start, dialogue_continue, build_dialogue_system, check_mode_compliance
from bot.config import config

router = Router()


@router.message(F.photo, StateFilter(UserState.photos))
async def process_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photo_ids = data.get("photo_ids", [])
    file_id = message.photo[-1].file_id
    if file_id not in photo_ids:
        photo_ids.append(file_id)
    await state.update_data(photo_ids=photo_ids)
    # Сохраняем photo_ids в БД сразу — чтобы пережить рестарт до оплаты
    await update_user(message.from_user.id, photo_ids=photo_ids)
    count = len(photo_ids)
    if count == 1:
        await message.answer(PHOTO_RECEIVED_1, reply_markup=photo_done_keyboard())
    elif count >= 3:
        await state.set_state(UserState.confirm)
        await show_confirm(message, state)
    else:
        await message.answer(PHOTO_RECEIVED_2, reply_markup=photo_done_keyboard())


@router.message(StateFilter(UserState.photos))
async def process_photo_invalid(message: Message, state: FSMContext):
    if message.text and message.text.strip() == PHOTO_DONE:
        data = await state.get_data()
        photo_ids = data.get("photo_ids", [])
        if not photo_ids:
            await message.answer("Отправь хотя бы одно фото.")
            return
        await state.set_state(UserState.confirm)
        await show_confirm(message, state)
    else:
        await message.answer(PHOTO_NOT_PHOTO)


@router.callback_query(F.data == "photo_skip", StateFilter(UserState.photos))
async def photo_skip(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    photo_ids = data.get("photo_ids", [])
    if not photo_ids:
        await callback.message.answer("Нужно хотя бы одно фото для анализа.")
        return
    await state.set_state(UserState.confirm)
    await show_confirm(callback.message, state)


@router.callback_query(F.data == "photo_done", StateFilter(UserState.photos))
async def photo_done(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    photo_ids = data.get("photo_ids", [])
    if not photo_ids:
        await callback.message.answer("Отправь хотя бы одно фото.")
        return
    await state.set_state(UserState.confirm)
    await show_confirm(callback.message, state)


async def show_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data.get("name", "—")
    age = data.get("age", "—")
    selected_goals = data.get("selected_goals", [])
    photo_ids = data.get("photo_ids", [])
    goals_str = ", ".join(selected_goals) if selected_goals else "—"
    text = CONFIRM_TEXT.format(
        name=name,
        age=age,
        goals=goals_str,
        photos_count=len(photo_ids),
    )
    await message.answer(text, reply_markup=confirm_keyboard())


@router.callback_query(F.data == "confirm_yes", StateFilter(UserState.confirm))
async def confirm_yes(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    data = await state.get_data()
    await update_user(
        telegram_id=callback.from_user.id,
        name=data.get("name"),
        age=data.get("age"),
        goals=data.get("selected_goals", []),
        photo_ids=data.get("photo_ids", []),
        status="new",
    )
    age = data.get("age", 25)
    goals = data.get("selected_goals", [])
    name = data.get("name", "")
    photo_ids = data.get("photo_ids", [])
    await callback.message.answer("🔍 Анализирую твои фото... это займёт несколько секунд.")
    analysis = await free_analysis(bot, photo_ids, name, age, goals)
    await state.update_data(free_analysis=analysis)
    await callback.message.answer("🤖 Анализ завершён. Прежде чем показать результат, задам пару вопросов.")
    msg = await dialogue_start(analysis, name, age, goals)
    await state.set_state(UserState.dialogue)
    await state.update_data(dialogue_count=0, dialogue_messages=[])
    await callback.message.answer(msg)


@router.message(StateFilter(UserState.dialogue))
async def dialogue_message(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    count = data.get("dialogue_count", 0)
    msgs = data.get("dialogue_messages", [])
    analysis = data.get("free_analysis", {})
    if not message.text:
        await message.answer("Напиши текстовый ответ, пожалуйста.")
        return
    user_text = message.text.strip()
    blocked = check_mode_compliance(user_text)
    if blocked:
        await message.answer(blocked)
        return
    msgs.append({"role": "user", "content": user_text})
    name = data.get("name", "")
    age = data.get("age", 25)
    goals = data.get("selected_goals", [])
    system = build_dialogue_system(analysis, name, age, goals)
    reply = await dialogue_continue(msgs, system)
    msgs.append({"role": "assistant", "content": reply})
    await state.update_data(dialogue_messages=msgs, dialogue_count=count + 1)
    await message.answer(reply)
    if count >= 3:
        await update_user(message.from_user.id, free_used=1)
        await state.set_state(UserState.free_shown)
        free_text = analysis.get("free_text", "")
        if free_text:
            await message.answer(free_text)
        else:
            text = FREE_ANALYSIS_TEXT.format(
                potential=analysis.get("current_potential", 50),
                zone=analysis.get("growth_zone", "—"),
                mistake=analysis.get("mistake", "—"),
                after=analysis.get("potential_after", 75),
            )
            await message.answer(text)
        await message.answer(
            "🔥 Полный разбор готов! Хочешь открыть его?",
            reply_markup=free_analysis_keyboard(),
        )


@router.callback_query(F.data == "confirm_edit", StateFilter(UserState.confirm))
async def confirm_edit(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(EDIT_CHOICE, reply_markup=edit_choice_keyboard())


@router.callback_query(F.data == "buy_full_report", StateFilter(UserState.free_shown))
async def buy_full_report(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    user = await get_user(callback.from_user.id)
    if user and user.godmode:
        await use_credit_yes(callback, state, bot)
        return
    balance = user.credits if user else 0
    if balance > 0:
        await state.set_state(UserState.credits_menu)
        from bot.texts.payment import USE_CREDIT_PROMPT
        await callback.message.answer(
            USE_CREDIT_PROMPT.format(balance=balance),
            reply_markup=use_credit_keyboard(),
        )
    else:
        await state.set_state(UserState.credits_menu)
        from bot.texts.sales import CREDIT_HEADER
        await callback.message.answer(
            CREDIT_HEADER,
            reply_markup=credit_packages_keyboard(0),
        )


@router.callback_query(F.data == "use_credit_yes", StateFilter(UserState.credits_menu))
async def use_credit_yes(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    user = await get_user(callback.from_user.id)
    if not user or (not user.godmode and (not user.credits or user.credits < 1)):
        await callback.message.answer("Недостаточно кредитов.")
        return
    if not user.godmode:
        await update_user(callback.from_user.id, credits=user.credits - 1)
    data = await state.get_data()
    age = data.get("age", 25)
    goals = data.get("selected_goals", [])
    name = data.get("name", "")
    photo_ids = data.get("photo_ids", [])
    dialogue_msgs = data.get("dialogue_messages", [])
    await callback.message.answer("🤖 Нейросеть анализирует твои фото... это займёт до 30 секунд.")
    report = await full_report(bot, photo_ids, name, age, goals, dialogue_history=dialogue_msgs)
    await update_user(callback.from_user.id, result_text=report, status="completed")
    await save_report_file(callback.from_user.id, report)
    from bot.db.queries import save_analysis
    await save_analysis(callback.from_user.id, "full", report)
    from bot.texts.result import FULL_REPORT_HEADER, FULL_REPORT_FOOTER
    full = FULL_REPORT_HEADER.format(name=name) + "\n" + report + "\n" + FULL_REPORT_FOOTER
    await state.set_state(UserState.result)
    await callback.message.answer(full, reply_markup=after_report_keyboard())


@router.callback_query(F.data == "use_credit_no", StateFilter(UserState.credits_menu))
async def use_credit_no(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = await get_user(callback.from_user.id)
    balance = user.credits if user else 0
    from bot.texts.sales import CREDIT_HEADER
    await callback.message.answer(
        CREDIT_HEADER,
        reply_markup=credit_packages_keyboard(balance),
    )


async def save_report_file(telegram_id: int, report: str):
    orders_dir = os.path.join(config.DATA_DIR, "reports")
    os.makedirs(orders_dir, exist_ok=True)
    filepath = os.path.join(orders_dir, f"report_{telegram_id}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
