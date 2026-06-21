from aiogram.fsm.state import State, StatesGroup


class QuestionFlow(StatesGroup):
    waiting_for_text = State()
