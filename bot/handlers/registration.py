from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from bot.states.user_states import UserState
from bot.texts.registration import *
from bot.keyboards.inline import *
from bot.utils.validators import validate_name, validate_age
from bot.db.queries import update_user

router = Router()


@router.message(StateFilter(UserState.name))
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not validate_name(name):
        await message.answer(NAME_ERROR)
        return
    await state.update_data(name=name)
    await state.set_state(UserState.age)
    await message.answer(AGE_PROMPT)


@router.message(StateFilter(UserState.age))
async def process_age(message: Message, state: FSMContext):
    age_text = message.text.strip()
    if not validate_age(age_text):
        await message.answer(AGE_ERROR)
        return
    await state.update_data(age=int(age_text))
    await state.set_state(UserState.goals)
    await message.answer(GOALS_PROMPT, reply_markup=goals_keyboard())


@router.callback_query(F.data.startswith("goal_"), StateFilter(UserState.goals))
async def process_goal_toggle(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    selected = data.get("selected_goals", [])
    goal_cb = callback.data
    goal_map = {
        "goal_face": "Лицо / черты",
        "goal_style": "Стиль одежды",
        "goal_hair": "Причёска",
        "goal_body": "Форма тела / осанка",
        "goal_confidence": "Уверенность в себе",
        "goal_other": "Другое",
    }
    goal_text = goal_map.get(goal_cb)
    if not goal_text:
        return
    if goal_cb == "goal_other":
        await state.set_state(UserState.goals)
        await callback.message.answer(GOALS_OTHER_PROMPT)
        return
    if goal_text in selected:
        selected.remove(goal_text)
    else:
        selected.append(goal_text)
    await state.update_data(selected_goals=selected)


@router.message(StateFilter(UserState.goals))
async def process_goal_other(message: Message, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_goals", [])
    selected.append(message.text.strip())
    await state.update_data(selected_goals=selected)
    await state.set_state(UserState.photos)
    await message.answer(PHOTOS_PROMPT, reply_markup=photo_skip_keyboard())


@router.callback_query(F.data == "goals_done", StateFilter(UserState.goals))
async def process_goals_done(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    selected = data.get("selected_goals", [])
    if not selected:
        await callback.message.answer("Выбери хотя бы одну цель.")
        return
    await state.set_state(UserState.photos)
    await callback.message.answer(PHOTOS_PROMPT, reply_markup=photo_skip_keyboard())


@router.callback_query(F.data == "edit_name")
async def edit_name(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(UserState.name)
    await callback.message.answer(NAME_PROMPT)


@router.callback_query(F.data == "edit_age")
async def edit_age(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(UserState.age)
    await callback.message.answer(AGE_PROMPT)


@router.callback_query(F.data == "edit_goals")
async def edit_goals(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(selected_goals=[])
    await state.set_state(UserState.goals)
    await callback.message.answer(GOALS_PROMPT, reply_markup=goals_keyboard())


@router.callback_query(F.data == "edit_photos")
async def edit_photos(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(photo_ids=[])
    await state.set_state(UserState.photos)
    await callback.message.answer(PHOTOS_PROMPT, reply_markup=photo_skip_keyboard())
