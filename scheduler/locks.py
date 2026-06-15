"""
Per-activity asyncio locks.

Booking and cancellation both read the current seat count and then write,
which is a classic check-then-act race: two people tapping "book" on the
last free seat at the same time could both pass the capacity check before
either writes. Holding a per-activity lock around the read+write makes
seat allocation atomic.

This is sufficient because the bot runs as a SINGLE process (see project
notes): an in-memory lock covers all concurrent handlers. If this ever
became multi-process, this would need to move to a DB-level lock.
"""

import asyncio
from collections import defaultdict

_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


def activity_lock(activity_id: int) -> asyncio.Lock:
    """Return the lock for a given activity, creating it on first use."""
    return _locks[activity_id]
