"""
Admin panel handler.

Entry: /admin (admins only, gated by filters.admin.IsAdmin).

Sections:
  - Participants per activity (+ tap a guest to toggle attendance)
  - Waitlists per activity
  - Guest search (by name / phone) -> guest card with cancel buttons
  - Manual add (pick activity -> search guest -> add)
  - Export (participants workbook / contacts workbook as .xlsx)

All callbacks are namespaced `adm:*`. The admin FSM search/add states
store the picked activity in FSM data.
"""

import html
from datetime import datetime
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud import admin as admin_crud
from db.crud.activities import get_activity_by_id
from db.crud.admins import add_admin, list_admins, remove_admin
from db.crud.bookings import get_booking_by_id
from db.crud.users import get_user_by_tg_id
from filters.admin import IsAdmin, add_admin_to_cache, is_admin, remove_admin_from_cache
from keyboards.admin import (
    activity_list_keyboard,
    add_guest_results_keyboard,
    admin_menu_keyboard,
    back_to_menu_keyboard,
    export_menu_keyboard,
    guest_card_keyboard,
    participants_keyboard,
)
from services import booking_actions as actions
from services import export_service
from states.admin import AdminAdd, AdminSearch
from texts import admin as t
from utils.time_utils import format_time, format_time_range

router = Router(name="admin")
# Gate every handler in this router behind the admin check.
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ---------------------------------------------------------------------------
# Entry + menu
# ---------------------------------------------------------------------------

@router.message(Command("admin"))
async def open_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(t.ADMIN_MENU, reply_markup=admin_menu_keyboard())


@router.callback_query(F.data == "adm:menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(t.ADMIN_MENU, reply_markup=admin_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm:close")
async def close_admin(callback: CallbackQuery) -> None:
    await callback.message.delete()
    await callback.answer()


# ---------------------------------------------------------------------------
# Participants
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "adm:participants")
async def participants_pick(callback: CallbackQuery, session: AsyncSession) -> None:
    activities = await admin_crud.regular_activities(session)
    await callback.message.edit_text(
        t.PICK_ACTIVITY,
        reply_markup=activity_list_keyboard(activities, "participants", include_consultations=True),
    )
    await callback.answer()


@router.callback_query(F.data == "adm:participants:consult")
async def participants_consult(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show all consultation participants together (one combined list)."""
    rows = await admin_crud.consultation_participants(session)
    consult_slots = await admin_crud.consultation_activities(session)

    header = t.CONSULT_PARTICIPANTS_HEADER.format(count=len(rows), total=len(consult_slots))

    if not rows:
        await callback.message.edit_text(header + "\n" + t.PARTICIPANTS_EMPTY, reply_markup=back_to_menu_keyboard())
        await callback.answer()
        return

    from db.models import BookingStatus

    lines = [header]
    kb_rows = []
    for booking, user, activity in rows:
        mark = t.ATTENDED_MARK if booking.status == BookingStatus.ATTENDED else t.NOT_ATTENDED_MARK
        lines.append(
            t.CONSULT_PARTICIPANT_LINE.format(
                time=format_time(activity.start_time),
                mark=mark,
                name=html.escape(user.full_name),
                phone=html.escape(user.phone),
            )
        )
        kb_rows.append(
            [InlineKeyboardButton(
                text=f"{mark} {format_time(activity.start_time)} {_truncate_name(user.full_name)}",
                callback_data=f"adm:att:{booking.id}",
            )]
        )
    lines.append(t.TOGGLE_HINT)

    kb_rows.append([InlineKeyboardButton(text=t.BTN_BACK, callback_data="adm:participants")])
    await callback.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await callback.answer()


def _truncate_name(name: str, n: int = 22) -> str:
    return name if len(name) <= n else name[: n - 1].rstrip() + "…"


@router.callback_query(F.data.startswith("adm:participants:act:"))
async def participants_show(callback: CallbackQuery, session: AsyncSession) -> None:
    activity_id = int(callback.data.rsplit(":", 1)[-1])
    await _render_participants(callback, session, activity_id)
    await callback.answer()


async def _render_participants(callback: CallbackQuery, session: AsyncSession, activity_id: int) -> None:
    activity = await get_activity_by_id(session, activity_id)
    if activity is None:
        await callback.message.edit_text(t.PARTICIPANTS_EMPTY, reply_markup=back_to_menu_keyboard())
        return

    participants = await admin_crud.participants_for_activity(session, activity_id)

    header = t.PARTICIPANTS_HEADER.format(
        title=html.escape(activity.title),
        time_range=format_time_range(activity.start_time, activity.end_time),
        count=len(participants),
        capacity=activity.capacity,
    )

    if not participants:
        await callback.message.edit_text(
            header + "\n" + t.PARTICIPANTS_EMPTY, reply_markup=back_to_menu_keyboard()
        )
        return

    from db.models import BookingStatus

    lines = [header]
    for i, (booking, user) in enumerate(participants, start=1):
        mark = t.ATTENDED_MARK if booking.status == BookingStatus.ATTENDED else t.NOT_ATTENDED_MARK
        lines.append(
            t.PARTICIPANT_LINE.format(idx=i, mark=mark, name=html.escape(user.full_name), phone=html.escape(user.phone))
        )
    lines.append(t.TOGGLE_HINT)

    await callback.message.edit_text(
        "\n".join(lines), reply_markup=participants_keyboard(activity_id, participants)
    )


@router.callback_query(F.data.startswith("adm:att:"))
async def toggle_attendance(callback: CallbackQuery, session: AsyncSession) -> None:
    """Toggle a booking's ATTENDED status, then re-render that activity's list."""
    from db.models import BookingStatus

    booking_id = int(callback.data.rsplit(":", 1)[-1])
    booking = await get_booking_by_id(session, booking_id)
    if booking is None:
        await callback.answer()
        return

    now_attended = booking.status == BookingStatus.ATTENDED
    await admin_crud.set_attendance(session, booking, attended=not now_attended)
    from services.sheets_service import mark_dirty
    mark_dirty()
    await callback.answer()

    activity = await get_activity_by_id(session, booking.activity_id)
    if activity is not None and activity.is_consultation_slot:
        await participants_consult(callback, session)
    else:
        await _render_participants(callback, session, booking.activity_id)


# ---------------------------------------------------------------------------
# Waitlists
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "adm:waitlists")
async def waitlists_pick(callback: CallbackQuery, session: AsyncSession) -> None:
    activities = await admin_crud.regular_activities(session)
    await callback.message.edit_text(
        t.PICK_ACTIVITY,
        reply_markup=activity_list_keyboard(activities, "waitlists", include_consultations=True),
    )
    await callback.answer()


@router.callback_query(F.data == "adm:waitlists:consult")
async def waitlists_consult(callback: CallbackQuery, session: AsyncSession) -> None:
    """Combined waitlist view across all consultation slots."""
    from db.models import WaitlistStatus

    consult_slots = await admin_crud.consultation_activities(session)
    lines = [t.WAITLIST_HEADER.format(title="Консультації Анни Баринової", time_range="")]
    found = False
    for activity in consult_slots:
        entries = await admin_crud.waitlist_for_activity(session, activity.id)
        for i, (entry, user) in enumerate(entries, start=1):
            found = True
            status = t.WL_STATUS_OFFERED if entry.status == WaitlistStatus.OFFERED else t.WL_STATUS_WAITING
            lines.append(
                f"🕒 {format_time(activity.start_time)} — <b>{html.escape(user.full_name)}</b> "
                f"📱 {html.escape(user.phone)} {status}"
            )
    if not found:
        lines.append(t.WAITLIST_EMPTY)
    await callback.message.edit_text("\n".join(lines), reply_markup=back_to_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:waitlists:act:"))
async def waitlists_show(callback: CallbackQuery, session: AsyncSession) -> None:
    from db.models import WaitlistStatus

    activity_id = int(callback.data.rsplit(":", 1)[-1])
    activity = await get_activity_by_id(session, activity_id)
    entries = await admin_crud.waitlist_for_activity(session, activity_id)

    header = t.WAITLIST_HEADER.format(
        title=html.escape(activity.title),
        time_range=format_time_range(activity.start_time, activity.end_time),
    )

    if not entries:
        await callback.message.edit_text(header + "\n" + t.WAITLIST_EMPTY, reply_markup=back_to_menu_keyboard())
        await callback.answer()
        return

    lines = [header]
    for i, (entry, user) in enumerate(entries, start=1):
        status = t.WL_STATUS_OFFERED if entry.status == WaitlistStatus.OFFERED else t.WL_STATUS_WAITING
        lines.append(
            t.WAITLIST_LINE.format(idx=i, name=html.escape(user.full_name), phone=html.escape(user.phone), status=status)
        )

    await callback.message.edit_text("\n".join(lines), reply_markup=back_to_menu_keyboard())
    await callback.answer()


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "adm:search")
async def search_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminSearch.waiting_for_query)
    await callback.message.answer(t.SEARCH_PROMPT, reply_markup=back_to_menu_keyboard())
    await callback.answer()


@router.message(AdminSearch.waiting_for_query, F.text)
async def search_run(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    query = message.text.strip()
    guests = await admin_crud.search_guests(session, query)

    if not guests:
        await message.answer(t.SEARCH_EMPTY.format(query=html.escape(query)), reply_markup=admin_menu_keyboard())
        return

    await message.answer(t.SEARCH_RESULT_HEADER.format(count=len(guests)))
    for guest in guests:
        await _send_guest_card(message, session, guest.id)


async def _send_guest_card(message: Message, session: AsyncSession, user_pk: int) -> None:
    from sqlalchemy import select
    from db.models import User

    guest = (await session.execute(select(User).where(User.id == user_pk))).scalar_one_or_none()
    if guest is None:
        return

    bookings = await admin_crud.guest_bookings(session, user_pk)
    if bookings:
        booking_lines = "\n".join(
            t.GUEST_BOOKING_LINE.format(day=a.day, time=format_time(a.start_time), title=html.escape(a.title))
            for _, a in bookings
        )
    else:
        booking_lines = t.GUEST_NO_BOOKINGS

    text = t.GUEST_CARD.format(
        name=html.escape(guest.full_name),
        phone=html.escape(guest.phone),
        email=html.escape(guest.email),
        bookings=booking_lines,
    )
    await message.answer(text, reply_markup=guest_card_keyboard(bookings))


@router.callback_query(F.data.startswith("adm:cancelbk:"))
async def admin_cancel_booking(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    """Admin cancels a guest's booking; frees the seat and promotes the waitlist."""
    booking_id = int(callback.data.rsplit(":", 1)[-1])
    booking = await get_booking_by_id(session, booking_id)
    if booking is None:
        await callback.answer(t.CANCELLED_OK, show_alert=True)
        return

    freed = await actions.cancel_booking(session, booking)
    await callback.answer(t.CANCELLED_OK)
    await callback.message.edit_text(t.CANCELLED_OK, reply_markup=back_to_menu_keyboard())

    if freed is not None:
        from handlers.booking import _promote_waitlist

        await _promote_waitlist(session, bot, freed.id)


# ---------------------------------------------------------------------------
# Manual add
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "adm:add")
async def add_pick_activity(callback: CallbackQuery, session: AsyncSession) -> None:
    activities = await admin_crud.all_activities(session)
    await callback.message.edit_text(
        t.ADD_PICK_ACTIVITY, reply_markup=activity_list_keyboard(activities, "add")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:add:act:"))
async def add_ask_guest(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    activity_id = int(callback.data.rsplit(":", 1)[-1])
    activity = await get_activity_by_id(session, activity_id)
    if activity is None:
        await callback.answer()
        return

    await state.set_state(AdminAdd.waiting_for_query)
    await state.update_data(add_activity_id=activity_id)
    await callback.message.answer(
        t.ADD_SEARCH_PROMPT.format(title=html.escape(activity.title)),
        reply_markup=back_to_menu_keyboard(),
    )
    await callback.answer()


@router.message(AdminAdd.waiting_for_query, F.text)
async def add_search(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    activity_id = data.get("add_activity_id")
    await state.clear()

    activity = await get_activity_by_id(session, activity_id) if activity_id else None
    if activity is None:
        await message.answer(t.PARTICIPANTS_EMPTY, reply_markup=admin_menu_keyboard())
        return

    guests = await admin_crud.search_guests(session, message.text.strip())
    if not guests:
        await message.answer(
            t.SEARCH_EMPTY.format(query=html.escape(message.text.strip())),
            reply_markup=admin_menu_keyboard(),
        )
        return

    await message.answer(
        t.ADD_PICK_GUEST, reply_markup=add_guest_results_keyboard(activity_id, guests)
    )


@router.callback_query(F.data.startswith("adm:addto:"))
async def add_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    """Add a chosen guest to a chosen activity (admin override: bypasses capacity)."""
    _, _, activity_id_str, user_pk_str = callback.data.split(":")
    activity_id, user_pk = int(activity_id_str), int(user_pk_str)

    activity = await get_activity_by_id(session, activity_id)
    if activity is None:
        await callback.answer()
        return

    from db.crud.bookings import create_booking, find_time_conflict, get_active_booking, count_occupied_seats
    from sqlalchemy import select
    from db.models import User

    guest = (await session.execute(select(User).where(User.id == user_pk))).scalar_one_or_none()
    if guest is None:
        await callback.answer()
        return

    name = html.escape(guest.full_name)

    if await get_active_booking(session, user_pk, activity_id) is not None:
        await callback.message.edit_text(
            t.ADD_ALREADY.format(title=html.escape(activity.title)), reply_markup=back_to_menu_keyboard()
        )
        await callback.answer()
        return

    conflict = await find_time_conflict(session, user_pk, activity.start_time, activity.end_time)
    if conflict is not None:
        conflict_activity = await get_activity_by_id(session, conflict.activity_id)
        await callback.message.edit_text(
            t.ADD_CONFLICT.format(conflict=html.escape(conflict_activity.title)),
            reply_markup=back_to_menu_keyboard(),
        )
        await callback.answer()
        return

    occupied = await count_occupied_seats(session, activity_id)
    await create_booking(session, user_pk, activity_id)
    from services.sheets_service import mark_dirty
    mark_dirty()

    msg = t.ADDED_OK.format(name=name, title=html.escape(activity.title))
    if occupied >= activity.capacity:
        msg += "\n" + t.ADD_FULL_FORCED
    await callback.message.edit_text(msg, reply_markup=back_to_menu_keyboard())
    await callback.answer()


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "adm:export")
async def export_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(t.EXPORT_MENU, reply_markup=export_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm:exp:participants")
async def export_participants(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer(t.EXPORT_GENERATING)
    path = await export_service.build_participants_workbook(session)
    await _send_export(callback, path, t.EXPORT_PARTICIPANTS_CAPTION)


@router.callback_query(F.data == "adm:exp:contacts")
async def export_contacts(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer(t.EXPORT_GENERATING)
    path = await export_service.build_contacts_workbook(session)
    await _send_export(callback, path, t.EXPORT_CONTACTS_CAPTION)


@router.callback_query(F.data == "adm:exp:gsheet")
async def export_gsheet_link(callback: CallbackQuery) -> None:
    """Give the admin the live Google Sheet URL (forces a sync first)."""
    from services.sheets_service import get_spreadsheet_url, mark_dirty, sync_if_dirty

    await callback.answer(t.EXPORT_GENERATING)
    mark_dirty()
    await sync_if_dirty()
    url = await get_spreadsheet_url()

    if url:
        await callback.message.answer(t.GSHEET_LINK.format(url=url), reply_markup=back_to_menu_keyboard())
    else:
        await callback.message.answer(t.GSHEET_UNAVAILABLE, reply_markup=back_to_menu_keyboard())


async def _send_export(callback: CallbackQuery, path: Path, caption_template: str) -> None:
    stamp = datetime.now().strftime("%d.%m.%Y %H:%M")
    await callback.message.answer_document(
        FSInputFile(path), caption=caption_template.format(stamp=stamp)
    )
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Admin management
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "adm:admins")
async def show_admins(callback: CallbackQuery, session: AsyncSession) -> None:
    db_admins = await list_admins(session)
    lines = ["👥 <b>Адміністратори</b>\n"]
    lines.append("<b>З config (.env):</b>")
    from config import settings
    for tg_id in settings.admin_ids:
        lines.append(f"  • <code>{tg_id}</code>")
    if db_admins:
        lines.append("\n<b>Додані через бота:</b>")
        for a in db_admins:
            lines.append(f"  • <code>{a.tg_id}</code> (додав <code>{a.added_by_tg_id}</code>)")
    else:
        lines.append("\n<i>Через бота не додано жодного.</i>")
    lines.append(
        "\n<b>Як додати:</b> надішліть /addadmin <code>&lt;tg_id&gt;</code>\n"
        "<b>Як видалити:</b> /removeadmin <code>&lt;tg_id&gt;</code>\n"
        "<b>Дізнатись свій ID:</b> /myid"
    )
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_menu_keyboard(),
    )
    await callback.answer()


@router.message(Command("addadmin"))
async def cmd_add_admin(message: Message, session: AsyncSession) -> None:
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].lstrip("-").isdigit():
        await message.answer("Використання: /addadmin <code>&lt;tg_id&gt;</code>")
        return
    tg_id = int(parts[1])
    if is_admin(tg_id):
        await message.answer(f"<code>{tg_id}</code> вже є адміністратором.")
        return
    result = await add_admin(session, tg_id, added_by=message.from_user.id)
    if result is None:
        await message.answer(f"<code>{tg_id}</code> вже є адміністратором.")
        return
    add_admin_to_cache(tg_id)
    await message.answer(f"✅ <code>{tg_id}</code> додано як адміністратора.")


@router.message(Command("removeadmin"))
async def cmd_remove_admin(message: Message, session: AsyncSession) -> None:
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].lstrip("-").isdigit():
        await message.answer("Використання: /removeadmin <code>&lt;tg_id&gt;</code>")
        return
    tg_id = int(parts[1])
    from config import settings
    if tg_id in settings.admin_ids:
        await message.answer(f"<code>{tg_id}</code> є в config (.env) — видаліть звідти вручну.")
        return
    removed = await remove_admin(session, tg_id)
    if not removed:
        await message.answer(f"<code>{tg_id}</code> не знайдено серед адміністраторів.")
        return
    remove_admin_from_cache(tg_id)
    await message.answer(f"✅ <code>{tg_id}</code> видалено з адміністраторів.")
