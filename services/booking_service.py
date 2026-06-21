"""
Booking drill-down logic for "✍️ Записатись".

Navigation model (category-based, two-level drill-down):
  pick day -> pick activity category -> pick sub-slot within that category

A "category" is a logical group of activities that the user thinks of as
one thing — e.g. "Тест-драйв MINI Countryman" collapses 6 individual
20-minute sub-slots from two different exclusive groups into one button.

Actual booking ACTIONS live in services.booking_actions.
"""

import html
import re
from collections import OrderedDict
from dataclasses import dataclass

from db.models import Activity
from texts import booking as t
from utils.status_emoji import seats_free, seats_text, status_emoji
from utils.time_utils import format_time, format_time_range


def _category_name(title: str) -> str:
    """Strip embedded '(HH:MM-HH:MM)' suffix to get the logical category name."""
    return re.sub(r"\s*\(\d{1,2}:\d{2}-\d{1,2}:\d{2}\)\s*$", "", title).strip()


@dataclass
class CategoryGroup:
    """All sub-slots that belong to one logical activity category."""

    name: str
    activities: list[tuple[Activity, int]]
    is_consultation: bool = False

    @property
    def total_capacity(self) -> int:
        return sum(a.capacity for a, _ in self.activities)

    @property
    def total_booked(self) -> int:
        return sum(b for _, b in self.activities)

    @property
    def total_free(self) -> int:
        return max(self.total_capacity - self.total_booked, 0)

    @property
    def anchor_id(self) -> int:
        return self.activities[0][0].id

    @property
    def first_activity(self) -> Activity:
        return self.activities[0][0]


def group_into_categories(activities: list[tuple[Activity, int]]) -> list[CategoryGroup]:
    """
    Group a day's activities into logical CategoryGroups.

    Consultation slots collapse into one category.  Everything else groups by
    _category_name(title), so e.g. test-drive 12:00/12:20/12:40/13:00/…
    from two different exclusive groups become one "Тест-драйв" category.

    Result sorted by earliest start_time.
    """
    regular = [(a, b) for a, b in activities if not a.is_consultation_slot]
    consultations = [(a, b) for a, b in activities if a.is_consultation_slot]

    cats: "OrderedDict[str, list[tuple[Activity, int]]]" = OrderedDict()
    for a, b in regular:
        cats.setdefault(_category_name(a.title), []).append((a, b))

    groups: list[CategoryGroup] = [
        CategoryGroup(name=name, activities=items)
        for name, items in cats.items()
    ]

    if consultations:
        groups.append(CategoryGroup(
            name="Консультація Анни Баринової",
            activities=consultations,
            is_consultation=True,
        ))

    groups.sort(key=lambda g: g.first_activity.start_time)
    return groups


def render_category_picker(day: int, date_label: str) -> str:
    return t.CATEGORY_PICKER_INTRO.format(day=day, date=date_label)


def render_subslot_picker(cat: CategoryGroup) -> str:
    """
    Text for the sub-slot screen: activity name, location, limit, optional speaker,
    sub-slot times list, and prompt.
    """
    first = cat.first_activity

    lines: list[str] = [f"<b>{html.escape(cat.name)}</b>"]

    if first.location_text:
        lines.append(f"📍 {html.escape(first.location_text)}")

    if first.booking_opens_at:
        lines.append(t.SUBSLOT_OPENS_AT.format(time=format_time(first.booking_opens_at)))

    lines.append("")

    if len(cat.activities) > 1:
        lines.append(t.SUBSLOT_PICK_TIME_PROMPT)
    else:
        lines.append(t.SUBSLOT_SINGLE_PROMPT)

    return "\n".join(lines)
