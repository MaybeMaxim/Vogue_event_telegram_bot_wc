"""
Read-only schedule rendering for the "📅 Розклад" view.

Layout goals (after UX feedback):
- Tight, scannable cards: status dot + bold title + seat count on ONE
  line, with an optional speaker sub-line.
- Time-slot groups separated by a single blank line; exclusive-choice
  slots get an italic "оберіть один варіант" hint on the header.
- Barinova consultations collapsed into a single line (booking the
  individual slots happens under "✍️ Записатись").

This module is intentionally booking-free now. The booking drill-down
("✍️ Записатись") builds its own per-slot screens in
services.booking_service.

HTML formatting: bot runs with ParseMode.HTML; all DB-sourced text
(titles, speaker names) is html.escape()d before insertion.
"""

import html
from collections import OrderedDict

from db.models import Activity
from texts import schedule as t
from utils.status_emoji import seats_free, seats_text, status_emoji
from utils.time_utils import format_time_range


def render_day_schedule(day: int, date_label: str, activities: list[tuple[Activity, int]]) -> str:
    """
    Build the full read-only schedule message for one day.

    `activities` is a list of (Activity, booked_count) tuples, ordered
    by start_time (as returned by db.crud.activities.get_activities_for_day).
    """
    header = t.DAY_HEADER.format(day=day, date=date_label)

    if not activities:
        return header + "\n\n" + t.NO_ACTIVITIES_FOR_DAY

    regular, consultations = _split_consultations(activities)

    sections: list[str] = [header]
    sections.extend(_render_regular_groups(regular))

    if consultations:
        sections.append(_render_consultation_line(consultations))

    body = "\n\n".join(sections)
    return body + "\n" + t.BOOK_HINT


def _split_consultations(
    activities: list[tuple[Activity, int]]
) -> tuple[list[tuple[Activity, int]], list[tuple[Activity, int]]]:
    """Separate Barinova consultation slots from regular activities."""
    regular = [(a, b) for a, b in activities if not a.is_consultation_slot]
    consultations = [(a, b) for a, b in activities if a.is_consultation_slot]
    return regular, consultations


def _render_regular_groups(activities: list[tuple[Activity, int]]) -> list[str]:
    """Group regular activities by (start_time, end_time) and render each group."""
    groups: "OrderedDict[tuple, list[tuple[Activity, int]]]" = OrderedDict()

    for activity, booked in activities:
        key = (activity.start_time, activity.end_time)
        groups.setdefault(key, []).append((activity, booked))

    rendered = []
    for (start, end), items in groups.items():
        header = t.TIME_SLOT_HEADER.format(time_range=format_time_range(start, end))
        if _is_exclusive_group(items):
            header += t.TIME_SLOT_EXCLUSIVE_HINT

        lines = [header, ""]
        for activity, booked in items:
            lines.append(_render_activity_line(activity, booked))

        rendered.append("\n".join(lines))

    return rendered


def _is_exclusive_group(items: list[tuple[Activity, int]]) -> bool:
    """True if all activities sharing this time slot are mutually exclusive alternatives."""
    if len(items) < 2:
        return False

    group_ids = {activity.exclusive_group_id for activity, _ in items}
    return len(group_ids) == 1 and None not in group_ids


def _render_activity_line(activity: Activity, booked: int) -> str:
    """Render a single activity as: dot + bold title + seat count (+ optional speaker/description)."""
    line = t.ACTIVITY_LINE.format(
        dot=status_emoji(activity.capacity, booked),
        title=html.escape(activity.title),
        seats=seats_text(activity.capacity, booked),
    )

    if activity.speaker_name:
        line += "\n" + t.ACTIVITY_SPEAKER_LINE.format(speaker_name=_speaker_display(activity))

    if activity.description:
        line += "\n" + t.ACTIVITY_DESC_LINE.format(description=html.escape(activity.description))

    return line


def _speaker_display(activity: Activity) -> str:
    """Render the speaker name, as a clickable link if a social URL is set."""
    name = html.escape(activity.speaker_name)

    if activity.speaker_social_url:
        url = html.escape(activity.speaker_social_url)
        return f'<a href="{url}">{name}</a> ↗'

    return name


def _render_consultation_line(consultations: list[tuple[Activity, int]]) -> str:
    """Render the collapsed Barinova consultation block as a single slot line."""
    first_activity, _ = consultations[0]
    last_activity, _ = consultations[-1]

    time_range = format_time_range(first_activity.start_time, last_activity.end_time)

    total_capacity = sum(activity.capacity for activity, _ in consultations)
    total_free = sum(seats_free(activity.capacity, booked) for activity, booked in consultations)

    dot = status_emoji(total_capacity, total_capacity - total_free)
    seats = f"{total_free} з {total_capacity} слотів" if total_free > 0 else "слотів немає"

    header = t.TIME_SLOT_HEADER.format(time_range=time_range)
    line = t.CONSULTATION_LINE.format(dot=dot, title="Консультації Анни Барінової", seats=seats)

    return header + "\n\n" + line
