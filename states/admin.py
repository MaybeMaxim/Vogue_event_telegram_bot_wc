from aiogram.fsm.state import State, StatesGroup


class AdminSearch(StatesGroup):
    """Free-text guest search from the admin panel."""

    waiting_for_query = State()


class AdminAdd(StatesGroup):
    """Manual-add flow: after picking an activity, search for the guest."""

    waiting_for_query = State()


class AdminBroadcast(StatesGroup):
    waiting_for_text = State()
    waiting_for_time = State()
