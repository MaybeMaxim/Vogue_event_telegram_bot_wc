"""Keyboard builders for the 💬 Підтримка (support) section."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from texts import support as t


def support_menu_keyboard() -> InlineKeyboardMarkup:
    """Three support options + close."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.CONTACT_ORGANIZER_BUTTON, callback_data="support:organizer")],
            [InlineKeyboardButton(text=t.ASK_QUESTION_BUTTON, callback_data="support:question")],
            [InlineKeyboardButton(text=t.REPORT_BUG_BUTTON, callback_data="support:bug")],
            [InlineKeyboardButton(text=t.CLOSE_BUTTON, callback_data="support:close")],
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel button shown while waiting for a question / bug description."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.CANCEL_BUTTON, callback_data="support:cancel")]
        ]
    )
