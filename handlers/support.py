"""
Handler for the 💬 Підтримка (support) section.

Replaces the former "Питання лекторці" anonymous-question flow with
three options:
  - Contact the organizer (shows a direct contact link)
  - Ask a question (free text -> forwarded to the support chat)
  - Report a bug (free text -> forwarded to the support chat)

Submissions are forwarded to config.effective_support_chat_id (an admin
chat / the first admin). Unlike the old sexologist flow these are NOT
anonymous — they include the sender so the team can follow up.
"""

import html
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import settings
from keyboards.main_menu import MENU_BUTTONS, MENU_SUPPORT
from keyboards.support import cancel_keyboard, support_menu_keyboard
from states.support import Support
from texts import support as t

router = Router(name="support")

logger = logging.getLogger(__name__)


@router.message(F.text == MENU_SUPPORT)
async def open_support(message: Message) -> None:
    """Show the support menu from the main menu."""
    await message.answer(t.SUPPORT_INTRO, reply_markup=support_menu_keyboard())


@router.callback_query(F.data == "support:close")
async def close_support(callback: CallbackQuery) -> None:
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "support:organizer")
async def contact_organizer(callback: CallbackQuery) -> None:
    """Show the organizer's direct contact."""
    await callback.message.edit_text(
        t.CONTACT_ORGANIZER.format(contact=html.escape(settings.organizer_contact)),
        reply_markup=support_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "support:question")
async def ask_question(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Support.waiting_for_question)
    await callback.message.answer(t.ASK_QUESTION_PROMPT, reply_markup=cancel_keyboard())
    await callback.answer()


@router.callback_query(F.data == "support:bug")
async def report_bug(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Support.waiting_for_bug)
    await callback.message.answer(t.REPORT_BUG_PROMPT, reply_markup=cancel_keyboard())
    await callback.answer()


@router.callback_query(F.data == "support:cancel")
async def cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(t.CANCELLED)
    await callback.answer()


@router.message(Support.waiting_for_question, F.text & ~F.text.in_(MENU_BUTTONS))
async def receive_question(message: Message, state: FSMContext, bot: Bot) -> None:
    """Forward a user's question to the support chat."""
    await state.clear()
    delivered = await _forward(bot, message, t.FWD_QUESTION)
    await message.answer(t.QUESTION_SENT if delivered else t.SUBMISSION_FAILED)


@router.message(Support.waiting_for_bug, F.text & ~F.text.in_(MENU_BUTTONS))
async def receive_bug(message: Message, state: FSMContext, bot: Bot) -> None:
    """Forward a user's bug report to the support chat."""
    await state.clear()
    delivered = await _forward(bot, message, t.FWD_BUG)
    await message.answer(t.BUG_SENT if delivered else t.SUBMISSION_FAILED)


async def _forward(bot: Bot, message: Message, template: str) -> bool:
    """
    Send a formatted submission to the support chat. Returns True on
    success, False if there's no support chat configured or sending fails.
    """
    chat_id = settings.effective_support_chat_id
    if chat_id is None:
        logger.warning("No support chat configured; submission dropped.")
        return False

    user = message.from_user
    user_display = html.escape(user.full_name)
    if user.username:
        user_display += f" (@{user.username})"

    text = template.format(
        user=user_display,
        tg_id=user.id,
        text=html.escape(message.text),
    )

    try:
        await bot.send_message(chat_id, text)
        return True
    except Exception:
        logger.exception("Failed to forward support submission to chat %s", chat_id)
        return False
