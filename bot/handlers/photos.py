from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from bot.states.user_states import UserState
from bot.texts.registration import *
from bot.keyboards.inline import *

router = Router()


@router.message(F.photo, StateFilter(UserState.photos))
async def process_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photo_ids = data.get("photo_ids", [])
    file_id = message.photo[-1].file_id
    if file_id not in photo_ids:
        photo_ids.append(file_id)
    await state.update_data(photo_ids=photo_ids)
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
async def confirm_yes(callback: CallbackQuery, state: FSMContext):
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
    from bot.texts.sales import SALES_TEXT
    from bot.keyboards.inline import payment_choice_keyboard
    await state.set_state(UserState.payment_method)
    await callback.message.answer(SALES_TEXT)
    await callback.message.answer(
        "Выбери способ оплаты:", reply_markup=payment_choice_keyboard()
    )


@router.callback_query(F.data == "confirm_edit", StateFilter(UserState.confirm))
async def confirm_edit(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(EDIT_CHOICE, reply_markup=edit_choice_keyboard())


@router.callback_query(F.data == "edit_back")
async def edit_back(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(UserState.confirm)
    await show_confirm(callback.message, state)
