from aiogram.fsm.state import State, StatesGroup


class Support(StatesGroup):
    waiting_for_bug = State()
