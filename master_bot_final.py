import os
import json
import gspread
from datetime import datetime
import pytz
from google.oauth2.service_account import Credentials

# ================= CONFIG =================

IST = pytz.timezone("Asia/Kolkata")

LIVE_MODE = True
TIME_BUFFER_MIN = 3

# === BOT MODE ===
# CONTENT  -> Content Sheet
# DROPSHIP -> Dropshipping Sheet
BOT_MODE = "CONTENT"

# === SHEET IDS (ONLY ID, NOT URL) ===
CONTENT_SHEET_ID = "1Kdd01UAt5rz-9VYDhjFYI4Dh35gaofLipbsjyl8u8hY"
DROPSHIP_SHEET_ID = "1lrn-plbxc7w4wHBLyOCfP_UYIP6EVJb79IdBUP5sgs"

# === GOOGLE CREDS ===
GCP_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

# === COLUMN INDEX (0-based) ===
DATE_COL = 0
DAY_COL = 1
TIME_COL = 2
PLATFORM_COL = 4
TITLE_COL = 7
HASHTAG_COL = 8
DESC_COL = 9
STATUS_COL = 10
LIVE_URL_COL = 11
UPLOAD_DURATION_COL = 12
VIEWS_COL = 13
LIKES_COL = 14
LOG_COL = 15

# ================= SHEET CONNECT =================

def connect_sheet():
    creds_dict = json.loads(GCP_JSON)

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    gc = gspread.authorize(creds)

    if BOT_MODE == "CONTENT":
        return gc.open_by_key(CONTENT_SHEET_ID).worksheet("Content_Sheet")
    else:
        return gc.open_by_key(DROPSHIP_SHEET_ID).worksheet("Sheet1")

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
    caption = f"{description}\n\n{hashtags}"
    return title, caption

# ================= PLATFORM MOCK POSTS =================

def post_instagram(title, caption):
    print("📸 INSTAGRAM POST")
    print(title)
    return "INSTAGRAM_POSTED"

def post_youtube(title, caption):
    print("▶️ YOUTUBE POST")
    print(title)
    return "YOUTUBE_POSTED"

def post_facebook(title, caption):
    print("📘 FACEBOOK POST")
    return "FACEBOOK_POSTED"

def post_pinterest(title, caption):
    print("📌 PINTEREST POST")
    return "PINTEREST_POSTED"

# ================= POST EXECUTOR =================

def execute_posting(row):
    platform = row[PLATFORM_COL].strip().lower()
    title, caption = build_content(row)

    start_time = datetime.now()

    if platform == "instagram":
        result = post_instagram(title, caption)
    elif platform == "youtube":
        result = post_youtube(title, caption)
    elif platform == "facebook":
        result = post_facebook(title, caption)
    elif platform == "pinterest":
        result = post_pinterest(title, caption)
    else:
        result = "UNKNOWN_PLATFORM"

    duration = (datetime.now() - start_time).seconds
    return result, f"{duration}s"

# ================= MAIN BOT =================

def main():
    print("🤖 MASTER BOT STARTED")

    now = datetime.now(IST)
    today_date = now.date()
    today_day = now.strftime("%A")

    sheet = connect_sheet()
    rows = sheet.get_all_values()

    target_row = None

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
            target_row = i + 1
            break

    if not target_row:
        print("⏸️ No matching task found")
        return

    print(f"🎯 MATCH FOUND → ROW {target_row}")

    result, duration = execute_posting(rows[target_row - 1])

    sheet.update_cell(target_row, STATUS_COL + 1, "DONE")
    sheet.update_cell(target_row, LOG_COL + 1, result)
    sheet.update_cell(target_row, UPLOAD_DURATION_COL + 1, duration)

    print("✅ TASK COMPLETED SUCCESSFULLY")

# ================= ENTRY =================

if __name__ == "__main__":
    main()
