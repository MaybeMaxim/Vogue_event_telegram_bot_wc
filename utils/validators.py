"""
Pure validation helpers for the registration flow.

Each function returns either a cleaned value (str) on success,
or None if the input is invalid. No side effects, no I/O —
easy to unit-test in isolation.
"""

import re

_NAME_MIN_LENGTH = 3
_NAME_MAX_LENGTH = 80
_NAME_MIN_WORDS = 2
_NAME_MAX_WORDS = 4

_EMAIL_MAX_LENGTH = 100
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Allows unicode letters, spaces, hyphens and apostrophes (for names like "О'Браєн")
_NAME_PATTERN = re.compile(r"^[^\d_]+$", re.UNICODE)

_PHONE_DIGITS_PATTERN = re.compile(r"\D+")


def normalize_full_name(raw: str) -> str | None:
    """
    Validate and normalize a full name string.

    Rules:
    - 3..80 characters after trimming
    - 2..4 words (allows middle names / patronymics)
    - no digits, no underscores
    - collapses repeated whitespace

    Returns the cleaned name, or None if invalid.
    """
    if not raw:
        return None

    cleaned = " ".join(raw.split())

    if not (_NAME_MIN_LENGTH <= len(cleaned) <= _NAME_MAX_LENGTH):
        return None

    words = cleaned.split(" ")
    if not (_NAME_MIN_WORDS <= len(words) <= _NAME_MAX_WORDS):
        return None

    if not _NAME_PATTERN.match(cleaned):
        return None

    return cleaned


def normalize_name_part(raw: str) -> str | None:
    """
    Validate and normalize a SINGLE name part (e.g. just a surname).

    Used when the first name is already known (from a shared contact)
    and we only need the user to supply the missing part. Accepts a
    single word (1..40 chars, no digits/underscores).

    Returns the cleaned single word, or None if invalid.
    """
    if not raw:
        return None

    cleaned = " ".join(raw.split())

    if not (2 <= len(cleaned) <= 40):
        return None

    if " " in cleaned:
        # More than one word -> not a single name part; the caller should
        # treat this as a full-name entry instead.
        return None

    if not _NAME_PATTERN.match(cleaned):
        return None

    return cleaned


def normalize_phone(raw: str) -> str | None:
    """
    Validate and normalize a phone number string.

    Accepts:
    - +380XXXXXXXXX
    - 380XXXXXXXXX
    - 0XXXXXXXXX (assumed Ukrainian, prefixed with +38)
    - generic international numbers (10..15 digits)

    Returns the normalized phone (always starting with '+'), or None if invalid.
    """
    if not raw:
        return None

    digits = _PHONE_DIGITS_PATTERN.sub("", raw)
    if not digits:
        return None

    # Ukrainian local format: 0XXXXXXXXX -> +38 0XXXXXXXXX
    if digits.startswith("0") and len(digits) == 10:
        digits = "38" + digits

    if not (10 <= len(digits) <= 15):
        return None

    return "+" + digits


def normalize_email(raw: str) -> str | None:
    """
    Validate and normalize an email address.

    Returns the trimmed, lowercased email, or None if invalid.
    """
    if not raw:
        return None

    cleaned = raw.strip().lower()

    if len(cleaned) > _EMAIL_MAX_LENGTH:
        return None

    if not _EMAIL_PATTERN.match(cleaned):
        return None

    return cleaned


def normalize_telegram_contact_name(first_name: str | None, last_name: str | None) -> str | None:
    """
    Build a full name from Telegram contact fields and validate it
    using the same rules as a manually typed name.

    Returns the combined "Прізвище Ім'я" string if both parts are
    usable, or None if the result doesn't pass validation
    (e.g. last_name missing, or first_name itself is unusable).
    """
    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()

    if not first_name or not last_name:
        return None

    combined = f"{last_name} {first_name}"
    return normalize_full_name(combined)


def is_usable_first_name(first_name: str | None) -> bool:
    """
    Check whether a Telegram-provided first_name is plausible
    enough to show back to the user (e.g. in "Бачу лише ім'я: {first_name}").

    This is intentionally lenient — only filters out empty/whitespace
    or clearly unusable (digit-only, single-char symbol) values.
    """
    if not first_name:
        return False

    cleaned = first_name.strip()
    if len(cleaned) < 2:
        return False

    if not _NAME_PATTERN.match(cleaned):
        return False

    return True
