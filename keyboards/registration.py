"""
Keyboard builders for the registration / onboarding flow.

Keeping these separate from handlers makes it trivial to restyle
buttons (emoji, layout, wording) without touching any business logic.
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from texts import registration as t


def start_registration_keyboard() -> InlineKeyboardMarkup:
    """Inline button shown on the welcome screen for new users."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.START_REGISTRATION_BUTTON, callback_data="reg:start")]
        ]
    )


def group_chat_redirect_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Deep-link button to open a private chat with the bot, for group-chat /start."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t.GROUP_CHAT_REDIRECT_BUTTON,
                    url=f"https://t.me/{bot_username}?start=register",
                )
            ]
        ]
    )


def name_or_contact_keyboard() -> ReplyKeyboardMarkup:
    """
    Step 1 keyboard: lets the user share their contact instead of typing a name.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.SHARE_CONTACT_BUTTON, request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def phone_request_keyboard() -> ReplyKeyboardMarkup:
    """Step 2 keyboard: request the user's phone number via contact share."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.SEND_PHONE_BUTTON, request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    """Used to hide the contact-share keyboard once a value has been captured."""
    return ReplyKeyboardRemove()


def confirm_derived_name_keyboard() -> InlineKeyboardMarkup:
    """
    Shown when a contact share gave us both first and last name —
    user confirms or chooses to type the name manually instead.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.CONFIRM_DERIVED_NAME_YES, callback_data="reg:name_ok")],
            [InlineKeyboardButton(text=t.CONFIRM_DERIVED_NAME_EDIT_NAME, callback_data="reg:name_edit")],
        ]
    )


def profile_preview_keyboard() -> InlineKeyboardMarkup:
    """
    Final preview screen: confirm & save, or edit any individual field.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.CONFIRM_SAVE_BUTTON, callback_data="reg:save")],
            [
                InlineKeyboardButton(text=t.EDIT_NAME_BUTTON, callback_data="reg:edit_name"),
                InlineKeyboardButton(text=t.EDIT_PHONE_BUTTON, callback_data="reg:edit_phone"),
            ],
            [InlineKeyboardButton(text=t.EDIT_EMAIL_BUTTON, callback_data="reg:edit_email")],
        ]
    )
