"""
Google Sheets live sync (optional, controlled by config.gsheets_enabled).

The bot mirrors current booking state into a single Google Spreadsheet:
  - one worksheet per REGULAR activity (participants + attendance checkbox)
  - one combined "Консультації" worksheet for all 15-min consultation
    slots (NOT one sheet per slot)
  - a "Контакти" worksheet (all guests)
  - a "Листи очікування" worksheet (all waitlist entries)

API-cost design (this is what keeps us under Google's 60 writes/min quota):
  - The whole spreadsheet is rewritten with ONE batchUpdate call per sync
    (values + sheet add/delete + checkbox formatting all batched), instead
    of clear()/resize()/update() per tab.
  - Sync runs at most once per ticker pass, and only when something changed
    (the _dirty flag).

Auth: a Google service account (see GOOGLE_SHEETS_SETUP.md).
gspread is blocking, so calls run in a thread via asyncio.to_thread.
"""

import asyncio
import logging
import re
from pathlib import Path

from config import settings
from db.base import async_session
from db.crud import admin as admin_crud
from db.models import BookingStatus, WaitlistStatus
from utils.time_utils import format_time, format_time_range

logger = logging.getLogger(__name__)

_dirty = True  # sync once on startup
_lock = asyncio.Lock()
_client = None
_spreadsheet = None

_CONTACTS_TAB = "Контакти"
_WAITLIST_TAB = "Листи очікування"
_CONSULT_TAB = "Консультації"

# Column index (0-based) of the "Присутність" checkbox column in activity tabs.
_ATTENDANCE_COL = 5


def mark_dirty() -> None:
    """Flag that booking data changed and the sheets need a refresh."""
    global _dirty
    _dirty = True


async def get_spreadsheet_url() -> str | None:
    if not await _ensure_ready():
        return None
    try:
        return _spreadsheet.url
    except Exception:
        logger.exception("Could not read spreadsheet URL")
        return None


def _status_label(status: BookingStatus) -> str:
    return {
        BookingStatus.CONFIRMED: "Підтверджено",
        BookingStatus.PENDING_CONFIRMATION: "Очікує підтвердження",
        BookingStatus.ATTENDED: "Був присутній",
    }.get(status, status.value)


def _safe_tab_title(raw: str, used: set[str]) -> str:
    title = re.sub(r"[\[\]:*?/\\]", " ", raw).strip()[:90] or "Sheet"
    base, n = title, 1
    while title in used:
        suffix = f" ({n})"
        title = base[: 90 - len(suffix)] + suffix
        n += 1
    used.add(title)
    return title


def _init_client():
    global _client, _spreadsheet
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(settings.gsheets_credentials_file, scopes=scopes)
    _client = gspread.authorize(creds)

    if settings.gsheets_spreadsheet_id:
        _spreadsheet = _client.open_by_key(settings.gsheets_spreadsheet_id)
    else:
        _spreadsheet = _client.create("Wellness Escape — записи")
        logger.warning(
            "Created a new Google Spreadsheet (id=%s). Set GSHEETS_SPREADSHEET_ID "
            "to reuse it and share it with your team. URL: %s",
            _spreadsheet.id, _spreadsheet.url,
        )
    return _spreadsheet


async def _ensure_ready() -> bool:
    if not settings.gsheets_enabled:
        return False
    if not Path(settings.gsheets_credentials_file).exists():
        logger.warning("Google Sheets enabled but credentials file not found: %s",
                       settings.gsheets_credentials_file)
        return False
    if _spreadsheet is not None:
        return True
    try:
        await asyncio.to_thread(_init_client)
        return True
    except Exception:
        logger.exception("Failed to initialise Google Sheets client")
        return False


async def sync_if_dirty() -> None:
    global _dirty
    if not _dirty:
        return
    if not await _ensure_ready():
        return

    async with _lock:
        if not _dirty:
            return
        try:
            tabs = await _gather_tabs()
            await asyncio.to_thread(_write_everything, tabs)
            _dirty = False
        except Exception:
            logger.exception("Google Sheets sync failed; will retry next tick")


async def _gather_tabs() -> list[dict]:
    """
    Build an ordered list of tab specs: {title, rows, attendance_rows}.
    `attendance_rows` is the set of 0-based data-row indices that should get
    a checkbox in the attendance column (None for non-activity tabs).
    """
    used: set[str] = set()
    tabs: list[dict] = []

    async with async_session() as session:
        activities = await admin_crud.all_activities(session)

        consult_rows: list[list] = []
        consult_present = 0

        for activity in activities:
            participants = await admin_crud.participants_for_activity(session, activity.id)

            if activity.is_consultation_slot:
                # Collapse all consultation slots into one combined tab.
                for booking, user in participants:
                    consult_rows.append([
                        format_time(activity.start_time),
                        user.full_name,
                        user.phone,
                        user.email,
                        _status_label(booking.status),
                        booking.status == BookingStatus.ATTENDED,
                    ])
                    consult_present += 1
                continue

            title = _safe_tab_title(f"Д{activity.day} {activity.title}", used)
            header_rows = [
                [f"{activity.title} — {format_time_range(activity.start_time, activity.end_time)}"],
                [f"Зайнято: {len(participants)} з {activity.capacity}"],
                [],
                ["№", "Прізвище та ім'я", "Телефон", "Email", "Статус", "Присутність"],
            ]
            data_rows = []
            checkbox_rows = []
            for i, (booking, user) in enumerate(participants):
                data_rows.append([
                    i + 1, user.full_name, user.phone, user.email,
                    _status_label(booking.status),
                    booking.status == BookingStatus.ATTENDED,
                ])
                checkbox_rows.append(len(header_rows) + i)  # absolute row index
            tabs.append({"title": title, "rows": header_rows + data_rows, "checkbox_rows": checkbox_rows})

        # Combined consultations tab (header + rows), if any consultation slots exist.
        consult_activities = [a for a in activities if a.is_consultation_slot]
        if consult_activities:
            first, last = consult_activities[0], consult_activities[-1]
            header_rows = [
                [f"Консультації Анни Барінової — {format_time_range(first.start_time, last.end_time)}"],
                [f"Зайнято слотів: {consult_present} з {len(consult_activities)}"],
                [],
                ["Час", "Прізвище та ім'я", "Телефон", "Email", "Статус", "Присутність"],
            ]
            checkbox_rows = [len(header_rows) + i for i in range(len(consult_rows))]
            tabs.append({"title": _CONSULT_TAB, "rows": header_rows + consult_rows, "checkbox_rows": checkbox_rows})

        # Contacts tab.
        guests = await admin_crud.all_guests(session)
        contact_rows = [["№", "Прізвище та ім'я", "Телефон", "Email", "Зареєстровано"]]
        for i, user in enumerate(guests, start=1):
            registered = user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else ""
            contact_rows.append([i, user.full_name, user.phone, user.email, registered])
        tabs.append({"title": _CONTACTS_TAB, "rows": contact_rows, "checkbox_rows": []})

        # Waitlist tab.
        wl_rows = [["День", "Час", "Активність", "Позиція", "Прізвище та ім'я", "Телефон", "Статус"]]
        for activity in activities:
            wl = await admin_crud.waitlist_for_activity(session, activity.id)
            for pos, (entry, user) in enumerate(wl, start=1):
                wl_rows.append([
                    f"Д{activity.day}",
                    format_time_range(activity.start_time, activity.end_time),
                    activity.title, pos, user.full_name, user.phone,
                    "запропоновано" if entry.status == WaitlistStatus.OFFERED else "очікує",
                ])
        tabs.append({"title": _WAITLIST_TAB, "rows": wl_rows, "checkbox_rows": []})

    return tabs


def _write_everything(tabs: list[dict]) -> None:
    """
    Rewrite the whole spreadsheet with a MINIMAL number of API calls:
      1. one batch_update to add missing sheets / delete stale ones
      2. one values_batch_update to write all cell values
      3. one batch_update to apply checkbox formatting to attendance columns
    """
    ss = _spreadsheet
    wanted = {tab["title"] for tab in tabs}

    existing = {ws.title: ws for ws in ss.worksheets()}

    # --- 1. structural changes (add missing, delete stale) in one batch ---
    requests = []
    # Add any missing sheets.
    for tab in tabs:
        if tab["title"] not in existing:
            requests.append({"addSheet": {"properties": {"title": tab["title"]}}})
    # Delete stale sheets, but never delete them all (Sheets requires >=1).
    stale = [ws for title, ws in existing.items() if title not in wanted]
    keep_one = len(wanted) == 0  # only matters in the degenerate empty case
    for ws in stale:
        if keep_one:
            keep_one = False
            continue
        requests.append({"deleteSheet": {"sheetId": ws.id}})

    if requests:
        ss.batch_update({"requests": requests})

    # Refresh worksheet handles after structural changes.
    existing = {ws.title: ws for ws in ss.worksheets()}

    # --- 2. write each tab's values (one update call per tab) ---
    # After collapsing consultations there are only ~8 tabs, so this stays
    # well under Google's 60 writes/min quota. Worksheet.update() is a
    # stable API across gspread versions.
    for tab in tabs:
        ws = existing.get(tab["title"])
        if ws is None:
            continue
        rows = tab["rows"] or [[""]]
        ncols = max((len(r) for r in rows), default=1)
        normalized = [r + [""] * (ncols - len(r)) for r in rows]
        ws.update(values=normalized, range_name="A1", value_input_option="USER_ENTERED")

    # --- 3. resize sheets to fit + apply checkbox data-validation in one batch ---
    fmt_requests = []
    for tab in tabs:
        ws = existing.get(tab["title"])
        if ws is None:
            continue
        rows = tab["rows"] or [[""]]
        nrows = max(len(rows), 1)
        ncols = max((len(r) for r in rows), default=1)

        # Resize to exactly fit (removes leftover rows/cols from prior writes).
        fmt_requests.append({
            "updateSheetProperties": {
                "properties": {"sheetId": ws.id, "gridProperties": {"rowCount": nrows, "columnCount": ncols}},
                "fields": "gridProperties.rowCount,gridProperties.columnCount",
            }
        })

        # Checkbox validation on the attendance column for each data row.
        checkbox_rows = tab.get("checkbox_rows") or []
        if checkbox_rows:
            start = min(checkbox_rows)
            end = max(checkbox_rows) + 1
            fmt_requests.append({
                "setDataValidation": {
                    "range": {
                        "sheetId": ws.id,
                        "startRowIndex": start,
                        "endRowIndex": end,
                        "startColumnIndex": _ATTENDANCE_COL,
                        "endColumnIndex": _ATTENDANCE_COL + 1,
                    },
                    "rule": {"condition": {"type": "BOOLEAN"}, "strict": True},
                }
            })

    if fmt_requests:
        ss.batch_update({"requests": fmt_requests})
