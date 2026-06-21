"""
Handler for the 💬 Підтримка (support) section.

Options:
  - Contact organizers: shows Veronika's number + FSM "send message"
  - Ask sexologist: redirects to the anonymous Q&A flow (question.py)
  - Report a mistake: free text -> forwarded to the support chat
"""

import html
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.crud.support import add_support_message
from keyboards.main_menu import MENU_BUTTONS, MENU_SUPPORT
from keyboards.support import cancel_keyboard, organizer_keyboard, support_menu_keyboard
from keyboards.question import question_cancel_keyboard
from states.question import QuestionFlow
from states.support import Support
from texts import support as t
from texts import question as tq

router = Router(name="support")
logger = logging.getLogger(__name__)


def _mark_sheets_dirty() -> None:
    try:
        from services.sheets_service import mark_dirty
        mark_dirty()
    except Exception:
        pass


@router.message(F.text == MENU_SUPPORT)
async def open_support(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(t.SUPPORT_INTRO, reply_markup=support_menu_keyboard())


@router.callback_query(F.data == "support:back")
async def back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await callback.message.edit_text(t.SUPPORT_INTRO, reply_markup=support_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "support:close")
async def close_support(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "support:sexologist")
async def start_sexologist_question(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(QuestionFlow.waiting_for_text)
    await callback.message.edit_text(tq.INTRO, reply_markup=question_cancel_keyboard())
    await callback.answer()


@router.callback_query(F.data == "support:organizer")
async def contact_organizer(callback: CallbackQuery) -> None:
    try:
        await callback.message.edit_text(
            t.CONTACT_ORGANIZER.format(contact=html.escape(settings.organizer_contact)),
            reply_markup=organizer_keyboard(),
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "support:org_message")
async def start_org_message(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Support.waiting_for_org_message)
    await callback.message.edit_text(t.ORG_MESSAGE_PROMPT, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(Support.waiting_for_org_message, F.text & ~F.text.in_(MENU_BUTTONS))
async def receive_org_message(message: Message, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    await state.clear()
    user = message.from_user
    await add_support_message(session, user.id, user.full_name, user.username, "org", message.text)
    _mark_sheets_dirty()
    delivered = await _forward(bot, message, t.FWD_ORG)
    await message.answer(t.ORG_MESSAGE_SENT if delivered else t.SUBMISSION_FAILED)



@router.callback_query(F.data == "support:bug")
async def report_bug(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Support.waiting_for_bug)
    await callback.message.edit_text(t.REPORT_BUG_PROMPT, reply_markup=cancel_keyboard())
    await callback.answer()


@router.callback_query(F.data == "support:cancel")
async def cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await callback.message.edit_text(t.SUPPORT_INTRO, reply_markup=support_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message(Support.waiting_for_bug, F.text & ~F.text.in_(MENU_BUTTONS))
async def receive_bug(message: Message, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    await state.clear()
    user = message.from_user
    await add_support_message(session, user.id, user.full_name, user.username, "bug", message.text)
    _mark_sheets_dirty()
    delivered = await _forward(bot, message, t.FWD_BUG)
    await message.answer(t.BUG_SENT if delivered else t.SUBMISSION_FAILED)


async def _forward(bot: Bot, message: Message, template: str) -> bool:
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
