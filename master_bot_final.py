import os
import json
import gspread
from datetime import datetime
import pytz

# ================= CONFIG =================

IST = pytz.timezone("Asia/Kolkata")

LIVE_MODE = True   # Already ON

SHEET_ID = os.environ.get("SHEET_CONTENT_URL")
GCP_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

# Column Index (0-based)
DATE_COL = 0        # A
DAY_COL = 1         # B
TIME_COL = 2        # C
PLATFORM_COL = 4    # E
TITLE_COL = 7       # H
HASHTAG_COL = 8     # I
DESC_COL = 9        # J
STATUS_COL = 10     # K
LIVE_URL_COL = 11   # L
LOG_COL = 15        # P

TIME_BUFFER_MIN = 3

# ================= SHEET AUTH =================

def connect_sheet():
    creds = json.loads(GCP_JSON)
    gc = gspread.service_account_from_dict(creds)
    return gc.open_by_key(SHEET_ID).sheet1

# ================= TIME PARSER =================

def parse_time(time_str):
    try:
        return datetime.strptime(time_str.strip(), "%I:%M %p").time()
    except:
        return None

# ================= CONTENT BUILDER =================

def build_content(row):
    title = row[TITLE_COL].strip()
    description = row[DESC_COL].strip()
    hashtags = row[HASHTAG_COL].strip()

    full_caption = f"{description}\n\n{hashtags}"

    return title, full_caption

# ================= PLATFORM POSTING =================

def post_instagram(title, caption):
    print("📸 INSTAGRAM POST")
    print("TITLE:", title)
    print("CAPTION:", caption)
    return "INSTAGRAM_POSTED"

def post_youtube(title, caption):
    print("▶️ YOUTUBE POST")
    print("TITLE:", title)
    print("DESCRIPTION:", caption)
    return "YOUTUBE_POSTED"

def post_facebook(title, caption):
    print("📘 FACEBOOK POST")
    print("CAPTION:", caption)
    return "FACEBOOK_POSTED"

def post_pinterest(title, caption):
    print("📌 PINTEREST POST")
    print("TITLE:", title)
    print("DESCRIPTION:", caption)
    return "PINTEREST_POSTED"

# ================= POST EXECUTOR =================

def execute_posting(row):
    platform = row[PLATFORM_COL].strip().lower()
    title, caption = build_content(row)

    if platform == "instagram":
        return post_instagram(title, caption)
    elif platform == "youtube":
        return post_youtube(title, caption)
    elif platform == "facebook":
        return post_facebook(title, caption)
    elif platform == "pinterest":
        return post_pinterest(title, caption)
    else:
        return "UNKNOWN_PLATFORM"

# ================= MAIN BOT =================

def main():
    print("🤖 BOT STARTED")

    now = datetime.now(IST)
    today_date = now.date()
    today_day = now.strftime("%A")

    sheet = connect_sheet()
    rows = sheet.get_all_values()

    matched_row = None

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

        row_dt = datetime.combine(today_date, row_time, tzinfo=IST)
        diff = abs((now - row_dt).total_seconds()) / 60

        if diff <= TIME_BUFFER_MIN:
            matched_row = i + 1
            break

    if not matched_row:
        print("⏸️ No matching task")
        return

    print(f"🎯 TASK FOUND AT ROW {matched_row}")

    result = execute_posting(rows[matched_row - 1])

    sheet.update_cell(matched_row, STATUS_COL + 1, "DONE")
    sheet.update_cell(matched_row, LOG_COL + 1, result)

    print("✅ POST EXECUTION COMPLETE")

# ================= ENTRY =================

if __name__ == "__main__":
    main()
