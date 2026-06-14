"""
Main persistent reply keyboard, shown to fully registered users.

Kept minimal and separate so other modules (booking, schedule, admin, etc.)
can extend or restyle it without touching registration code.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

MENU_SCHEDULE = "📅 Розклад"
MENU_BOOK = "✍️ Записатись"
MENU_MY_BOOKINGS = "📋 Мої записи"
MENU_CONSULTATION = "🩺 Консультація хірурга"
MENU_QUESTION = "❓ Питання лекторці"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Persistent main menu shown after successful registration."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_SCHEDULE), KeyboardButton(text=MENU_BOOK)],
            [KeyboardButton(text=MENU_MY_BOOKINGS)],
            [KeyboardButton(text=MENU_CONSULTATION), KeyboardButton(text=MENU_QUESTION)],
        ],
        resize_keyboard=True,
    )
