import os
import json
import requests
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials

# ================= CONFIG =================

IST = pytz.timezone("Asia/Kolkata")
TIME_BUFFER_MIN = 3

CONTENT_SHEET_ID = "1Kdd01UAt5rz-9VYDhjFYL4Dh35gaofLipbsjyl8u8hY"

GCP_JSON = os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]
IG_ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]

# 🔥 BRAND NAME → IG USER ID (FINAL)
INSTAGRAM_BRAND_MAP = {
    "pearl verse": "17841478822408000",
    "diamond dice": "17841478369307404",
    "emerald edge": "17841479056452004",
    "grand orbit": "17841479516066757",
    "royal nexus": "17841479056452004",
    "opus elite": "17841479493645419",
    "urban glint": "17841479492205083",
    "luxivibe": "17841478140648372"
}

# Column indexes (0-based)
DATE_COL = 0
DAY_COL = 1
TIME_COL = 2
BRAND_COL = 3
PLATFORM_COL = 4
VIDEO_COL = 6
TITLE_COL = 7
HASHTAG_COL = 8
DESC_COL = 9
STATUS_COL = 10
LIVE_URL_COL = 11
LOG_COL = 15

# ================= SHEET =================

def connect_sheet():
    creds = Credentials.from_service_account_info(
        json.loads(GCP_JSON),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(CONTENT_SHEET_ID).get_worksheet(0)
    print("✅ Connected to sheet:", sheet.title)
    return sheet

def parse_time(t):
    try:
        return datetime.strptime(t.strip(), "%I:%M %p").time()
    except:
        return None

# ================= INSTAGRAM =================

def post_instagram(video_url, caption, brand_name):
    key = brand_name.strip().lower()

    if key not in INSTAGRAM_BRAND_MAP:
        raise Exception(f"❌ Unknown Brand Name: {brand_name}")

    ig_user_id = INSTAGRAM_BRAND_MAP[key]

    # Create media
    r = requests.post(
        f"https://graph.facebook.com/v19.0/{ig_user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": IG_ACCESS_TOKEN
        }
    )
    r.raise_for_status()
    creation_id = r.json()["id"]

    # Publish
    r2 = requests.post(
        f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": IG_ACCESS_TOKEN
        }
    )
    r2.raise_for_status()
    media_id = r2.json()["id"]

    return f"https://www.instagram.com/p/{media_id}/"

# ================= MAIN =================

def main():
    print("🤖 MASTER BOT STARTED")
    now = datetime.now(IST)
    today = now.date()
    day = now.strftime("%A").lower()

    sheet = connect_sheet()
    rows = sheet.get_all_values()

    for i in range(1, len(rows)):
        row = rows[i]

        if row[STATUS_COL].upper() != "PENDING":
            continue

        if row[DAY_COL].lower() != day:
            continue

        if datetime.strptime(row[DATE_COL], "%m-%d-%Y").date() != today:
            continue

        t = parse_time(row[TIME_COL])
        if not t:
            continue

        scheduled = IST.localize(datetime.combine(today, t))
        if abs((now - scheduled).total_seconds()) > TIME_BUFFER_MIN * 60:
            continue

        try:
            caption = f"{row[TITLE_COL]}\n\n{row[DESC_COL]}\n\n{row[HASHTAG_COL]}"
            live = post_instagram(row[VIDEO_COL], caption, row[BRAND_COL])

            sheet.update_cell(i+1, STATUS_COL+1, "DONE")
            sheet.update_cell(i+1, LIVE_URL_COL+1, live)
            sheet.update_cell(i+1, LOG_COL+1, "INSTAGRAM_POSTED")

            print("✅ POSTED:", row[BRAND_COL])
            return

        except Exception as e:
            sheet.update_cell(i+1, STATUS_COL+1, "FAILED")
            sheet.update_cell(i+1, LOG_COL+1, str(e))
            raise

    print("⏸️ No task to run")

if __name__ == "__main__":
    main()
