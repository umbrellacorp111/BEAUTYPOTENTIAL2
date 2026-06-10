from aiogram.fsm.state import State, StatesGroup


class UserState(StatesGroup):
    name = State()
    age = State()
    goals = State()
    photos = State()
    confirm = State()
    dialogue = State()
    free_shown = State()
    credits_menu = State()
    payment_method = State()
    awaiting_payment = State()
    result = State()
    stylist_chat = State()
