from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from bot.texts.result import *
from bot.keyboards.inline import feedback_keyboard
from bot.db.queries import get_user
from bot.states.user_states import UserState

router = Router()


async def send_result(message: Message, user):
    text = RESULT_HEADER.format(name=user.name)
    if user.result_text:
        text += f"\n{user.result_text}\n"
    text += RESULT_FOOTER

    if user.result_file_id:
        try:
            await message.answer_document(
                document=user.result_file_id,
                caption=RESULT_WITH_FILE,
            )
        except Exception:
            pass

    await message.answer(text)
    await message.answer(FEEDBACK_TEXT, reply_markup=feedback_keyboard())
