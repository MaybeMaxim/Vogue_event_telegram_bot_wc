"""
Handler for the "✍️ Записатись" booking drill-down.

Navigation:
  "✍️ Записатись" -> day picker
  bookday:{day}   -> slot picker for that day
  bookslot:{day}:{anchor_id} -> activity picker for that slot
  bookact / bookwait -> (placeholder) book / join waitlist
  bookconsult:{day}  -> (placeholder) consultation slot picker
  bookdays           -> back to day picker

Booking ACTIONS (conflict/limit/capacity checks, creating bookings) and
the consultation slot picker are added in later steps; the bookact/
bookwait/bookconsult callbacks currently show a placeholder alert.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud.activities import get_activities_for_day, get_activity_by_id, get_activities_in_slot
from keyboards.booking import (
    activity_picker_keyboard,
    day_label,
    day_picker_keyboard,
    slot_picker_keyboard,
)
from keyboards.main_menu import MENU_BOOK
from services.booking_service import Slot, group_into_slots, render_activity_picker, render_slot_picker
from texts import booking as t

router = Router(name="booking")


@router.message(F.text == MENU_BOOK)
async def show_day_picker(message: Message) -> None:
    """Entry point: choose which day to book on."""
    await message.answer(t.BOOK_INTRO, reply_markup=day_picker_keyboard())


@router.callback_query(F.data == "bookdays")
async def back_to_day_picker(callback: CallbackQuery) -> None:
    """Back to the day picker."""
    await callback.message.edit_text(t.BOOK_INTRO, reply_markup=day_picker_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("bookday:"))
async def show_slot_picker(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show the time-slot picker for the chosen day."""
    day = int(callback.data.split(":")[1])

    activities = await get_activities_for_day(session, day)
    if not activities:
        await callback.message.edit_text(t.NO_ACTIVITIES_FOR_DAY, reply_markup=day_picker_keyboard())
        await callback.answer()
        return

    slots = group_into_slots(activities)
    text = render_slot_picker(day, day_label(day), slots)

    await callback.message.edit_text(text, reply_markup=slot_picker_keyboard(day, slots))
    await callback.answer()


@router.callback_query(F.data.startswith("bookslot:"))
async def show_activity_picker(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show the activities within one chosen time slot."""
    _, day_str, anchor_id_str = callback.data.split(":")
    day = int(day_str)
    anchor_id = int(anchor_id_str)

    anchor = await get_activity_by_id(session, anchor_id)
    if anchor is None:
        await callback.answer(t.NO_ACTIVITIES_FOR_DAY, show_alert=True)
        return

    slot_activities = await get_activities_in_slot(session, day, anchor.start_time, anchor.end_time)
    slot = Slot(
        start_time=anchor.start_time,
        end_time=anchor.end_time,
        activities=slot_activities,
        is_consultation=False,
    )

    text = render_activity_picker(slot)
    await callback.message.edit_text(text, reply_markup=activity_picker_keyboard(day, slot))
    await callback.answer()


@router.callback_query(F.data.startswith("bookact:") | F.data.startswith("bookwait:"))
async def book_placeholder(callback: CallbackQuery) -> None:
    """Placeholder for the booking action (added in the next step)."""
    await callback.answer(t.BOOKING_COMING_SOON, show_alert=True)


@router.callback_query(F.data.startswith("bookconsult:"))
async def consultation_placeholder(callback: CallbackQuery) -> None:
    """Placeholder for the consultation slot picker (added in the next step)."""
    await callback.answer(t.CONSULTATION_COMING_SOON, show_alert=True)
