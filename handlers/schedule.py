"""
Handler for the "📅 Розклад" main menu section (read-only).

Flow:
  "📅 Розклад" -> day picker -> tap a day -> static schedule for that day
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from keyboards.main_menu import MENU_SCHEDULE
from keyboards.schedule import day_picker_keyboard, day_view_keyboard
from services.schedule_service import render_day_schedule
from texts import schedule as t

router = Router(name="schedule")


@router.message(F.text == MENU_SCHEDULE)
async def show_day_picker(message: Message) -> None:
    await message.answer(t.SCHEDULE_INTRO, reply_markup=day_picker_keyboard())


@router.callback_query(F.data == "schedule:days")
async def back_to_day_picker(callback: CallbackQuery) -> None:
    await callback.message.edit_text(t.SCHEDULE_INTRO, reply_markup=day_picker_keyboard())
    await callback.answer()


@router.callback_query(F.data.in_({"schedule:day:1", "schedule:day:2"}))
async def show_day_schedule(callback: CallbackQuery) -> None:
    day = int(callback.data.rsplit(":", 1)[-1])
    text = render_day_schedule(day)
    await callback.message.edit_text(text, reply_markup=day_view_keyboard())
    await callback.answer()
