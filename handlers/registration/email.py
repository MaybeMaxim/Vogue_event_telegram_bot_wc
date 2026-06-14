"""
Step 3 of registration: email address.

Always required regardless of which path got the user here
(typed name, contact share with full name, or contact share with
surname filled in manually afterwards).
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from states.registration import Registration
from texts import registration as t
from utils.validators import normalize_email

router = Router(name="registration_email")


@router.message(Registration.email, F.text)
async def handle_email(message: Message, state: FSMContext) -> None:
    """Validate the email and move to the profile preview/confirmation step."""
    email = normalize_email(message.text)

    if email is None:
        await message.answer(t.INVALID_EMAIL)
        return

    await state.update_data(email=email)
    await state.set_state(Registration.confirm)

    # Imported lazily to avoid a circular import with confirm.py
    from handlers.registration.confirm import show_profile_preview

    await show_profile_preview(message, state)


@router.message(Registration.email, ~F.text)
async def handle_non_text_at_email_step(message: Message) -> None:
    """Reject non-text input (photo, sticker, etc.) while waiting for an email."""
    await message.answer(t.EMAIL_REQUIRED)
