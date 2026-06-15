"""
User-facing strings for the 💬 Підтримка (support) section.
"""

SUPPORT_INTRO = (
    "💬 <b>Підтримка</b>\n\n"
    "Чим можемо допомогти? Оберіть один із варіантів 👇"
)

CONTACT_ORGANIZER_BUTTON = "📞 Зв'язатися з організатором"
ASK_QUESTION_BUTTON = "❓ Поставити запитання"
REPORT_BUG_BUTTON = "🐞 Повідомити про помилку"
CLOSE_BUTTON = "✅ Закрити"

CANCEL_BUTTON = "❌ Скасувати"

# Contact organizer
CONTACT_ORGANIZER = (
    "📞 <b>Зв'язок з організатором</b>\n\n"
    "Напишіть нам напряму: {contact}\n\n"
    "Ми відповімо якнайшвидше 🙂"
)

# Ask a question
ASK_QUESTION_PROMPT = (
    "❓ Напишіть ваше запитання одним повідомленням — "
    "ми передамо його команді заходу."
)
QUESTION_SENT = "✅ Дякуємо! Ваше запитання надіслано команді. Ми зв'яжемось із вами за потреби."

# Report a bug
REPORT_BUG_PROMPT = (
    "🐞 Опишіть, будь ласка, що пішло не так — "
    "що ви робили й що сталося. Це допоможе нам швидко все виправити."
)
BUG_SENT = "✅ Дякуємо за повідомлення! Ми розберемось із цим якнайшвидше."

# Shown if there's nowhere to route the submission (misconfiguration).
SUBMISSION_FAILED = "⚠️ Не вдалося надіслати повідомлення. Спробуйте, будь ласка, пізніше."

CANCELLED = "Скасовано."

# Forwarded-to-support formatting (sent to the support chat, not the user).
FWD_QUESTION = "❓ <b>Нове запитання</b>\nВід: {user} (id <code>{tg_id}</code>)\n\n{text}"
FWD_BUG = "🐞 <b>Повідомлення про помилку</b>\nВід: {user} (id <code>{tg_id}</code>)\n\n{text}"
