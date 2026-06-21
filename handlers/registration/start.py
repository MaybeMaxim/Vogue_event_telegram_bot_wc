"""
Entry-point handlers for /start and the beginning of the registration flow.

This module only handles:
- /start in private chats and groups
- routing into the registration FSM
- the "name_or_contact" step (Step 1), including the contact-share branch

Subsequent steps (phone, email, confirm) live in their own modules
to keep each file focused and easy to navigate.
"""

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Contact, Message
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud.users import get_user_by_tg_id
from keyboards.main_menu import main_menu_keyboard
from keyboards.registration import (
    confirm_derived_name_keyboard,
    group_chat_redirect_keyboard,
    name_or_contact_keyboard,
    phone_request_keyboard,
    remove_keyboard,
    start_registration_keyboard,
)
from states.registration import Registration
from texts import registration as t
from utils.validators import (
    is_usable_first_name,
    normalize_full_name,
    normalize_name_part,
    normalize_phone,
    normalize_telegram_contact_name,
)

router = Router(name="registration_start")


# ---------------------------------------------------------------------------
# /myid — available to anyone, no registration required
# ---------------------------------------------------------------------------

@router.message(Command("myid"))
async def cmd_myid(message: Message) -> None:
    await message.answer(f"🪪 Ваш Telegram ID: <code>{message.from_user.id}</code>")


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

@router.message(CommandStart(), F.chat.type != "private")
async def start_in_group(message: Message, bot: Bot) -> None:
    """If /start is used in a group chat, redirect the user to a private chat."""
    bot_info = await bot.get_me()
    await message.answer(
        t.GROUP_CHAT_REDIRECT,
        reply_markup=group_chat_redirect_keyboard(bot_info.username),
    )


@router.message(CommandStart(), F.chat.type == "private")
async def start_private(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """
    Main /start entry point for private chats.

    - Registered users -> welcome back + main menu.
    - New users with no FSM state -> welcome message + "start registration" button.
    - New users already mid-registration -> resume at their current step.
    """
    user = await get_user_by_tg_id(session, message.from_user.id)
    if user is not None:
        await _show_returning_user_welcome(message, user.full_name)
        return

    current_state = await state.get_state()
    if current_state is not None:
        await _resume_registration(message, state)
        return

    await message.answer(t.WELCOME_NEW_USER, reply_markup=start_registration_keyboard())


async def _show_returning_user_welcome(message: Message, full_name: str) -> None:
    """Greet an already-registered user and show the main menu."""
    await message.answer(
        t.WELCOME_BACK.format(full_name=full_name),
        reply_markup=main_menu_keyboard(),
    )


async def _resume_registration(message: Message, state: FSMContext) -> None:
    """Re-show the prompt for whatever step the user was on before."""
    await message.answer(t.RESUME_REGISTRATION)
    await _send_step_prompt(message, state)


async def _send_step_prompt(message: Message, state: FSMContext) -> None:
    """Dispatch to the correct prompt based on the current FSM state."""
    current_state = await state.get_state()

    if current_state == Registration.name_or_contact.state:
        await message.answer(t.ASK_NAME_OR_CONTACT, reply_markup=name_or_contact_keyboard())
    elif current_state == Registration.name_only.state:
        data = await state.get_data()
        first_name = data.get("tg_first_name")
        if first_name and is_usable_first_name(first_name):
            await message.answer(t.ASK_SURNAME_AFTER_CONTACT.format(first_name=first_name))
        else:
            await message.answer(t.ASK_FULL_NAME_AFTER_CONTACT)
    elif current_state == Registration.phone.state:
        data = await state.get_data()
        await message.answer(
            t.THANKS_NAME_ASK_PHONE.format(full_name=data.get("full_name", "")),
            reply_markup=phone_request_keyboard(),
        )
    elif current_state == Registration.email.state:
        await message.answer(t.ASK_EMAIL)
    elif current_state == Registration.confirm.state:
        # Imported lazily to avoid a circular import with confirm.py
        from handlers.registration.confirm import show_profile_preview

        await show_profile_preview(message, state)


# ---------------------------------------------------------------------------
# Step 1: "Почати реєстрацію" button pressed
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "reg:start")
async def begin_registration(callback: CallbackQuery, state: FSMContext) -> None:
    """User pressed the inline "Почати реєстрацію" button."""
    await state.set_state(Registration.name_or_contact)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(t.ASK_NAME_OR_CONTACT, reply_markup=name_or_contact_keyboard())
    await callback.answer()


# ---------------------------------------------------------------------------
# Step 1: user typed a name as plain text
# ---------------------------------------------------------------------------

@router.message(Registration.name_or_contact, F.text)
async def handle_typed_name(message: Message, state: FSMContext) -> None:
    """User typed their full name instead of sharing a contact."""
    cleaned = normalize_full_name(message.text)

    if cleaned is None:
        await message.answer(t.INVALID_NAME)
        return

    await state.update_data(full_name=cleaned)
    await state.set_state(Registration.phone)
    await message.answer(
        t.THANKS_NAME_ASK_PHONE.format(full_name=cleaned),
        reply_markup=phone_request_keyboard(),
    )


@router.message(Registration.name_or_contact, ~F.text & ~F.contact)
async def handle_non_text_at_name_step(message: Message) -> None:
    """User sent a photo/sticker/voice etc. instead of text or a contact."""
    await message.answer(t.NAME_NOT_TEXT)


# ---------------------------------------------------------------------------
# Step 1: user shared their contact
# ---------------------------------------------------------------------------

@router.message(Registration.name_or_contact, F.contact)
async def handle_shared_contact(message: Message, state: FSMContext) -> None:
    """
    User shared their contact at the very first step.

    Branches into:
    - confirm-derived-name (both first + last name usable)
    - name_only (phone known, surname missing/unusable)
    """
    contact = message.contact

    if not _is_own_contact(contact, message.from_user.id):
        await message.answer(t.CONTACT_NOT_OWN)
        return

    phone = normalize_phone(contact.phone_number)
    if phone is None:
        # Extremely unlikely for a Telegram-provided contact, but stay safe.
        await message.answer(t.INVALID_PHONE)
        return

    # Remove the "Share contact" reply keyboard now that we have the contact.
    await message.answer(t.CONTACT_RECEIVED, reply_markup=remove_keyboard())

    await state.update_data(phone=phone, tg_first_name=contact.first_name)

    derived_name = normalize_telegram_contact_name(contact.first_name, contact.last_name)
    if derived_name is not None:
        await _offer_derived_name(message, state, derived_name, phone)
        return

    await _ask_for_surname_after_contact(message, state, contact.first_name)


def _is_own_contact(contact: Contact, sender_tg_id: int) -> bool:
    """Check that the shared contact belongs to the sender themselves."""
    return contact.user_id is None or contact.user_id == sender_tg_id


async def _offer_derived_name(message: Message, state: FSMContext, derived_name: str, phone: str) -> None:
    """Both first and last name were usable: ask the user to confirm or edit."""
    await state.update_data(full_name=derived_name)
    await message.answer(
        t.CONFIRM_DERIVED_NAME.format(full_name=derived_name, phone=phone),
        reply_markup=confirm_derived_name_keyboard(),
    )


async def _ask_for_surname_after_contact(message: Message, state: FSMContext, first_name: str | None) -> None:
    """Surname missing or unusable: ask for it (tg_first_name already stored upstream)."""
    await state.set_state(Registration.name_only)

    if first_name and is_usable_first_name(first_name):
        await message.answer(t.ASK_SURNAME_AFTER_CONTACT.format(first_name=first_name))
    else:
        await message.answer(t.ASK_FULL_NAME_AFTER_CONTACT)


# ---------------------------------------------------------------------------
# "name_only" step: contact gave phone, but we still need a full name
# ---------------------------------------------------------------------------

@router.message(Registration.name_only, F.text)
async def handle_name_only(message: Message, state: FSMContext) -> None:
    """
    Receive a name while in the name_only state.

    Three callers land here:
    - After a contact share that gave a usable first name but no surname:
      the user only needs to type their SURNAME, which we combine with
      the known first name into "Прізвище Ім'я".
    - After a contact share with no usable name at all: the user types
      their full "Прізвище Ім'я".
    - Editing the name from the preview screen: same as above, but email
      is already known so we return to the preview.
    """
    data = await state.get_data()
    known_first = data.get("tg_first_name")

    full_name = _resolve_name_only_input(message.text, known_first)

    if full_name is None:
        await message.answer(t.INVALID_NAME)
        return

    await state.update_data(full_name=full_name)
    # The first name has now been folded into full_name; drop the hint so
    # a later edit from the preview asks for the full name, not a surname.
    await state.update_data(tg_first_name=None)

    if "email" in data:
        from handlers.registration.confirm import show_profile_preview

        await state.set_state(Registration.confirm)
        await show_profile_preview(message, state)
    else:
        await state.set_state(Registration.email)
        await message.answer(t.ASK_EMAIL)


def _resolve_name_only_input(raw: str, known_first: str | None) -> str | None:
    """
    Turn the user's input at the name_only step into a full name.

    If we already know a usable first name and the user typed a single
    word, treat that word as the surname and combine into "Прізвище Ім'я".
    Otherwise, validate the input as a complete full name.

    Returns the full name, or None if the input is invalid.
    """
    if known_first and is_usable_first_name(known_first):
        surname = normalize_name_part(raw)
        if surname is not None:
            return f"{surname} {known_first.strip()}"
        # Not a single word -> fall through and accept it as a full name
        # (covers the user typing "Прізвище Ім'я" in full anyway).

    return normalize_full_name(raw)


@router.message(Registration.name_only, ~F.text)
async def handle_non_text_at_name_only(message: Message) -> None:
    """Reject non-text input while waiting for a full name."""
    await message.answer(t.NAME_NOT_TEXT)


# ---------------------------------------------------------------------------
# Confirm-derived-name step (inline buttons)
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "reg:name_ok")
async def confirm_derived_name(callback: CallbackQuery, state: FSMContext) -> None:
    """User accepted the name derived from their Telegram contact."""
    await callback.message.edit_reply_markup(reply_markup=None)

    # Phone already known -> skip phone step, go straight to email.
    await state.set_state(Registration.email)
    await callback.message.answer(t.ASK_EMAIL)
    await callback.answer()


@router.callback_query(F.data == "reg:name_edit")
async def edit_derived_name(callback: CallbackQuery, state: FSMContext) -> None:
    """User wants to type their name manually instead of using the derived one."""
    await callback.message.edit_reply_markup(reply_markup=None)

    # Phone stays saved in FSM data; only the name is re-collected.
    await state.set_state(Registration.name_only)
    await callback.message.answer(t.ASK_FULL_NAME_AFTER_CONTACT)
    await callback.answer()


# ---------------------------------------------------------------------------
# Fallback: any interaction outside of a known text/contact branch
# ---------------------------------------------------------------------------

@router.callback_query(Registration.name_or_contact)
async def ignore_unrelated_callback_at_name_step(callback: CallbackQuery) -> None:
    """Defensive: ignore stray callbacks (e.g. stale buttons) at this step."""
    await callback.answer()
