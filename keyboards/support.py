"""Keyboard builders for the 💬 Підтримка (support) section."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from texts import support as t


def support_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.CONTACT_ORGANIZER_BUTTON, callback_data="support:organizer")],
            [InlineKeyboardButton(text=t.ASK_SEXOLOGIST_BUTTON, callback_data="support:sexologist")],
            [InlineKeyboardButton(text=t.REPORT_BUG_BUTTON, callback_data="support:bug")],
            [InlineKeyboardButton(text=t.CLOSE_BUTTON, callback_data="support:close")],
        ]
    )


def organizer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.SEND_MESSAGE_BUTTON, callback_data="support:org_message")],
            [InlineKeyboardButton(text=t.BACK_BUTTON, callback_data="support:back")],
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.CANCEL_BUTTON, callback_data="support:cancel")]
        ]
    )
