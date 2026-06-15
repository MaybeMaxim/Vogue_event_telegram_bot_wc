from aiogram.fsm.state import State, StatesGroup


class Support(StatesGroup):
    """States for the support section's free-text flows."""

    waiting_for_question = State()
    waiting_for_bug = State()
