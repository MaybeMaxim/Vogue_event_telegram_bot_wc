"""User-facing strings for the 📋 Мої записи section."""

MY_BOOKINGS_HEADER = "📋 <b>Мої записи</b>"
MY_BOOKINGS_EMPTY = (
    "📋 <b>Мої записи</b>\n\n"
    "У вас поки немає записів. Перейдіть до «✍️ Записатись», щоб обрати активність 🙂"
)

# Day section header within the list.
DAY_SECTION = "<b>📆 День {day} ({date})</b>"

# One booking entry: time + bold title (+ optional location line).
BOOKING_ENTRY = "🕒 {time_range}  —  <b>{title}</b>"
BOOKING_LOCATION = "      📍 {location}"

CANCEL_BUTTON = "❌ {time} {title}"
CANCELLED_OK = "Запис на «{title}» скасовано."
CANCEL_FAILED = "Не вдалося скасувати запис. Можливо, його вже скасовано."
