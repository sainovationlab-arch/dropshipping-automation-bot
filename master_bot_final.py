import os
import time
import json
import requests
import difflib
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

print("🤖 SMART AI BOT STARTED")

# ================= CONFIG =================

GRAPH_URL = "https://graph.facebook.com/v19.0"
INSTAGRAM_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

SHEET_URL = os.environ.get("SHEET_CONTENT_URL")
SHEET_TAB = "Pending_Uploads"

# Column names (exactly sheet headers)
COL_BRAND = "Brand_Name"
COL_PLATFORM = "Platform"
COL_VIDEO = "Video_Drive_Link"
COL_CAPTION = "Description"
COL_STATUS = "Status"

# Instagram brand → user id mapping (existing env)
RAW_IG_IDS = json.loads(os.environ.get("INSTAGRAM_USER_IDS", "{}"))

# =========================================


def normalize(text):
    if not text:
        return ""
    return "".join(c.lower() for c in text if c.isalnum())


def smart_find_ig_user(brand_text):
    brand_norm = normalize(brand_text)

    best_match = None
    best_score = 0

    for brand, ig_id in RAW_IG_IDS.items():
        score = difflib.SequenceMatcher(
            None, brand_norm, normalize(brand)
        ).ratio()

        if score > best_score:
            best_score = score
            best_match = ig_id

    if best_match and best_score >= 0.4:
        return best_match

    raise Exception(f"No confident IG match for brand: {brand_text}")


# ================= INSTAGRAM CORE =================

def ig_create_media(ig_user_id, video_url, caption):
    url = f"{GRAPH_URL}/{ig_user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": INSTAGRAM_TOKEN,
    }
    r = requests.post(url, data=payload)
    r.raise_for_status()
    return r.json()["id"]


def ig_wait_until_ready(container_id, timeout=300):
    status_url = f"{GRAPH_URL}/{container_id}"
    start = time.time()

    while True:
        r = requests.get(
            status_url,
            params={
                "fields": "status_code",
                "access_token": INSTAGRAM_TOKEN,
            },
        )
        r.raise_for_status()
        status = r.json().get("status_code")

        if status == "FINISHED":
            return True

        if status == "ERROR":
            raise Exception("Instagram processing failed")

        if time.time() - start > timeout:
            raise Exception("Timeout waiting for Instagram processing")

        time.sleep(10)  # SAFE WAIT


def ig_publish(ig_user_id, container_id):
    url = f"{GRAPH_URL}/{ig_user_id}/media_publish"
    r = requests.post(
        url,
        data={
            "creation_id": container_id,
            "access_token": INSTAGRAM_TOKEN,
        },
    )
    r.raise_for_status()
    return r.json()


def post_instagram(video_url, caption, brand_name):
    ig_user_id = smart_find_ig_user(brand_name)

    container_id = ig_create_media(ig_user_id, video_url, caption)

    ig_wait_until_ready(container_id)

    publish_result = ig_publish(ig_user_id, container_id)

    return publish_result.get("id")


# ================= GOOGLE SHEET =================

def connect_sheet():
    creds = Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]),
        scopes=SCOPES,
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SHEET_URL).worksheet(SHEET_TAB)
    print(f"✅ Connected to sheet: {SHEET_TAB}")
    return sheet


# ================= MAIN =================

def main():
    sheet = connect_sheet()
    rows = sheet.get_all_records()

    for idx, row in enumerate(rows, start=2):
        try:
            if row.get(COL_STATUS, "").upper() == "DONE":
                continue

            platform = row.get(COL_PLATFORM, "").lower()
            if "insta" not in platform:
                continue

            brand = row.get(COL_BRAND)
            video = row.get(COL_VIDEO)
            caption = row.get(COL_CAPTION, "")

            print(f"🚀 Posting Instagram | Row {idx} | {brand}")

            post_id = post_instagram(video, caption, brand)

            sheet.update_cell(idx, list(row.keys()).index(COL_STATUS) + 1, "DONE")

            print(f"✅ Instagram posted successfully: {post_id}")

        except Exception as e:
            print(f"❌ ERROR Row {idx}: {e}")
            continue


if __name__ == "__main__":
    main()
