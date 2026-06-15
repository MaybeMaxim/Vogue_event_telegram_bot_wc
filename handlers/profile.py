"""
Handler for the ⚙️ Профіль section: view profile and edit individual
fields (name / phone / email), reusing the registration validators.

Fixes the earlier gap where a mistyped name couldn't be corrected after
registration.
"""

import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud.users import get_user_by_tg_id, update_user_field
from keyboards.profile import cancel_edit_keyboard, profile_keyboard
from keyboards.main_menu import MENU_BUTTONS, MENU_PROFILE
from states.profile import ProfileEdit
from texts import profile as t
from utils.validators import normalize_email, normalize_full_name, normalize_phone

router = Router(name="profile")


async def _show_profile(message: Message, session: AsyncSession, tg_id: int, edit: bool = False) -> None:
    """Render the profile card. If `edit`, edit the existing message in place."""
    user = await get_user_by_tg_id(session, tg_id)
    if user is None:
        return

    text = t.PROFILE_VIEW.format(
        full_name=html.escape(user.full_name),
        phone=html.escape(user.phone),
        email=html.escape(user.email),
    )

    if edit:
        await message.edit_text(text, reply_markup=profile_keyboard())
    else:
        await message.answer(text, reply_markup=profile_keyboard())


@router.message(F.text == MENU_PROFILE)
async def open_profile(message: Message, session: AsyncSession) -> None:
    """Show the profile card from the main menu."""
    await _show_profile(message, session, message.from_user.id)


@router.callback_query(F.data == "profile:close")
async def close_profile(callback: CallbackQuery) -> None:
    """Collapse the profile card."""
    await callback.message.edit_text(t.CLOSED)
    await callback.answer()


# --- Edit entry points -----------------------------------------------------

@router.callback_query(F.data == "profile:edit_name")
async def edit_name(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileEdit.waiting_for_name)
    await callback.message.answer(t.ASK_NEW_NAME, reply_markup=cancel_edit_keyboard())
    await callback.answer()


@router.callback_query(F.data == "profile:edit_phone")
async def edit_phone(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileEdit.waiting_for_phone)
    await callback.message.answer(t.ASK_NEW_PHONE, reply_markup=cancel_edit_keyboard())
    await callback.answer()


@router.callback_query(F.data == "profile:edit_email")
async def edit_email(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileEdit.waiting_for_email)
    await callback.message.answer(t.ASK_NEW_EMAIL, reply_markup=cancel_edit_keyboard())
    await callback.answer()


@router.callback_query(F.data == "profile:cancel_edit")
async def cancel_edit(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Abort an in-progress field edit and return to the profile card."""
    await state.clear()
    await callback.message.edit_text(t.EDIT_CANCELLED)
    await _show_profile(callback.message, session, callback.from_user.id)
    await callback.answer()


# --- Edit input handlers ---------------------------------------------------

@router.message(ProfileEdit.waiting_for_name, F.text & ~F.text.in_(MENU_BUTTONS))
async def save_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    cleaned = normalize_full_name(message.text)
    if cleaned is None:
        await message.answer(t.INVALID_NAME)
        return

    await update_user_field(session, message.from_user.id, "full_name", cleaned)
    await state.clear()
    await message.answer(t.NAME_UPDATED)
    await _show_profile(message, session, message.from_user.id)


@router.message(ProfileEdit.waiting_for_phone, F.text & ~F.text.in_(MENU_BUTTONS))
async def save_phone(message: Message, state: FSMContext, session: AsyncSession) -> None:
    phone = normalize_phone(message.text)
    if phone is None:
        await message.answer(t.INVALID_PHONE)
        return

    await update_user_field(session, message.from_user.id, "phone", phone)
    await state.clear()
    await message.answer(t.PHONE_UPDATED)
    await _show_profile(message, session, message.from_user.id)


@router.message(ProfileEdit.waiting_for_email, F.text & ~F.text.in_(MENU_BUTTONS))
async def save_email(message: Message, state: FSMContext, session: AsyncSession) -> None:
    email = normalize_email(message.text)
    if email is None:
        await message.answer(t.INVALID_EMAIL)
        return

    await update_user_field(session, message.from_user.id, "email", email)
    await state.clear()
    await message.answer(t.EMAIL_UPDATED)
    await _show_profile(message, session, message.from_user.id)
