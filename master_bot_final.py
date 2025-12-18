import os
import json
import gspread
from datetime import datetime
import pytz
from google.oauth2.service_account import Credentials

# ================= CONFIG =================

IST = pytz.timezone("Asia/Kolkata")
TIME_BUFFER_MIN = 3

BOT_MODE = "CONTENT"  # CONTENT or DROPSHIP

CONTENT_SHEET_ID = "1Kdd01UAt5rz-9VYDhjFYL4Dh35gaofLipbsjyl8u8hY"
DROPSHIP_SHEET_ID = "1lrn-plbxc7w4wHBLYoCfP_UYIP6EVJbj79IdBUP5sgs"

GCP_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

# Column indexes (0-based)
DATE_COL = 0
DAY_COL = 1
TIME_COL = 2
PLATFORM_COL = 4
TITLE_COL = 7
HASHTAG_COL = 8
DESC_COL = 9
STATUS_COL = 10
LOG_COL = 15

# ================= SHEET CONNECT =================

def connect_sheet():
    creds_dict = json.loads(GCP_JSON)

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    client = gspread.authorize(creds)

    if BOT_MODE == "CONTENT":
        spreadsheet = client.open_by_key(CONTENT_SHEET_ID)
    else:
        spreadsheet = client.open_by_key(DROPSHIP_SHEET_ID)

    # 🔥 AUTO PICK FIRST WORKSHEET (NO NAME ISSUE)
    sheet = spreadsheet.get_worksheet(0)

    print("✅ Connected to sheet:", sheet.title)
    return sheet

# ================= TIME =================

def parse_time(time_str):
    try:
        return datetime.strptime(time_str.strip(), "%I:%M %p").time()
    except:
        return None

# ================= CONTENT =================

def build_content(row):
    title = row[TITLE_COL].strip()
    desc = row[DESC_COL].strip()
    tags = row[HASHTAG_COL].strip()
    return title, f"{desc}\n\n{tags}"

# ================= MOCK POST =================

def post(platform, title, caption):
    print(f"🚀 Posting to {platform.upper()}")
    print("TITLE:", title)
    return f"{platform.upper()}_POSTED"

# ================= MAIN =================

def main():
    print("🤖 MASTER BOT STARTED")

    now = datetime.now(IST)
    today_date = now.date()
    today_day = now.strftime("%A")

    sheet = connect_sheet()
    rows = sheet.get_all_values()

    for i in range(1, len(rows)):
        row = rows[i]

        if row[STATUS_COL].strip().upper() != "PENDING":
            continue

        try:
            row_date = datetime.strptime(row[DATE_COL], "%m-%d-%Y").date()
        except:
            continue

        if row_date != today_date:
            continue

        if row[DAY_COL].lower() != today_day.lower():
            continue

        row_time = parse_time(row[TIME_COL])
        if not row_time:
            continue

        row_dt = IST.localize(datetime.combine(today_date, row_time))
        diff = abs((now - row_dt).total_seconds()) / 60

        if diff <= TIME_BUFFER_MIN:
            title, caption = build_content(row)
            result = post(row[PLATFORM_COL], title, caption)

            sheet.update_cell(i + 1, STATUS_COL + 1, "DONE")
            sheet.update_cell(i + 1, LOG_COL + 1, result)

            print("✅ TASK COMPLETED")
            return

    print("⏸️ No task to run")

if __name__ == "__main__":
    main()
