"""
Middleware that intercepts any message/callback from a user with no
saved profile and, if they're not already inside the registration FSM,
nudges them to start registration instead of processing the original
update.

IMPORTANT: for CallbackQuery updates, `callback_query.message` is the
BOT's own message (the one with the inline keyboard) — its `from_user`
is the bot, not the person who tapped the button. The actual user is
`callback_query.from_user`. Always resolve the user via this, never via
`message.from_user`, when handling callbacks.
"""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject, Update, User
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud.users import get_user_by_tg_id
from keyboards.registration import name_or_contact_keyboard, start_registration_keyboard
from states.registration import Registration
from texts import registration as t

# Commands that must always pass through, even for unregistered users.
_ALWAYS_ALLOWED_COMMANDS = {"/start"}

# Callback-data prefixes that belong to the registration flow itself and
# must always reach their handler, even before any FSM state is set
# (e.g. the very first "Почати реєстрацію" tap from the welcome screen).
_ALWAYS_ALLOWED_CALLBACK_PREFIXES = ("reg:",)


class RegistrationRequiredMiddleware(BaseMiddleware):
    """Ensures a user has completed registration before using any other feature."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        inner = _unwrap(event)
        if inner is None:
            return await handler(event, data)

        message, callback, user, chat_type = inner

        if chat_type != "private":
            return await handler(event, data)

        if message is not None and message.text in _ALWAYS_ALLOWED_COMMANDS:
            return await handler(event, data)

        if callback is not None and callback.data is not None and callback.data.startswith(
            _ALWAYS_ALLOWED_CALLBACK_PREFIXES
        ):
            return await handler(event, data)

        session: AsyncSession = data["session"]
        state: FSMContext = data["state"]

        existing_user = await get_user_by_tg_id(session, user.id)
        if existing_user is not None:
            return await handler(event, data)

        current_state = await state.get_state()
        if current_state is not None:
            # Already mid-registration -> let the relevant handler process it.
            return await handler(event, data)

        if callback is not None:
            # Don't silently swallow a tap on a stale/foreign inline
            # keyboard for an unregistered user — acknowledge it so
            # Telegram doesn't show a loading spinner.
            await callback.answer()

        target_message = message if message is not None else callback.message
        await _prompt_to_register(target_message, state, is_button_press=message is not None)
        return None


def _unwrap(event: TelegramObject) -> tuple[Message | None, CallbackQuery | None, User, str] | None:
    """
    Normalize a Message or CallbackQuery update into
    (message, callback, user, chat_type), or None if neither applies
    (e.g. edited_message, channel posts, etc. — let those pass through
    unmodified).
    """
    if isinstance(event, Update):
        if event.message is not None:
            msg = event.message
            return msg, None, msg.from_user, msg.chat.type
        if event.callback_query is not None:
            cb = event.callback_query
            chat_type = cb.message.chat.type if cb.message is not None else "private"
            return None, cb, cb.from_user, chat_type
        return None

    if isinstance(event, Message):
        return event, None, event.from_user, event.chat.type

    if isinstance(event, CallbackQuery):
        chat_type = event.message.chat.type if event.message is not None else "private"
        return None, event, event.from_user, chat_type

    return None


async def _prompt_to_register(message: Message, state: FSMContext, is_button_press: bool) -> None:
    """
    Nudge an unregistered, non-mid-flow user toward registration.

    Per the spec: pressing a main-menu button before registering should
    feel like a gentle redirect, not an error.
    """
    if is_button_press:
        await state.set_state(Registration.name_or_contact)
        await message.answer(
            "Спершу завершимо реєстрацію — це швидко! 🙂\n\n" + t.ASK_NAME_OR_CONTACT,
            reply_markup=name_or_contact_keyboard(),
        )
    else:
        await message.answer(t.WELCOME_NEW_USER, reply_markup=start_registration_keyboard())
