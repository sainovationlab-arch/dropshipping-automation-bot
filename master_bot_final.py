import os
import json
import requests
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials
from difflib import SequenceMatcher

# ================= CONFIG =================

IST = pytz.timezone("Asia/Kolkata")
TIME_BUFFER_MIN = 5

CONTENT_SHEET_ID = "1Kdd01UAt5rz-9VYDhjFYL4Dh35gaofLipbsjyl8u8hY"

GCP_JSON = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
IG_ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]

# 🔥 ALL IG ACCOUNTS (ONE TIME)
RAW_IG_USERS = json.loads(os.environ["INSTAGRAM_USER_IDS"])

# Sheet Columns (0-based)
DATE_COL = 0
DAY_COL = 1
TIME_COL = 2
PLATFORM_COL = 4
BRAND_COL = 5          # 👈 Brand Name column
TITLE_COL = 7
HASHTAG_COL = 8
DESC_COL = 9
STATUS_COL = 10
VIDEO_URL_COL = 11
LOG_COL = 15

# ================= HELPERS =================

def normalize(text):
    return "".join(text.lower().split())

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def smart_find_ig_user(brand_name):
    target = normalize(brand_name)

    best_match = None
    best_score = 0

    for name, ig_id in RAW_IG_USERS.items():
        score = similarity(target, normalize(name))
        if score > best_score:
            best_score = score
            best_match = ig_id

    if best_score < 0.70:
        raise Exception(f"No confident IG match for brand: {brand_name}")

    return best_match

# ================= SHEET =================

def connect_sheet():
    creds = Credentials.from_service_account_info(
        GCP_JSON,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(CONTENT_SHEET_ID).get_worksheet(0)
    print("✅ Connected to sheet:", sheet.title)
    return sheet

# ================= INSTAGRAM =================

def post_instagram(video_url, caption, ig_user_id):
    create_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media"

    r = requests.post(create_url, data={
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": IG_ACCESS_TOKEN
    })
    r.raise_for_status()

    creation_id = r.json()["id"]

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
    print("🤖 SMART AI BOT STARTED")

    now = datetime.now(IST)
    today = now.date()
    today_day = now.strftime("%A").lower()

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

        if row_date != today:
            continue

        if row[DAY_COL].strip().lower() != today_day:
            continue

        try:
            post_time = datetime.strptime(row[TIME_COL], "%I:%M %p").time()
        except:
            continue

        scheduled = IST.localize(datetime.combine(today, post_time))
        if abs((now - scheduled).total_seconds()) / 60 > TIME_BUFFER_MIN:
            continue

        platform = row[PLATFORM_COL].lower()
        brand_name = row[BRAND_COL]

        title = row[TITLE_COL]
        desc = row[DESC_COL]
        tags = row[HASHTAG_COL]
        caption = f"{title}\n\n{desc}\n\n{tags}"

        try:
            if platform == "instagram":
                ig_user_id = smart_find_ig_user(brand_name)

                live_url = post_instagram(
                    row[VIDEO_URL_COL],
                    caption,
                    ig_user_id
                )

                sheet.update_cell(i+1, STATUS_COL+1, "DONE")
                sheet.update_cell(i+1, VIDEO_URL_COL+1, live_url)
                sheet.update_cell(i+1, LOG_COL+1, "INSTAGRAM_POSTED")

                print("🎉 POSTED SUCCESSFULLY")
                return

        except Exception as e:
            sheet.update_cell(i+1, STATUS_COL+1, "FAILED")
            sheet.update_cell(i+1, LOG_COL+1, str(e))
            raise

    print("⏸️ No task to run")

# ================= ENTRY =================

if __name__ == "__main__":
    main()
