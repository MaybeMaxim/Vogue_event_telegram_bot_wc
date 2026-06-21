from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from texts.question import CANCEL_BUTTON


def question_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=CANCEL_BUTTON, callback_data="question:cancel")]]
    )
