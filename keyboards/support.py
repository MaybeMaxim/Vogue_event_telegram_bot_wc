"""Keyboard builders for the 💬 Підтримка (support) section."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from texts import support as t


def support_menu_keyboard() -> InlineKeyboardMarkup:
    """Two support options + close."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.CONTACT_ORGANIZER_BUTTON, callback_data="support:organizer")],
            [InlineKeyboardButton(text=t.REPORT_BUG_BUTTON, callback_data="support:bug")],
            [InlineKeyboardButton(text=t.CLOSE_BUTTON, callback_data="support:close")],
        ]
    )


def organizer_keyboard() -> InlineKeyboardMarkup:
    """Back button on the organizer contact screen."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.BACK_BUTTON, callback_data="support:back")],
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel button shown while the user is typing a bug report."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.CANCEL_BUTTON, callback_data="support:cancel")]
        ]
    )
