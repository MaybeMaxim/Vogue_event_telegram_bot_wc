# Google Sheets live sync — setup

The bot can mirror all bookings into a Google Spreadsheet that your team
opens in a browser. It refreshes automatically (about once a minute, only
when something changed). The in-bot `.xlsx` export keeps working with no
setup, so this is optional.

## 1. Create a Google Cloud project + service account

1. Go to https://console.cloud.google.com/ and create (or pick) a project.
2. Enable two APIs for that project:
   - **Google Sheets API**
   - **Google Drive API**
   (APIs & Services → Library → search → Enable.)
3. APIs & Services → Credentials → **Create credentials → Service account**.
   Give it any name; no roles are required.
4. Open the new service account → **Keys → Add key → Create new key → JSON**.
   A `.json` file downloads. This is the bot's credential.

## 2. Put the key next to the bot

- Save the downloaded file as `google_credentials.json` in the project root
  (or set `GSHEETS_CREDENTIALS_FILE` to its path in `.env`).
- **Do not commit it** — it's already covered by `.gitignore`.

## 3. Choose how the spreadsheet is created

The service-account JSON contains a `client_email` like
`something@your-project.iam.gserviceaccount.com`.

**Option A — let the bot create the sheet (simplest):**
- Leave `GSHEETS_SPREADSHEET_ID` empty.
- On first sync the bot creates a spreadsheet and logs its id + URL.
- That sheet is owned by the service account, so to let your team see it,
  open the URL from the logs while signed in as the service account is not
  possible directly — instead use Option B, or have the bot share it (the
  created sheet is private to the service account until shared). For a team,
  Option B is usually easier.

**Option B — you create the sheet and share it (recommended for teams):**
1. Create a blank Google Sheet in your own Google account.
2. Click **Share**, add the service account's `client_email` as **Editor**.
3. Copy the spreadsheet id from its URL
   (`https://docs.google.com/spreadsheets/d/THIS_PART/edit`).
4. Put it in `.env` as `GSHEETS_SPREADSHEET_ID=...`.
5. Share the same sheet with your team members (View or Edit) as normal.

## 4. Enable it in `.env`

```
GSHEETS_ENABLED=true
GSHEETS_CREDENTIALS_FILE=google_credentials.json
GSHEETS_SPREADSHEET_ID=...   # from Option B, or empty for Option A
GSHEETS_SYNC_SECONDS=60
```

Install deps and run:

```
pip install -r requirements.txt
python bot.py
```

## What you get

- One tab per activity: №, Прізвище та ім'я, Телефон, Email, Статус,
  Присутність (the attendance column reflects on-site check-ins).
- A **Контакти** tab with every registered guest.
- A **Листи очікування** tab with all waitlist entries and positions.

Admins can also tap **/admin → 📊 Експорт → 🔗 Google Таблиця** to force a
refresh and get the live link.

## Notes

- The sync runs only when bookings changed, so it stays well under Google's
  API limits even during a rush.
- The bot's host must allow outbound HTTPS to `googleapis.com`.
- If credentials are missing or sync fails, the bot logs a warning and keeps
  running normally — bookings are never blocked by a Sheets problem.
