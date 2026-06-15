"""
Seat-availability status indicators, shared by the schedule view and
(later) the booking flow.

Status thresholds:
- 🟢 plenty of seats free (more than half the capacity)
- 🟡 some seats free (half or fewer, but at least one)
- 🔴 full (zero seats free)
"""

GREEN = "🟢"
YELLOW = "🟡"
RED = "🔴"


def seats_free(capacity: int, booked: int) -> int:
    """Return the number of free seats, never negative."""
    return max(capacity - booked, 0)


def status_emoji(capacity: int, booked: int) -> str:
    """Return the traffic-light emoji for the given capacity/booked counts."""
    free = seats_free(capacity, booked)

    if free <= 0:
        return RED
    if free <= capacity / 2:
        return YELLOW
    return GREEN


def availability_text(capacity: int, booked: int) -> str:
    """
    Human-readable availability line, e.g. "🟢 Вільно: 14 з 20"
    or "🔴 Місць немає" when full.
    """
    free = seats_free(capacity, booked)
    emoji = status_emoji(capacity, booked)

    if free <= 0:
        return f"{emoji} Місць немає"

    return f"{emoji} Вільно: {free} з {capacity}"


def seats_text(capacity: int, booked: int) -> str:
    """
    Compact seat count without the dot, for one-line cards where the
    dot is rendered separately, e.g. "14 з 20" or "немає місць".
    """
    free = seats_free(capacity, booked)

    if free <= 0:
        return "немає місць"

    return f"{free} з {capacity}"
