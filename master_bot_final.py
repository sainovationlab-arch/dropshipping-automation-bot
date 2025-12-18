import os
import json
import time
import requests
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials

# ================== CONFIG ==================

IST = pytz.timezone("Asia/Kolkata")
TIME_BUFFER_MIN = 3

BOT_MODE = "CONTENT"  # CONTENT or DROPSHIP

CONTENT_SHEET_ID = "1Kdd01UAt5rz-9VYDhjFYL4Dh35gaofLipbsjyl8u8hY"
DROPSHIP_SHEET_ID = "1lrn-plbxc7w4wHBLYoCfP_UYIP6EVJbj79IdBUP5sgs"

# ================== SECRETS ==================

GCP_JSON = os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]
IG_ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]

# Example:
# {
#   "urban_glint": "17841479492205083",
#   "opal_elite": "17841479493645419"
# }
IG_USER_IDS = json.loads(os.environ["INSTAGRAM_USER_IDS"])

# ================== SHEET COLUMNS (0-BASED) ==================

DATE_COL = 0
DAY_COL = 1
TIME_COL = 2
PLATFORM_COL = 4
BRAND_COL = 5          # 👈 BRAND KEY COLUMN (IMPORTANT)
TITLE_COL = 7
HASHTAG_COL = 8
DESC_COL = 9
STATUS_COL = 10
VIDEO_URL_COL = 11
LOG_COL = 15

# ================== GOOGLE SHEET CONNECT ==================

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

# ================== TIME PARSER ==================

def parse_time(time_str):
    try:
        return datetime.strptime(time_str.strip(), "%I:%M %p").time()
    except:
        return None

# ================== REAL INSTAGRAM POST ==================

def post_instagram(video_url, caption, brand_key):
    if brand_key not in IG_USER_IDS:
        raise Exception(f"❌ Brand key not found: {brand_key}")

    ig_user_id = IG_USER_IDS[brand_key]

    # ---------- STEP 1: CREATE MEDIA ----------
    create_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media"

    create_payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": IG_ACCESS_TOKEN
    }

    r = requests.post(create_url, data=create_payload)
    r.raise_for_status()

    creation_id = r.json().get("id")
    if not creation_id:
        raise Exception("❌ Media container creation failed")

    print("📦 Media container created:", creation_id)

    # ---------- WAIT FOR PROCESSING ----------
    time.sleep(8)

    # ---------- STEP 2: PUBLISH ----------
    publish_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish"

    publish_payload = {
        "creation_id": creation_id,
        "access_token": IG_ACCESS_TOKEN
    }

    r2 = requests.post(publish_url, data=publish_payload)
    r2.raise_for_status()

    media_id = r2.json().get("id")
    if not media_id:
        raise Exception("❌ Publish failed")

    print("🚀 INSTAGRAM REEL POSTED:", media_id)

    return f"https://www.instagram.com/reel/{media_id}/"

# ================== MAIN LOGIC ==================

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

        if row[DAY_COL].strip().lower() != today_day.lower():
            continue

        row_time = parse_time(row[TIME_COL])
        if not row_time:
            continue

        row_dt = IST.localize(datetime.combine(today_date, row_time))
        diff = abs((now - row_dt).total_seconds()) / 60

        if diff > TIME_BUFFER_MIN:
            continue

        platform = row[PLATFORM_COL].strip().lower()
        brand_key = row[BRAND_COL].strip().lower()

        title = row[TITLE_COL].strip()
        desc = row[DESC_COL].strip()
        tags = row[HASHTAG_COL].strip()
        caption = f"{title}\n\n{desc}\n\n{tags}"

        try:
            if platform == "instagram":
                live_url = post_instagram(
                    row[VIDEO_URL_COL],
                    caption,
                    brand_key
                )

                sheet.update_cell(i + 1, STATUS_COL + 1, "DONE")
                sheet.update_cell(i + 1, VIDEO_URL_COL + 1, live_url)
                sheet.update_cell(i + 1, LOG_COL + 1, "INSTAGRAM_POSTED")

                print("✅ TASK COMPLETED")
                return

        except Exception as e:
            sheet.update_cell(i + 1, STATUS_COL + 1, "FAILED")
            sheet.update_cell(i + 1, LOG_COL + 1, str(e))
            raise

    print("⏸️ No task to run")

# ================== ENTRY ==================

if __name__ == "__main__":
    main()
