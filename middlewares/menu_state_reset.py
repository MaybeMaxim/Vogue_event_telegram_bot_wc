"""
Middleware that cancels any in-progress FSM flow when the user taps a
main-menu reply-keyboard button.

Without this, tapping e.g. "📅 Розклад" while in the middle of editing a
profile field would leave the edit state active, so the user's next
message would be misinterpreted as the field value. Clearing the state
here — before any handler runs — guarantees menu navigation always
escapes whatever flow the user was in.

Registration is exempt: while a user is registering (no profile yet),
menu buttons are handled by the registration middleware instead, and we
don't want to drop their half-entered registration data.
"""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject, Update

from keyboards.main_menu import MENU_BUTTONS
from states.registration import Registration


class MenuStateResetMiddleware(BaseMiddleware):
    """Clears non-registration FSM state when a main-menu button is tapped."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        message = _extract_message(event)

        if message is not None and message.text in MENU_BUTTONS:
            state: FSMContext = data["state"]
            current = await state.get_state()
            if current is not None and not _is_registration_state(current):
                await state.clear()

        return await handler(event, data)


def _extract_message(event: TelegramObject) -> Message | None:
    """Return the Message for a message Update, or None for anything else."""
    if isinstance(event, Update):
        return event.message
    if isinstance(event, Message):
        return event
    return None


def _is_registration_state(state_str: str) -> bool:
    """True if the given state string belongs to the registration flow."""
    return state_str.startswith(Registration.__name__ + ":")
