"""
Handler for the anonymous sexologist Q&A feature.

Flow:
  menu tap -> check deadline -> show prompt + cancel button
  user sends text -> store in DB (tg_id only) -> forward anonymously to support chat
"""

import html
import logging
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.crud.support import add_question
from keyboards.main_menu import MENU_BUTTONS
from keyboards.question import question_cancel_keyboard
from states.question import QuestionFlow
from texts import question as t

router = Router(name="question")
logger = logging.getLogger(__name__)

_MAX_LEN = 1000


def _deadline_passed() -> bool:
    """True if the submission deadline (naive UTC from config) has passed."""
    try:
        deadline = datetime.strptime(settings.sexologist_question_deadline, "%Y-%m-%d %H:%M")
    except ValueError:
        return False
    return datetime.utcnow() > deadline


@router.callback_query(F.data == "question:cancel")
async def cancel_question(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.delete()
    await callback.answer()


@router.message(QuestionFlow.waiting_for_text, F.text & ~F.text.in_(MENU_BUTTONS))
async def receive_question(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    await state.clear()

    text = (message.text or "").strip()
    if len(text) > _MAX_LEN:
        await message.answer(t.QUESTION_TOO_LONG)
        return

    await add_question(session, message.from_user.id, text)
    try:
        from services.sheets_service import mark_dirty
        mark_dirty()
    except Exception:
        pass

    delivered = await _forward(bot, text)
    await message.answer(t.QUESTION_SENT if delivered else t.SEND_FAILED)


async def _forward(bot: Bot, text: str) -> bool:
    chat_id = settings.effective_support_chat_id
    if chat_id is None:
        logger.warning("No support chat configured; question dropped.")
        return False
    try:
        await bot.send_message(chat_id, t.FWD_QUESTION.format(text=html.escape(text)))
        return True
    except Exception:
        logger.exception("Failed to forward question to chat %s", chat_id)
        return False
