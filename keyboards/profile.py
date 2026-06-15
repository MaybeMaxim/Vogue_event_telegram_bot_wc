"""Keyboard builder for the ⚙️ Профіль view."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from texts import profile as t


def profile_keyboard() -> InlineKeyboardMarkup:
    """Edit buttons + a 'done' button for the profile view."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.EDIT_NAME_BUTTON, callback_data="profile:edit_name")],
            [InlineKeyboardButton(text=t.EDIT_PHONE_BUTTON, callback_data="profile:edit_phone")],
            [InlineKeyboardButton(text=t.EDIT_EMAIL_BUTTON, callback_data="profile:edit_email")],
            [InlineKeyboardButton(text=t.CLOSE_BUTTON, callback_data="profile:close")],
        ]
    )


def cancel_edit_keyboard() -> InlineKeyboardMarkup:
    """Single 'cancel' button shown while waiting for a new field value."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.CANCEL_EDIT_BUTTON, callback_data="profile:cancel_edit")]
        ]
    )
