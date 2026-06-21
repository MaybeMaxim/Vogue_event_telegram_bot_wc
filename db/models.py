"""
ORM models for the Wellness Escape bot.

Design notes (read before modifying):

- `Activity` rows represent every individually bookable thing: regular
  activities, lectures, and Anna Barinova's consultation slots (each
  15-minute consultation slot is its own Activity row with capacity=1
  and is_consultation_slot=True).

- `exclusive_group_id` groups activities that are presented to the user
  as alternatives within the same time window (e.g. Day 1 12:00-14:00:
  test-drive / face-massage / territory tour). It is a UI/grouping aid.
  The actual "no double-booking" rule in booking_service must check for
  TIME-RANGE OVERLAP across a user's bookings, not just matching
  exclusive_group_id — two activities can overlap in time without
  sharing a group, and that must still be blocked.

- `Booking.status` covers the full lifecycle described in the corrected
  brief: CONFIRMED -> PENDING_CONFIRMATION (30 min before start) ->
  either back to CONFIRMED (user confirms), or CANCELLED / NO_SHOW
  (auto-released, triggers waitlist promotion). ATTENDED is set by
  admins marking actual presence on-site, an alternative path that
  also counts as "confirmed presence".

- `Waitlist` is FIFO per activity via `created_at`. OFFERED entries have
  an `offer_expires_at` deadline checked by the periodic ticker.

- All datetimes are stored as timezone-aware UTC. Display/formatting
  converts to Europe/Kyiv (see config.event_timezone) at the UI layer.
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(Base):
    """A registered guest profile, linked 1:1 to a Telegram account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")
    waitlist_entries: Mapped[list["Waitlist"]] = relationship(back_populates="user")


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------

class Activity(Base):
    """
    A single bookable thing: a workshop, lecture, or one consultation slot.

    `day` is 1 or 2, matching the event's two days. `start_time`/`end_time`
    are timezone-aware UTC datetimes for the actual event dates.
    """

    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(120))
    day: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    capacity: Mapped[int] = mapped_column(Integer)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    speaker_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    speaker_social_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_text: Mapped[str] = mapped_column(String(255))

    # Grouping aid for mutually-exclusive alternatives within one time
    # window (see module docstring). NULL = not part of any group.
    exclusive_group_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # All activities currently require the 30-min attendance confirmation
    # flow per the corrections; kept as a flag in case some activity is
    # later exempted (e.g. an always-open info booth).
    requires_confirmation: Mapped[bool] = mapped_column(default=True)

    # True for each generated Anna Barinova consultation slot.
    is_consultation_slot: Mapped[bool] = mapped_column(default=False)

    # Ticker broadcast flags — set once the corresponding broadcast has been
    # sent so the ticker doesn't fire it again on the next pass.
    broadcast_sent: Mapped[bool] = mapped_column(default=False)          # free-seat broadcast at T-10
    opens_broadcast_sent: Mapped[bool] = mapped_column(default=False)    # booking-opens broadcast
    reminder_broadcast_sent: Mapped[bool] = mapped_column(default=False) # T-30 broadcast to non-booked

    # If set, booking attempts before this UTC datetime are rejected with
    # a "not open yet" message (used for consultation slots that unlock at
    # 15:30 on Day 1).
    booking_opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    bookings: Mapped[list["Booking"]] = relationship(back_populates="activity")
    waitlist_entries: Mapped[list["Waitlist"]] = relationship(back_populates="activity")


# ---------------------------------------------------------------------------
# Booking
# ---------------------------------------------------------------------------

class BookingStatus(str, enum.Enum):
    """Lifecycle states for a booking. See module docstring for transitions."""

    CONFIRMED = "confirmed"
    PENDING_CONFIRMATION = "pending_confirmation"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    ATTENDED = "attended"


class Booking(Base):
    """A user's reservation for one Activity."""

    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)

    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, native_enum=False, length=30),
        default=BookingStatus.CONFIRMED,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Set by the ticker once each notification has been sent, so it isn't
    # sent again on the next pass.
    reminder_sent: Mapped[bool] = mapped_column(default=False)
    confirmation_sent: Mapped[bool] = mapped_column(default=False)

    user: Mapped["User"] = relationship(back_populates="bookings")
    activity: Mapped["Activity"] = relationship(back_populates="bookings")


# ---------------------------------------------------------------------------
# Waitlist
# ---------------------------------------------------------------------------

class WaitlistStatus(str, enum.Enum):
    """Lifecycle states for a waitlist entry."""

    WAITING = "waiting"        # in the FIFO queue, not yet offered a spot
    OFFERED = "offered"        # a spot opened up; awaiting user confirmation
    EXPIRED = "expired"        # offer not confirmed in time, moved on
    CONFIRMED = "confirmed"    # user confirmed; a Booking was created


class Waitlist(Base):
    """A FIFO queue entry for a full Activity."""

    __tablename__ = "waitlist_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)

    status: Mapped[WaitlistStatus] = mapped_column(
        Enum(WaitlistStatus, native_enum=False, length=20),
        default=WaitlistStatus.WAITING,
        index=True,
    )

    # FIFO ordering is by created_at within (activity_id, status=WAITING).
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    offer_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    offer_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="waitlist_entries")
    activity: Mapped["Activity"] = relationship(back_populates="waitlist_entries")


# ---------------------------------------------------------------------------
# Question (anonymous Q&A for the sexologist lecture)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Admin (runtime-added admins, beyond the static admin_ids in config)
# ---------------------------------------------------------------------------

class Admin(Base):
    """Extra admin users added at runtime via /addadmin."""

    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    added_by_tg_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Question(Base):
    """
    An anonymous question submitted for the sexology lecture.

    `tg_id` is stored only for anti-abuse/rate-limiting and is never
    shown alongside the forwarded question text.
    """

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    tg_id: Mapped[int] = mapped_column(BigInteger, index=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ---------------------------------------------------------------------------
# SupportMessage (messages to organizers and bug reports)
# ---------------------------------------------------------------------------

class SupportMessage(Base):
    """A message sent through the support flow (organizer contact or bug report)."""

    __tablename__ = "support_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    tg_id: Mapped[int] = mapped_column(BigInteger, index=True)
    full_name: Mapped[str] = mapped_column(String(256))
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    message_type: Mapped[str] = mapped_column(String(16))  # "org" or "bug"
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
