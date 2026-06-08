from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from bot.texts.welcome import WELCOME_TEXT
from bot.keyboards.inline import start_keyboard
from bot.db.queries import get_user, create_user
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


@router.callback_query(F.data == "start_survey")
async def start_survey(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    from bot.texts.registration import NAME_PROMPT
    await state.set_state(UserState.name)
    await callback.message.answer(NAME_PROMPT)
