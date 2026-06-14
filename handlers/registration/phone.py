"""
Step 2 of registration: phone number.

Only reached when the user typed their name manually at Step 1
(handlers.registration.start.handle_typed_name). If the phone was
already captured via a shared contact, this step is skipped entirely.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Contact, Message

from keyboards.registration import remove_keyboard
from states.registration import Registration
from texts import registration as t
from utils.validators import normalize_phone

router = Router(name="registration_phone")


@router.message(Registration.phone, F.contact)
async def handle_phone_via_contact(message: Message, state: FSMContext) -> None:
    """User shared their contact at the phone step."""
    contact = message.contact

    if not _is_own_contact(contact, message.from_user.id):
        await message.answer(t.CONTACT_PHONE_ONLY_NOT_OWN)
        return

    phone = normalize_phone(contact.phone_number)
    if phone is None:
        await message.answer(t.INVALID_PHONE)
        return

    await _save_phone_and_proceed(message, state, phone)


@router.message(Registration.phone, F.text)
async def handle_phone_via_text(message: Message, state: FSMContext) -> None:
    """User typed their phone number manually."""
    phone = normalize_phone(message.text)

    if phone is None:
        await message.answer(t.INVALID_PHONE)
        return

    await _save_phone_and_proceed(message, state, phone)


@router.message(Registration.phone, ~F.text & ~F.contact)
async def handle_non_text_at_phone_step(message: Message) -> None:
    """Reject input that's neither text nor a contact (photo, sticker, etc.)."""
    await message.answer(t.PHONE_REQUIRED_REDIRECT)


def _is_own_contact(contact: Contact, sender_tg_id: int) -> bool:
    """Check that the shared contact belongs to the sender themselves."""
    return contact.user_id is None or contact.user_id == sender_tg_id


async def _save_phone_and_proceed(message: Message, state: FSMContext, phone: str) -> None:
    """
    Persist the phone in FSM data, hide the contact keyboard, and continue.

    Two distinct callers land here:
    - First-time registration (no email yet) -> proceed to the email step.
    - Editing from the preview screen (email already known) -> return
      to the preview.
    """
    await state.update_data(phone=phone)
    data = await state.get_data()

    await message.answer(t.THANKS_PHONE, reply_markup=remove_keyboard())

    if "email" in data:
        from handlers.registration.confirm import show_profile_preview

        await state.set_state(Registration.confirm)
        await show_profile_preview(message, state)
    else:
        await state.set_state(Registration.email)
        await message.answer(t.ASK_EMAIL)
