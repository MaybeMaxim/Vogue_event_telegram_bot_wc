from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    """States for the user registration / onboarding flow."""

    # Entry point: user can either type a full name or share a contact
    name_or_contact = State()

    # Reached when contact was shared but Telegram gave no usable surname
    # (phone is already known at this point)
    name_only = State()

    # Reached when the user typed their name manually first
    # and we still need a phone number
    phone = State()

    # Always required, regardless of which path got us here
    email = State()

    # Final preview/confirmation screen with edit options
    confirm = State()
