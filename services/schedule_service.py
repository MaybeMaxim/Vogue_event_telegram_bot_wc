"""
Schedule rendering logic, shared between the read-only "📅 Розклад"
view and (later) the booking flow's activity listings.

Grouping rules:
- Regular activities are grouped by (start_time, end_time): activities
  sharing the same time window are shown together under one "🕒 HH:MM-HH:MM"
  header, since that's how the user reads "pick one of these alternatives".
  If every activity in the group shares the same exclusive_group_id
  (i.e. it's a genuine "pick one" set), a short hint is appended to the
  header.
- Anna Barinova's 12 consultation slots (is_consultation_slot=True) are
  collapsed into a single summary line with an aggregate free-seat count,
  rather than listed individually — the per-slot picker lives in the
  consultation booking flow.

HTML formatting: the bot runs with ParseMode.HTML. Any text that comes
from the database (activity titles, speaker names) is passed through
html.escape() before being inserted into the <b>/<a> templates in
texts.schedule, so seed data containing quotes/ampersands/etc. can't
break the markup.
"""

import html
from collections import OrderedDict

from db.models import Activity
from texts import schedule as t
from utils.status_emoji import availability_text, seats_free
from utils.time_utils import format_time_range


def render_day_schedule(day: int, date_label: str, activities: list[tuple[Activity, int]]) -> str:
    """
    Build the full schedule message text for one day.

    `activities` is a list of (Activity, booked_count) tuples, as
    returned by db.crud.activities.get_activities_for_day, already
    ordered by start_time.
    """
    if not activities:
        return t.DAY_HEADER.format(day=day, date=date_label) + "\n\n" + t.NO_ACTIVITIES_FOR_DAY

    regular, consultations = _split_consultations(activities)

    sections: list[str] = [t.DAY_HEADER.format(day=day, date=date_label)]
    sections.extend(_render_regular_groups(regular))

    if consultations:
        sections.append(_render_consultation_summary(consultations))

    return "\n\n".join(sections)


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
        time_range = format_time_range(start, end)
        header = t.TIME_SLOT_HEADER.format(time_range=time_range)

        if _is_exclusive_group(items):
            header += t.TIME_SLOT_EXCLUSIVE_HINT

        lines = [header]

        for activity, booked in items:
            lines.append(_render_activity_card(activity, booked))

        rendered.append("\n".join(lines))

    return rendered


def _is_exclusive_group(items: list[tuple[Activity, int]]) -> bool:
    """True if all activities sharing this time slot are mutually exclusive alternatives."""
    if len(items) < 2:
        return False

    group_ids = {activity.exclusive_group_id for activity, _ in items}
    return len(group_ids) == 1 and None not in group_ids


def _render_activity_card(activity: Activity, booked: int) -> str:
    """Render a single activity card (title, availability, optional speaker line)."""
    card = t.ACTIVITY_CARD.format(
        title=html.escape(activity.title),
        availability=availability_text(activity.capacity, booked),
    )

    if activity.speaker_name:
        card += "\n" + t.ACTIVITY_SPEAKER_LINE.format(speaker_name=_speaker_display(activity))

    return card


def _speaker_display(activity: Activity) -> str:
    """
    Render the speaker name, as a clickable link if a social URL is set.

    Both the visible name and the URL are HTML-escaped: the name because
    it's rendered as link text, the URL because it goes inside an href
    attribute (html.escape with quote=True, the default, also escapes
    double quotes so the attribute can't be broken out of).
    """
    name = html.escape(activity.speaker_name)

    if activity.speaker_social_url:
        url = html.escape(activity.speaker_social_url)
        return f'<a href="{url}">{name}</a> ↗'

    return name


def _render_consultation_summary(consultations: list[tuple[Activity, int]]) -> str:
    """
    Render a single collapsed summary line for all Barinova consultation
    slots: overall time window + aggregate free-slot count.
    """
    first_activity, _ = consultations[0]
    last_activity, _ = consultations[-1]

    time_range = format_time_range(first_activity.start_time, last_activity.end_time)

    total_capacity = sum(activity.capacity for activity, _ in consultations)
    total_free = sum(seats_free(activity.capacity, booked) for activity, booked in consultations)

    summary = f"Вільно слотів: {total_free} з {total_capacity}" if total_free > 0 else "Вільних слотів немає"

    return t.CONSULTATION_SUMMARY.format(
        time_range=time_range,
        title="Консультації Анни Барінової",
        availability_summary=summary,
    )
