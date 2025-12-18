import os
import time
import json
import requests
import difflib
import gspread
from google.oauth2.service_account import Credentials

print("🤖 SMART AI BOT STARTED")

GRAPH_URL = "https://graph.facebook.com/v19.0"
ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]

SHEET_URL = os.environ["SHEET_CONTENT_URL"]
TAB_NAME = "Pending_Uploads"

MAX_WAIT_SECONDS = 180   # ⏱️ 3 minutes max
CHECK_INTERVAL = 10      # every 10 seconds

RAW_IG_IDS = json.loads(os.environ["INSTAGRAM_USER_IDS"])


# ================= UTILS =================

def normalize(txt):
    return "".join(c.lower() for c in txt if c.isalnum())


def smart_brand_match(brand_name):
    brand_norm = normalize(brand_name)
    best_id = None
    best_score = 0

    for key, ig_id in RAW_IG_IDS.items():
        score = difflib.SequenceMatcher(
            None, brand_norm, normalize(key)
        ).ratio()

        if score > best_score:
            best_score = score
            best_id = ig_id

    if best_score < 0.4:
        raise Exception(f"Brand match failed: {brand_name}")

    return best_id


# ================= INSTAGRAM =================

def create_media(ig_user_id, video_url, caption):
    r = requests.post(
        f"{GRAPH_URL}/{ig_user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": ACCESS_TOKEN,
        },
    )
    r.raise_for_status()
    cid = r.json()["id"]
    print(f"📦 Container created: {cid}")
    return cid


def wait_until_ready(container_id):
    start = time.time()

    while time.time() - start < MAX_WAIT_SECONDS:
        r = requests.get(
            f"{GRAPH_URL}/{container_id}",
            params={
                "fields": "status_code",
                "access_token": ACCESS_TOKEN,
            },
        )
        r.raise_for_status()

        status = r.json().get("status_code")
        print(f"⏳ Media status: {status}")

        if status == "FINISHED":
            return True

        if status == "ERROR":
            raise Exception("Instagram processing ERROR")

        time.sleep(CHECK_INTERVAL)

    raise Exception("Instagram processing timeout")


def publish_media(ig_user_id, container_id):
    r = requests.post(
        f"{GRAPH_URL}/{ig_user_id}/media_publish",
        data={
            "creation_id": container_id,
            "access_token": ACCESS_TOKEN,
        },
    )
    r.raise_for_status()
    return r.json()["id"]


def post_instagram(video_url, caption, brand_name):
    ig_user_id = smart_brand_match(brand_name)
    container_id = create_media(ig_user_id, video_url, caption)
    wait_until_ready(container_id)
    media_id = publish_media(ig_user_id, container_id)
    print("🎉 INSTAGRAM POSTED")
    return media_id


# ================= GOOGLE SHEET =================

def connect_sheet():
    creds = Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    gc = gspread.authorize(creds)
    sheet = gc.open_by_url(SHEET_URL).worksheet(TAB_NAME)
    print("✅ Connected to sheet:", TAB_NAME)
    return sheet


# ================= MAIN =================

def main():
    sheet = connect_sheet()
    rows = sheet.get_all_records()

    for idx, row in enumerate(rows, start=2):
        try:
            if row["Status"].upper() != "PENDING":
                continue

            if "insta" not in row["Platform"].lower():
                continue

            print(f"🚀 Row {idx} posting…")

            media_id = post_instagram(
                row["Video_Drive_Link"],
                row["Description"],
                row["Brand_Name"],
            )

            sheet.update_cell(idx, list(row.keys()).index("Status") + 1, "DONE")
            print(f"✅ DONE Row {idx} | {media_id}")
            return

        except Exception as e:
            print(f"❌ Row {idx} failed: {e}")
            sheet.update_cell(idx, list(row.keys()).index("Status") + 1, "FAILED")
            return


if __name__ == "__main__":
    main()
