from aiogram.fsm.state import State, StatesGroup


class ProfileEdit(StatesGroup):
    """States for editing an existing profile field from ⚙️ Профіль."""

    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_email = State()
