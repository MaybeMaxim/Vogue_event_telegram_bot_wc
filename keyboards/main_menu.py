"""
Main persistent reply keyboard, shown to fully registered users.

Kept minimal and separate so other modules (booking, schedule, profile,
admin, etc.) can extend or restyle it without touching registration code.

Consultations are NOT a separate menu item — they're booked through
"✍️ Записатись" like any other activity (they're just a day-2 slot).
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

MENU_SCHEDULE = "📅 Розклад"
MENU_BOOK = "✍️ Записатись"
MENU_MY_BOOKINGS = "📋 Мої записи"
MENU_SUPPORT = "💬 Підтримка"
MENU_PROFILE = "⚙️ Профіль"

# All main-menu button labels, used to detect when a user taps the menu
# (so any in-progress FSM flow, e.g. profile editing, can be cancelled
# before the menu handler runs).
MENU_BUTTONS = frozenset(
    {MENU_SCHEDULE, MENU_BOOK, MENU_MY_BOOKINGS, MENU_SUPPORT, MENU_PROFILE}
)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Persistent main menu shown after successful registration."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_SCHEDULE), KeyboardButton(text=MENU_BOOK)],
            [KeyboardButton(text=MENU_MY_BOOKINGS)],
            [KeyboardButton(text=MENU_SUPPORT), KeyboardButton(text=MENU_PROFILE)],
        ],
        resize_keyboard=True,
    )
