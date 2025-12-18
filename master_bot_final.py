import os
import json
import time
import requests
import gspread
from datetime import datetime
import pytz
from google.oauth2.service_account import Credentials

# ===================== CONFIG =====================

IST = pytz.timezone("Asia/Kolkata")
TIME_BUFFER_MIN = 3
GRAPH_API_VERSION = "v19.0"

# SHEET IDS
CONTENT_SHEET_ID = "1Kdd01UAt5rz-9VYDhjFYL4Dh35gaofLipbsjyl8u8hY"

# ENV SECRETS
GCP_JSON = os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]
IG_ACCESS_TOKEN = os.environ["FB_ACCESS_TOKEN"]
IG_USER_ID = os.environ["INSTAGRAM_IG_USER_ID"]  # <-- MUST EXIST

# COLUMN INDEX (0-based)
DATE_COL = 0
DAY_COL = 1
TIME_COL = 2
PLATFORM_COL = 4
TITLE_COL = 7
HASHTAG_COL = 8
DESC_COL = 9
STATUS_COL = 10
LIVE_URL_COL = 11
LOG_COL = 15

# ===================== SHEET CONNECT =====================

def connect_sheet():
    creds = Credentials.from_service_account_info(
        json.loads(GCP_JSON),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(CONTENT_SHEET_ID).get_worksheet(0)
    print("✅ Connected to sheet:", sheet.title)
    return sheet

# ===================== TIME =====================

def parse_time(time_str):
    return datetime.strptime(time_str.strip(), "%I:%M %p").time()

# ===================== CONTENT =====================

def build_content(row):
    title = row[TITLE_COL].strip()
    desc = row[DESC_COL].strip()
    tags = row[HASHTAG_COL].strip()
    return title, f"{desc}\n\n{tags}"

# ===================== REAL INSTAGRAM UPLOAD =====================

def upload_instagram_reel(video_url, caption):
    print("📤 Creating Instagram media container...")

    create_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{IG_USER_ID}/media"
    create_payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": IG_ACCESS_TOKEN
    }

    create_resp = requests.post(create_url, data=create_payload).json()

    if "id" not in create_resp:
        raise Exception(f"Media create failed: {create_resp}")

    creation_id = create_resp["id"]
    print("✅ Container created:", creation_id)

    time.sleep(12)  # IMPORTANT

    publish_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{IG_USER_ID}/media_publish"
    publish_payload = {
        "creation_id": creation_id,
        "access_token": IG_ACCESS_TOKEN
    }

    publish_resp = requests.post(publish_url, data=publish_payload).json()

    if "id" not in publish_resp:
        raise Exception(f"Publish failed: {publish_resp}")

    post_id = publish_resp["id"]
    live_url = f"https://www.instagram.com/p/{post_id}/"

    print("🎉 INSTAGRAM REEL POSTED")
    return live_url

# ===================== MAIN BOT =====================

def main():
    print("🤖 MASTER BOT STARTED")

    now = datetime.now(IST)
    today_date = now.date()
    today_day = now.strftime("%A").lower()

    sheet = connect_sheet()
    rows = sheet.get_all_values()

    for i in range(1, len(rows)):
        row = rows[i]

        if row[STATUS_COL].strip().upper() != "PENDING":
            continue

        try:
            row_date = datetime.strptime(row[DATE_COL], "%m-%d-%Y").date()
            row_time = parse_time(row[TIME_COL])
        except:
            continue

        if row_date != today_date:
            continue

        if row[DAY_COL].strip().lower() != today_day:
            continue

        row_dt = IST.localize(datetime.combine(today_date, row_time))
        diff = abs((now - row_dt).total_seconds()) / 60

        if diff > TIME_BUFFER_MIN:
            continue

        platform = row[PLATFORM_COL].strip().lower()
        title, caption = build_content(row)

        try:
            if platform == "instagram":
                video_url = row[LIVE_URL_COL].strip()
                live_url = upload_instagram_reel(video_url, caption)
            else:
                raise Exception("Only Instagram enabled in this final build")

            sheet.update_cell(i + 1, STATUS_COL + 1, "DONE")
            sheet.update_cell(i + 1, LIVE_URL_COL + 1, live_url)
            sheet.update_cell(i + 1, LOG_COL + 1, "INSTAGRAM_POSTED")

            print("✅ TASK COMPLETED")
            return

        except Exception as e:
            sheet.update_cell(i + 1, LOG_COL + 1, str(e))
            print("❌ ERROR:", e)
            return

    print("⏸️ No task to run")

# ===================== ENTRY =====================

if __name__ == "__main__":
    main()
