from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.texts.result import *
from bot.keyboards.inline import start_keyboard
from bot.config import config

router = Router()


@router.callback_query(F.data == "fb_consult")
async def fb_consult(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        FEEDBACK_CONSULT_ANSWER.format(support=config.SUPPORT_USERNAME)
    )


@router.callback_query(F.data == "fb_retry")
async def fb_retry(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        FEEDBACK_RETRY_ANSWER.format(bot_link=config.BOT_LINK)
    )


@router.callback_query(F.data == "fb_no")
async def fb_no(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(FEEDBACK_NO_ANSWER, reply_markup=start_keyboard())
