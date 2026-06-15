"""
Step 4 of registration: profile preview, field-level editing entry points,
and saving.

This module owns:
- rendering the preview (show_profile_preview, called from email.py too)
- the "reg:save" / "reg:edit_*" inline button callbacks
- text input on the name_only/phone/email states WHEN returning from
  an edit on the preview (distinguished by "email" already present
  in FSM data)

To avoid duplicate handlers for the same state, the actual text-input
validation for name/phone/email lives in a single place per field:
- name_only text  -> this module (shared with start.py's name_only,
                      see note in handle_name_input)
- phone text      -> this module (shared with phone.py)
- email text      -> email.py owns this exclusively; it already calls
                      show_profile_preview on success, which correctly
                      re-renders both first-time and edit-return cases.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud.users import create_user
from keyboards.main_menu import main_menu_keyboard
from keyboards.registration import profile_preview_keyboard
from states.registration import Registration
from texts import registration as t

router = Router(name="registration_confirm")

logger = logging.getLogger(__name__)


async def show_profile_preview(message: Message, state: FSMContext) -> None:
    """
    Render the profile preview with edit/save buttons.

    Called from the email step on first arrival, and again after any
    field edit completes.
    """
    data = await state.get_data()

    await message.answer(
        t.PROFILE_PREVIEW.format(
            full_name=data["full_name"],
            phone=data["phone"],
            email=data["email"],
        ),
        reply_markup=profile_preview_keyboard(),
    )


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

@router.callback_query(Registration.confirm, F.data == "reg:save")
async def save_profile(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """User confirmed the preview: persist the profile and show the main menu."""
    data = await state.get_data()

    # Remove the buttons immediately so a double-tap can't fire a second
    # "reg:save" before the first one finishes (create_user is also
    # idempotent as a second line of defense for genuine races).
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()

    try:
        user = await create_user(
            session,
            tg_id=callback.from_user.id,
            full_name=data["full_name"],
            phone=data["phone"],
            email=data["email"],
        )
    except Exception:
        logger.exception("Failed to save profile for tg_id=%s", callback.from_user.id)
        await callback.message.answer(t.SAVE_FAILED)
        return

    await state.clear()

    await callback.message.answer(t.REGISTRATION_COMPLETE.format(full_name=user.full_name))
    # Send the long intro WITHOUT the keyboard, then attach the reply
    # keyboard to a short prompt. On mobile, tapping a reply-keyboard
    # button quotes the message the keyboard is anchored to, so anchoring
    # it to a short line keeps that quote unobtrusive.
    await callback.message.answer(t.MAIN_MENU_INTRO)
    await callback.message.answer(t.MAIN_MENU_PROMPT, reply_markup=main_menu_keyboard())


# ---------------------------------------------------------------------------
# Edit buttons: switch to the relevant single-field state
# ---------------------------------------------------------------------------

@router.callback_query(Registration.confirm, F.data == "reg:edit_name")
async def start_edit_name(callback: CallbackQuery, state: FSMContext) -> None:
    """User wants to change their name."""
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.set_state(Registration.name_only)
    await callback.message.answer(t.ASK_NAME_AGAIN)
    await callback.answer()


@router.callback_query(Registration.confirm, F.data == "reg:edit_phone")
async def start_edit_phone(callback: CallbackQuery, state: FSMContext) -> None:
    """User wants to change their phone number."""
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.set_state(Registration.phone)
    await callback.message.answer(t.ASK_PHONE_AGAIN)
    await callback.answer()


@router.callback_query(Registration.confirm, F.data == "reg:edit_email")
async def start_edit_email(callback: CallbackQuery, state: FSMContext) -> None:
    """User wants to change their email address."""
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.set_state(Registration.email)
    await callback.message.answer(t.ASK_EMAIL_AGAIN)
    await callback.answer()


# ---------------------------------------------------------------------------
# Defensive: ignore free text on the preview screen itself
# ---------------------------------------------------------------------------

@router.message(Registration.confirm)
async def handle_text_on_preview(message: Message, state: FSMContext) -> None:
    """User sent free text instead of pressing a button on the preview screen."""
    await message.answer(t.PREVIEW_USE_BUTTONS)
    await show_profile_preview(message, state)
