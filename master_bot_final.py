import os
import json
import time
import requests
import gspread
from datetime import datetime
import pytz
from google.oauth2.service_account import Credentials

# ================== CONFIG ==================

IST = pytz.timezone("Asia/Kolkata")
TIME_BUFFER_MIN = 3

ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]

IG_ACCOUNTS = {
    "URBAN_GLINT": os.environ["INSTAGRAM_URBAN_GLINT_ID"],
    "OPUS_ELITE": os.environ["INSTAGRAM_OPUS_ELITE_ID"],
    "ROYAL_NEXUS": os.environ["INSTAGRAM_ROYAL_NEXUS_ID"],
    "GRAND_ORBIT": os.environ["INSTAGRAM_GRAND_ORBIT_ID"],
    "PEARL_VERSE": os.environ["INSTAGRAM_PEARL_VERSE_ID"],
    "DIAMOND_DICE": os.environ["INSTAGRAM_DIAMOND_DICE_ID"],
    "LUXIVIBE": os.environ["INSTAGRAM_LUXIVIBE_ID"],
}

CONTENT_SHEET_ID = os.environ["SHEET_CONTENT_URL"]
GCP_JSON = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])

DATE_COL = 0
DAY_COL = 1
TIME_COL = 2
BRAND_COL = 3
PLATFORM_COL = 4
TITLE_COL = 7
HASHTAG_COL = 8
DESC_COL = 9
STATUS_COL = 10
LIVE_URL_COL = 11
LOG_COL = 15

# ================== SHEET ==================

def connect_sheet():
    creds = Credentials.from_service_account_info(
        GCP_JSON,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    return gc.open_by_key(CONTENT_SHEET_ID).get_worksheet(0)

# ================== INSTAGRAM UPLOAD ==================

def upload_instagram_video(ig_user_id, video_url, caption):
    create_url = f"https://graph.facebook.com/v24.0/{ig_user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": ACCESS_TOKEN
    }
    r = requests.post(create_url, data=payload).json()
    if "id" not in r:
        raise Exception(r)

    container_id = r["id"]
    time.sleep(10)

    publish_url = f"https://graph.facebook.com/v24.0/{ig_user_id}/media_publish"
    publish = requests.post(
        publish_url,
        data={"creation_id": container_id, "access_token": ACCESS_TOKEN}
    ).json()

    if "id" not in publish:
        raise Exception(publish)

    return f"https://instagram.com/p/{publish['id']}"

# ================== MAIN ==================

def main():
    print("🤖 MASTER BOT STARTED")
    now = datetime.now(IST)

    sheet = connect_sheet()
    rows = sheet.get_all_values()

    for i in range(1, len(rows)):
        row = rows[i]

        if row[STATUS_COL].upper() != "PENDING":
            continue

        if row[PLATFORM_COL].lower() != "instagram":
            continue

        row_date = datetime.strptime(row[DATE_COL], "%m-%d-%Y").date()
        row_time = datetime.strptime(row[TIME_COL], "%I:%M %p").time()
        row_dt = IST.localize(datetime.combine(row_date, row_time))

        if abs((now - row_dt).total_seconds()) / 60 > TIME_BUFFER_MIN:
            continue

        brand = row[BRAND_COL].strip()
        ig_user_id = IG_ACCOUNTS.get(brand)

        if not ig_user_id:
            raise Exception(f"Missing IG ID for {brand}")

        caption = f"{row[DESC_COL]}\n\n{row[HASHTAG_COL]}"
        video_url = row[6]

        live_url = upload_instagram_video(ig_user_id, video_url, caption)

        sheet.update_cell(i+1, STATUS_COL+1, "DONE")
        sheet.update_cell(i+1, LIVE_URL_COL+1, live_url)
        sheet.update_cell(i+1, LOG_COL+1, "INSTAGRAM_POSTED")

        print("✅ REAL INSTAGRAM POST DONE")
        return

    print("⏸️ No task")

if __name__ == "__main__":
    main()
