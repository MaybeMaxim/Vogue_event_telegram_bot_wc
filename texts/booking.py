"""
User-facing strings for the booking drill-down ("✍️ Записатись").

ParseMode.HTML is active; dynamic DB text is html.escape()d in
services.booking_service before insertion here.
"""

# Step 1 — day picker
BOOK_INTRO = "На який день хочете записатись? 👇"

# Step 2 — slot picker. The intro is followed by a per-slot overview
# (time + the activities in that slot), then time buttons below.
SLOT_PICKER_INTRO = "📅 <b>День {day} ({date})</b>"
SLOT_PICKER_PROMPT = "Оберіть час, щоб побачити деталі та записатись 👇"

# One block in the slot-picker overview: time header + activity names.
SLOT_OVERVIEW_BLOCK = "🕒 <b>{time_range}</b>\n{names}"

# Step 3 — activity picker (one slot)
ACTIVITY_PICKER_HEADER = "🕒 <b>{time_range}</b>"
ACTIVITY_PICKER_EXCLUSIVE_HINT = "<i>Можна обрати лише один варіант із цього часу.</i>"
ACTIVITY_PICKER_LINE = "{dot} <b>{title}</b> — {seats}"
ACTIVITY_PICKER_SPEAKER = "    👤 {speaker_name}"
ACTIVITY_PICKER_DESC = "    <i>{description}</i>"

# Buttons
BOOK_ACTIVITY_BUTTON = "✍️ Записатись на «{title}»"
WAITLIST_ACTIVITY_BUTTON = "🔔 Лист очікування: «{title}»"
BACK_TO_SLOTS_BUTTON = "⬅️ Назад до часу"
BACK_TO_DAYS_BUTTON = "⬅️ Обрати інший день"

# Consultation slot button (leads into the per-slot consultation picker)
CONSULTATION_SLOT_BUTTON = "🩺 {time_range} · Консультації Анни Барінової"

# --- Consultation slot picker ---------------------------------------------
CONSULTATION_PICKER_HEADER = (
    "🩺 <b>Консультації Анни Барінової</b>\n"
    "{time_range}\n\n"
    "Оберіть вільний час для індивідуальної консультації (15 хв) 👇"
)
CONSULTATION_SLOT_FREE = "🟢 {time}"
CONSULTATION_SLOT_TAKEN = "🔴 {time} — зайнято (черга очікування →)"
CONSULTATION_NONE_FREE = (
    "🩺 <b>Консультації Анни Барінової</b>\n\n"
    "На жаль, усі слоти наразі зайняті. "
    "Ви можете приєднатись до листа очікування на конкретний час."
)

# --- Booking confirmation card --------------------------------------------
CONFIRM_BOOKING = (
    "Підтвердьте запис 👇\n\n"
    "🗓 <b>{title}</b>\n"
    "🕒 {time_range}\n\n"
    "Ваші дані:\n"
    "👤 {full_name}\n"
    "📱 {phone}\n\n"
    "Все вірно?"
)
CONFIRM_BUTTON = "✅ Підтвердити запис"
CONFIRM_EDIT_DATA_BUTTON = "✏️ Змінити мої дані"
CONFIRM_CANCEL_BUTTON = "⬅️ Назад"
# After a successful booking — return to the same day's slot list to book more.
BACK_TO_DAY_BUTTON = "⬅️ Повернутись до Дня {day}"

# --- Booking outcome messages ---------------------------------------------
BOOKED_OK = (
    "✅ Готово! Вас записано:\n\n"
    "🗓 <b>{title}</b>\n"
    "🕒 {time_range}\n\n"
    "Нагадування надішлемо перед початком. Керувати записами можна в «📋 Мої записи»."
)
ALREADY_BOOKED = "Ви вже записані на «{title}» 🙂"
CONFLICT_FOUND = (
    "⚠️ На цей час у вас вже є запис:\n\n"
    "🗓 <b>{conflict_title}</b>\n"
    "🕒 {conflict_time}\n\n"
    "Не можна бути у двох місцях одночасно. "
    "Спершу скасуйте попередній запис, якщо хочете змінити вибір."
)
CONSULTATION_CONFLICT_FOUND = (
    "⚠️ Ви вже записані на консультацію Анни Барінової:\n\n"
    "🗓 <b>{conflict_title}</b>\n\n"
    "Можна мати лише одну консультацію. "
    "Скасуйте поточний запис, якщо хочете обрати інший час."
)
BOOKED_OK_WAITLIST_DROPPED = (
    "✅ Готово! Вас записано:\n\n"
    "🗓 <b>{title}</b>\n"
    "🕒 {time_range}\n\n"
    "ℹ️ Ваше місце в черзі очікування на «{dropped_title}» було автоматично скасовано, "
    "оскільки можна мати лише одну консультацію."
)
WAITLIST_CONSULTATION_CONFLICT = (
    "⚠️ Ви вже перебуваєте в черзі очікування на іншу консультацію Анни Барінової. "
    "Можна чекати лише на одну консультацію одночасно."
)
WAITLIST_OFFER_CONFIRMED_SWAPPED = (
    "✅ Чудово! Вас записано на «{title}».\n"
    "🕒 {time_range}\n\n"
    "Запис на «{swapped_title}» скасовано автоматично."
)
CONFLICT_CANCEL_BUTTON = "❌ Скасувати «{conflict_title}»"
ACTIVITY_FULL_OFFER_WAITLIST = (
    "😔 На жаль, місць на «{title}» вже немає.\n\n"
    "Хочете приєднатись до листа очікування? Якщо місце звільниться, "
    "ми одразу повідомимо вас."
)
JOIN_WAITLIST_BUTTON = "🔔 Так, у лист очікування"
BOOKING_NOT_FOUND = "Не вдалося знайти цю активність. Спробуйте ще раз."

# --- Waitlist outcome messages --------------------------------------------
WAITLIST_JOINED = (
    "🔔 Вас додано до листа очікування на «{title}».\n"
    "Ваша позиція в черзі: <b>{position}</b>.\n\n"
    "Щойно звільниться місце, ми надішлемо вам запрошення підтвердити запис."
)
WAITLIST_ALREADY = "Ви вже у листі очікування на «{title}» 🙂"
WAITLIST_SEAT_AVAILABLE = "Гарні новини — місце звільнилося! Спробуйте записатись ще раз."

# --- Waitlist promotion (offer) notification ------------------------------
WAITLIST_OFFER = (
    "🎉 Звільнилося місце на «{title}»!\n"
    "🕒 {time_range}\n\n"
    "Підтвердьте, будь ласка, протягом {minutes} хв, інакше місце "
    "перейде наступному в черзі."
)
WAITLIST_OFFER_CONFLICT_WARNING = (
    "\n\n⚠️ Якщо ви підтвердите, ваш поточний запис на «{conflict_title}» "
    "(🕒 {conflict_time}) буде автоматично скасовано."
)
WAITLIST_OFFER_CONFIRM_BUTTON = "✅ Підтвердити запис"
WAITLIST_OFFER_DECLINE_BUTTON = "❌ Відмовитись"
WAITLIST_OFFER_CONFIRMED = (
    "✅ Чудово! Вас записано на «{title}». Деталі — у «📋 Мої записи»."
)
WAITLIST_OFFER_DECLINED = "Зрозуміло, місце передамо наступному. Дякуємо!"
WAITLIST_OFFER_EXPIRED = "На жаль, час підтвердження минув, і місце вже передано далі."
WAITLIST_OFFER_TAKEN = "На жаль, місце вже зайняте."

# Placeholder kept for any not-yet-wired callbacks.
BOOKING_COMING_SOON = "🚧 Ця дія буде доступна найближчим часом."

# --- Time-driven notifications (ticker) -----------------------------------
REMINDER = (
    "⏰ Нагадування!\n\n"
    "🗓 <b>{title}</b>\n"
    "🕒 {time_range}\n"
    "📍 {location}\n\n"
    "Скоро початок — чекаємо на вас 🙂"
)

CONFIRMATION_REQUEST = (
    "⏰ Зовсім скоро починається:\n\n"
    "🗓 <b>{title}</b>\n"
    "🕒 {time_range}\n"
    "📍 {location}\n\n"
    "Підтвердьте, будь ласка, що будете — інакше місце звільниться для інших."
)
CONFIRM_ATTENDANCE_BUTTON = "✅ Я буду"
CANT_MAKE_BUTTON = "❌ Не зможу"

ATTENDANCE_CONFIRMED = "✅ Дякуємо! Чекаємо на вас 🙂"
ATTENDANCE_DECLINED = "Зрозуміло, дякуємо що попередили. Місце передамо іншим."
ATTENDANCE_EXPIRED = "На жаль, час підтвердження минув."

NO_SHOW_RELEASED = (
    "⌛️ Ви не підтвердили участь, тож місце на «{title}» звільнено.\n"
    "Якщо плани змінились — можете записатись знову, якщо є вільні місця."
)

BOOKING_ABORTED = "Скасовано."
EDIT_DATA_PROMPT = "Оновіть дані в профілі, а потім поверніться до запису 🙂"
CONFLICT_CANCELLED_TRY_AGAIN_BUTTON = "✍️ Записатись тепер"
CONFLICT_CANCELLED = "Попередній запис скасовано. Тепер можете обрати інший варіант 🙂"
WAITLIST_JOINED_WITH_CONFLICT = (
    "🔔 Вас додано до листа очікування на «{title}».\n"
    "Ваша позиція в черзі: <b>{position}</b>.\n\n"
    "⚠️ Якщо місце звільниться, ваш поточний запис на «{conflict_title}» буде автоматично скасовано."
)

NO_ACTIVITIES_FOR_DAY = "На цей день активностей не знайдено."
