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
from collections import OrderedDict
from pathlib import Path

from config import settings
from db.base import async_session
from db.crud import admin as admin_crud
from db.crud.support import all_questions, all_support_messages
from db.models import BookingStatus, WaitlistStatus
from utils.time_utils import format_time, format_time_range

logger = logging.getLogger(__name__)

_dirty = True  # sync once on startup
_lock = asyncio.Lock()
_client = None
_spreadsheet = None

_CONTACTS_TAB = "Контакти"
_WAITLIST_TAB = "Листи очікування"
_CONSULT_TAB = "Консультація Анни Барінової"
_QUESTIONS_TAB = "Питання сексологу"
_ORG_MSG_TAB = "Повідомлення організаторам"
_BUG_TAB = "Повідомлення про помилки"

# Default (0-based) column index for the "Присутність" checkbox.
_ATTENDANCE_COL_SINGLE = 5   # single-slot tabs: №,Name,Phone,Email,Status,Attendance
_ATTENDANCE_COL_MULTI = 6    # multi-slot tabs:  №,Time,Name,Phone,Email,Status,Attendance


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
        except (asyncio.CancelledError, RuntimeError) as exc:
            # Raised during event-loop shutdown (executor already torn down).
            # Not a real sync failure — just swallow it.
            logger.debug("Sheets sync skipped during shutdown: %s", exc)
        except Exception:
            logger.exception("Google Sheets sync failed; will retry next tick")


def _category_name(title: str) -> str:
    """Strip '(HH:MM-HH:MM)' suffix to get the logical group name."""
    return re.sub(r"\s*\(\d{1,2}:\d{2}-\d{1,2}:\d{2}\)\s*$", "", title).strip()


async def _gather_tabs() -> list[dict]:
    """
    Build an ordered list of tab specs: {title, rows, checkbox_rows}.

    Activity tabs: one tab per logical event (sub-slots grouped by category name).
    Consultation slots: one combined tab.
    Support tabs: organizer messages, bug reports, sexologist questions.
    """
    used: set[str] = set()
    tabs: list[dict] = []

    async with async_session() as session:
        activities = await admin_crud.all_activities(session)

        # --- Group regular activities by (day, category_name) ---
        # Each group becomes one tab. Sub-slots (e.g. Kérastase 12:00/12:20/…)
        # are listed as separate rows with their time range.
        regular = [a for a in activities if not a.is_consultation_slot]
        grouped: "OrderedDict[tuple, list]" = OrderedDict()
        for a in regular:
            key = (a.day, _category_name(a.title))
            grouped.setdefault(key, []).append(a)

        for (day, cat_name), group in grouped.items():
            all_participants: list[tuple] = []
            total_capacity = 0
            for activity in group:
                participants = await admin_crud.participants_for_activity(session, activity.id)
                for booking, user in participants:
                    all_participants.append((activity, booking, user))
                total_capacity += activity.capacity

            tab_title = _safe_tab_title(f"Д{day} {cat_name}", used)

            if len(group) == 1:
                a = group[0]
                header_rows = [
                    [f"{cat_name} — {format_time_range(a.start_time, a.end_time)}"],
                    [f"Зайнято: {len(all_participants)} з {total_capacity}"],
                    [],
                    ["№", "Прізвище та ім'я", "Телефон", "Email", "Статус", "Присутність"],
                ]
            else:
                header_rows = [
                    [cat_name],
                    [f"Зайнято: {len(all_participants)} з {total_capacity}"],
                    [],
                    ["№", "Час", "Прізвище та ім'я", "Телефон", "Email", "Статус", "Присутність"],
                ]

            data_rows = []
            checkbox_rows = []
            for i, (activity, booking, user) in enumerate(all_participants):
                if len(group) == 1:
                    row = [i + 1, user.full_name, user.phone, user.email,
                           _status_label(booking.status), booking.status == BookingStatus.ATTENDED]
                else:
                    row = [i + 1, format_time_range(activity.start_time, activity.end_time),
                           user.full_name, user.phone, user.email,
                           _status_label(booking.status), booking.status == BookingStatus.ATTENDED]
                data_rows.append(row)
                # attendance col is last in both layouts
                checkbox_rows.append(len(header_rows) + i)

            att_col = _ATTENDANCE_COL_SINGLE if len(group) == 1 else _ATTENDANCE_COL_MULTI
            tabs.append({"title": tab_title, "rows": header_rows + data_rows, "checkbox_rows": checkbox_rows, "attendance_col": att_col})

        # --- Consultations tab (one combined) ---
        consult_activities = [a for a in activities if a.is_consultation_slot]
        if consult_activities:
            first, last = consult_activities[0], consult_activities[-1]
            consult_rows: list[list] = []
            consult_present = 0
            for activity in consult_activities:
                for booking, user in await admin_crud.participants_for_activity(session, activity.id):
                    consult_rows.append([
                        format_time(activity.start_time),
                        user.full_name, user.phone, user.email,
                        _status_label(booking.status),
                        booking.status == BookingStatus.ATTENDED,
                    ])
                    consult_present += 1
            header_rows = [
                [f"Консультація Анни Барінової — {format_time_range(first.start_time, last.end_time)}"],
                [f"Зайнято слотів: {consult_present} з {len(consult_activities)}"],
                [],
                ["Час", "Прізвище та ім'я", "Телефон", "Email", "Статус", "Присутність"],
            ]
            checkbox_rows = [len(header_rows) + i for i in range(len(consult_rows))]
            tabs.append({"title": _CONSULT_TAB, "rows": header_rows + consult_rows, "checkbox_rows": checkbox_rows, "attendance_col": _ATTENDANCE_COL_SINGLE})

        # --- Contacts tab ---
        guests = await admin_crud.all_guests(session)
        contact_rows = [["№", "Прізвище та ім'я", "Телефон", "Email", "Зареєстровано"]]
        for i, user in enumerate(guests, start=1):
            registered = user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else ""
            contact_rows.append([i, user.full_name, user.phone, user.email, registered])
        tabs.append({"title": _CONTACTS_TAB, "rows": contact_rows, "checkbox_rows": []})

        # --- Waitlist tab ---
        wl_rows = [["День", "Час", "Активність", "Позиція", "Прізвище та ім'я", "Телефон", "Статус"]]
        for activity in activities:
            wl = await admin_crud.waitlist_for_activity(session, activity.id)
            for pos, (entry, user) in enumerate(wl, start=1):
                wl_rows.append([
                    f"Д{activity.day}",
                    format_time_range(activity.start_time, activity.end_time),
                    _category_name(activity.title), pos, user.full_name, user.phone,
                    "запропоновано" if entry.status == WaitlistStatus.OFFERED else "очікує",
                ])
        tabs.append({"title": _WAITLIST_TAB, "rows": wl_rows, "checkbox_rows": []})

        # --- Organizer messages tab ---
        org_msgs = await all_support_messages(session, "org")
        org_rows = [["№", "Прізвище та ім'я", "Username", "Telegram ID", "Час", "Повідомлення"]]
        for i, msg in enumerate(org_msgs, start=1):
            username = f"@{msg.username}" if msg.username else "—"
            ts = msg.created_at.strftime("%Y-%m-%d %H:%M") if msg.created_at else ""
            org_rows.append([i, msg.full_name, username, msg.tg_id, ts, msg.text])
        tabs.append({"title": _ORG_MSG_TAB, "rows": org_rows, "checkbox_rows": []})

        # --- Bug reports tab ---
        bug_msgs = await all_support_messages(session, "bug")
        bug_rows = [["№", "Прізвище та ім'я", "Username", "Telegram ID", "Час", "Повідомлення"]]
        for i, msg in enumerate(bug_msgs, start=1):
            username = f"@{msg.username}" if msg.username else "—"
            ts = msg.created_at.strftime("%Y-%m-%d %H:%M") if msg.created_at else ""
            bug_rows.append([i, msg.full_name, username, msg.tg_id, ts, msg.text])
        tabs.append({"title": _BUG_TAB, "rows": bug_rows, "checkbox_rows": []})

        # --- Anonymous sexologist questions tab ---
        questions = await all_questions(session)
        q_rows = [["№", "Час", "Запитання"]]
        for i, q in enumerate(questions, start=1):
            ts = q.created_at.strftime("%Y-%m-%d %H:%M") if q.created_at else ""
            q_rows.append([i, ts, q.text])
        tabs.append({"title": _QUESTIONS_TAB, "rows": q_rows, "checkbox_rows": []})

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
    # Google Sheets sheet names are case-insensitive; normalise for comparisons.
    existing_lower = {title.lower(): ws for title, ws in existing.items()}
    wanted_lower = {t.lower() for t in wanted}

    # --- 1. structural changes (add missing, delete stale) in one batch ---
    requests = []
    # Add any missing sheets (case-insensitive check to avoid API 400 error).
    for tab in tabs:
        if tab["title"].lower() not in existing_lower:
            requests.append({"addSheet": {"properties": {"title": tab["title"]}}})
    # Delete stale sheets, but never delete them all (Sheets requires >=1).
    stale = [ws for title, ws in existing.items() if title.lower() not in wanted_lower]
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
        att_col = tab.get("attendance_col", _ATTENDANCE_COL_SINGLE)
        if checkbox_rows:
            start = min(checkbox_rows)
            end = max(checkbox_rows) + 1
            fmt_requests.append({
                "setDataValidation": {
                    "range": {
                        "sheetId": ws.id,
                        "startRowIndex": start,
                        "endRowIndex": end,
                        "startColumnIndex": att_col,
                        "endColumnIndex": att_col + 1,
                    },
                    "rule": {"condition": {"type": "BOOLEAN"}, "strict": True},
                }
            })

    if fmt_requests:
        ss.batch_update({"requests": fmt_requests})
