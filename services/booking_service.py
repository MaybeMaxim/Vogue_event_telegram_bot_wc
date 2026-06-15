"""
Booking drill-down logic for "✍️ Записатись".

Navigation model (Option A, two-level drill-down):
  pick day -> pick time slot -> pick activity within that slot

This module groups a day's activities into "slots" (one per distinct
(start_time, end_time) window) for the slot-picker screen, and renders
the per-slot activity list for the activity-picker screen.

The Barinova consultation block is treated as ONE slot at this level
(16:00-19:00); tapping it leads into the per-consultation-slot picker
(built with the consultation booking flow).

Actual booking ACTIONS (conflict/limit/capacity checks, creating a
Booking) are added in the booking action step -- this module is just
the browse/drill-down structure plus rendering.
"""

import html
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime

from db.models import Activity
from texts import booking as t
from utils.status_emoji import seats_free, seats_text, status_emoji
from utils.time_utils import format_time_range


@dataclass
class Slot:
    """One bookable time window on a day, with the activities it contains."""

    start_time: datetime
    end_time: datetime
    activities: list[tuple[Activity, int]]
    is_consultation: bool

    @property
    def total_capacity(self) -> int:
        return sum(a.capacity for a, _ in self.activities)

    @property
    def total_free(self) -> int:
        return sum(seats_free(a.capacity, b) for a, b in self.activities)

    @property
    def is_exclusive(self) -> bool:
        """True if the activities here are mutually-exclusive alternatives."""
        if len(self.activities) < 2:
            return False
        group_ids = {a.exclusive_group_id for a, _ in self.activities}
        return len(group_ids) == 1 and None not in group_ids


def group_into_slots(activities: list[tuple[Activity, int]]) -> list[Slot]:
    """
    Group a day's (Activity, booked) tuples into Slots.

    All consultation slots collapse into a single Slot spanning the
    whole consultation window; regular activities group by exact
    (start_time, end_time).
    """
    regular = [(a, b) for a, b in activities if not a.is_consultation_slot]
    consultations = [(a, b) for a, b in activities if a.is_consultation_slot]

    slots: list[Slot] = []

    grouped: "OrderedDict[tuple, list[tuple[Activity, int]]]" = OrderedDict()
    for activity, booked in regular:
        grouped.setdefault((activity.start_time, activity.end_time), []).append((activity, booked))

    for (start, end), items in grouped.items():
        slots.append(Slot(start_time=start, end_time=end, activities=items, is_consultation=False))

    if consultations:
        start = consultations[0][0].start_time
        end = consultations[-1][0].end_time
        slots.append(Slot(start_time=start, end_time=end, activities=consultations, is_consultation=True))

    slots.sort(key=lambda s: s.start_time)
    return slots


def render_slot_picker(day: int, date_label: str, slots: list[Slot]) -> str:
    """
    Build the slot-picker overview: each time slot listed with the
    activities it contains, so the user sees what's in each block before
    tapping a time button.
    """
    blocks = [t.SLOT_PICKER_INTRO.format(day=day, date=date_label)]

    for slot in slots:
        time_range = format_time_range(slot.start_time, slot.end_time)
        names = " · ".join(html.escape(a.title) for a, _ in slot.activities)
        if slot.is_consultation:
            names = "Консультації Анни Барінової"
        blocks.append(t.SLOT_OVERVIEW_BLOCK.format(time_range=time_range, names=names))

    blocks.append(t.SLOT_PICKER_PROMPT)
    return "\n\n".join(blocks)


def slot_button_label(slot: Slot) -> str:
    """Label for a slot button in the slot picker, e.g. '🕒 11:00-12:00 · 🟢 є місця'."""
    time_range = format_time_range(slot.start_time, slot.end_time)
    dot = status_emoji(slot.total_capacity, slot.total_capacity - slot.total_free)
    status = "є місця" if slot.total_free > 0 else "немає місць"
    return f"🕒 {time_range} · {dot} {status}"


def render_activity_picker(slot: Slot) -> str:
    """Build the text for the activity-picker screen (one slot's options)."""
    time_range = format_time_range(slot.start_time, slot.end_time)

    lines = [t.ACTIVITY_PICKER_HEADER.format(time_range=time_range)]

    if slot.is_exclusive:
        lines.append(t.ACTIVITY_PICKER_EXCLUSIVE_HINT)

    lines.append("")

    for activity, booked in slot.activities:
        lines.append(
            t.ACTIVITY_PICKER_LINE.format(
                dot=status_emoji(activity.capacity, booked),
                title=html.escape(activity.title),
                seats=seats_text(activity.capacity, booked),
            )
        )
        if activity.speaker_name:
            lines.append(t.ACTIVITY_PICKER_SPEAKER.format(speaker_name=_speaker_display(activity)))
        if activity.description:
            lines.append(t.ACTIVITY_PICKER_DESC.format(description=html.escape(activity.description)))

    return "\n".join(lines)


def _speaker_display(activity: Activity) -> str:
    """Render the speaker name, as a clickable link if a social URL is set."""
    name = html.escape(activity.speaker_name)
    if activity.speaker_social_url:
        url = html.escape(activity.speaker_social_url)
        return f'<a href="{url}">{name}</a> ↗'
    return name
