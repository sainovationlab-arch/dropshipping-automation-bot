import os
import json
import time
import requests
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials
import re

# ================== BASIC CONFIG ==================

IST = pytz.timezone("Asia/Kolkata")
TIME_BUFFER_MIN = 3

BOT_MODE = "CONTENT"  # CONTENT or DROPSHIP

CONTENT_SHEET_ID = "1Kdd01UAt5rz-9VYDhjFYL4Dh35gaofLipbsjyl8u8hY"
DROPSHIP_SHEET_ID = "1lrn-plbxc7w4wHBLYoCfP_UYIP6EVJbj79IdBUP5sgs"

# ================== SECRETS ==================

GCP_JSON = os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]
IG_ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]

# INSTAGRAM_USER_IDS example:
# {
#   "urban glint": "1784...",
#   "pearl verse": "1784..."
# }
IG_USER_IDS_RAW = json.loads(os.environ["INSTAGRAM_USER_IDS"])

# normalize keys once
IG_USER_IDS = {
    re.sub(r"[^a-z0-9]", "", k.lower()): v
    for k, v in IG_USER_IDS_RAW.items()
}

# ================== SHEET COLUMN INDEXES ==================
# Based exactly on your Google Sheet

DATE_COL = 0
DAY_COL = 1
TIME_COL = 2
BRAND_COL = 3          # ✅ Brand Name column
PLATFORM_COL = 4
VIDEO_NAME_COL = 5
VIDEO_URL_COL = 6
TITLE_COL = 7
HASHTAG_COL = 8
DESC_COL = 9
STATUS_COL = 10
LIVE_URL_COL = 11
LOG_COL = 15

# ================== GOOGLE SHEET ==================

def connect_sheet():
    creds = Credentials.from_service_account_info(
        json.loads(GCP_JSON),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)

    sheet_id = CONTENT_SHEET_ID if BOT_MODE == "CONTENT" else DROPSHIP_SHEET_ID
    sheet = client.open_by_key(sheet_id).get_worksheet(0)

    print("✅ Connected to sheet:", sheet.title)
    return sheet

# ================== TIME ==================

def parse_time(time_str):
    try:
        return datetime.strptime(time_str.strip(), "%I:%M %p").time()
    except:
        return None

# ================== SMART BRAND MATCH ==================

def smart_find_ig_user_id(brand_name):
    if not brand_name:
        return None

    clean = re.sub(r"[^a-z0-9]", "", brand_name.lower())

    if clean in IG_USER_IDS:
        return IG_USER_IDS[clean]

    # fuzzy fallback
    for key in IG_USER_IDS:
        if key in clean or clean in key:
            return IG_USER_IDS[key]

    return None

# ================== INSTAGRAM POST ==================

def post_instagram(video_url, caption, brand_name):
    ig_user_id = smart_find_ig_user_id(brand_name)

    if not ig_user_id:
        raise Exception(f"No IG account match for brand: {brand_name}")

    # 1️⃣ Create media container
    create_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media"
    create_payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": IG_ACCESS_TOKEN
    }

    r = requests.post(create_url, data=create_payload)
    if r.status_code != 200:
        raise Exception(f"Media create failed: {r.text}")

    creation_id = r.json().get("id")
    time.sleep(5)

    # 2️⃣ Publish
    publish_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish"
    publish_payload = {
        "creation_id": creation_id,
        "access_token": IG_ACCESS_TOKEN
    }

    r2 = requests.post(publish_url, data=publish_payload)
    if r2.status_code != 200:
        raise Exception(f"Publish failed: {r2.text}")

    media_id = r2.json().get("id")
    print("🎉 INSTAGRAM REEL POSTED")

    return f"https://www.instagram.com/p/{media_id}/"

# ================== MAIN ==================

def main():
    print("🤖 SMART AI BOT STARTED")

    now = datetime.now(IST)
    today_date = now.date()
    today_day = now.strftime("%A").lower()

    sheet = connect_sheet()
    rows = sheet.get_all_values()

    for i in range(1, len(rows)):
        row = rows[i]

        try:
            if row[STATUS_COL].strip().upper() != "PENDING":
                continue

            row_date = datetime.strptime(row[DATE_COL], "%m-%d-%Y").date()
            if row_date != today_date:
                continue

            if row[DAY_COL].lower() != today_day:
                continue

            row_time = parse_time(row[TIME_COL])
            if not row_time:
                continue

            row_dt = IST.localize(datetime.combine(today_date, row_time))
            diff = abs((now - row_dt).total_seconds()) / 60
            if diff > TIME_BUFFER_MIN:
                continue

            platform = row[PLATFORM_COL].lower().strip()
            brand_name = row[BRAND_COL].strip()
            video_url = row[VIDEO_URL_COL].strip()

            title = row[TITLE_COL].strip()
            desc = row[DESC_COL].strip()
            tags = row[HASHTAG_COL].strip()
            caption = f"{title}\n\n{desc}\n\n{tags}"

            if platform == "instagram":
                live_url = post_instagram(video_url, caption, brand_name)

                sheet.update_cell(i + 1, STATUS_COL + 1, "DONE")
                sheet.update_cell(i + 1, LIVE_URL_COL + 1, live_url)
                sheet.update_cell(i + 1, LOG_COL + 1, "INSTAGRAM_POSTED")

                print("✅ TASK COMPLETED")
                return

        except Exception as e:
            sheet.update_cell(i + 1, STATUS_COL + 1, "FAILED")
            sheet.update_cell(i + 1, LOG_COL + 1, str(e))
            print("❌ ERROR:", e)
            return

    print("⏸️ No task to run")

# ================== ENTRY ==================

if __name__ == "__main__":
    main()
