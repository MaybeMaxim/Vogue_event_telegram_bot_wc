"""
Handler for the "📅 Розклад" main menu section.

Flow:
  main menu "📅 Розклад" -> day picker (Day 1 / Day 2)
  -> tap a day -> full schedule for that day, with per-activity
     "Записатись" / "У лист очікування" buttons and a button to
     switch back to the day picker.

The card-rendering logic in services.schedule_service and the keyboard
in keyboards.schedule.day_view_keyboard are reused as-is by the booking
flow once it's implemented — the booking/waitlist callbacks below are
placeholders until then.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud.activities import get_activities_for_day
from keyboards.main_menu import MENU_SCHEDULE
from keyboards.schedule import day_label, day_picker_keyboard, day_view_keyboard
from services.schedule_service import render_day_schedule
from texts import schedule as t

router = Router(name="schedule")


@router.message(F.text == MENU_SCHEDULE)
async def show_day_picker(message: Message) -> None:
    """User opened the schedule section: ask which day to view."""
    await message.answer(t.SCHEDULE_INTRO, reply_markup=day_picker_keyboard())


@router.callback_query(F.data == "schedule:days")
async def back_to_day_picker(callback: CallbackQuery) -> None:
    """User wants to switch days: re-show the day picker."""
    await callback.message.edit_text(t.SCHEDULE_INTRO, reply_markup=day_picker_keyboard())
    await callback.answer()


@router.callback_query(F.data.in_({"schedule:day:1", "schedule:day:2"}))
async def show_day_schedule(callback: CallbackQuery, session: AsyncSession) -> None:
    """Render the full schedule for the selected day, with booking buttons."""
    day = int(callback.data.rsplit(":", 1)[-1])

    activities = await get_activities_for_day(session, day)
    text = render_day_schedule(day, day_label(day), activities)

    await callback.message.edit_text(text, reply_markup=day_view_keyboard(activities))
    await callback.answer()


@router.callback_query(F.data.startswith("book:") | F.data.startswith("waitlist:"))
async def booking_coming_soon(callback: CallbackQuery) -> None:
    """
    Placeholder until the booking flow (conflict checks, capacity locks,
    waitlist) is implemented. Reachable from the per-activity buttons in
    day_view_keyboard.
    """
    await callback.answer(t.BOOKING_COMING_SOON, show_alert=True)
