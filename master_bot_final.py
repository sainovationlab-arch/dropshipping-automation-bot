# master_bot_final.py
# Paste this exact file into your repo (replace old file).
# Requires secrets: GOOGLE_APPLICATION_CREDENTIALS_JSON, INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_IDS
# Run in GitHub Actions where the secrets are injected as env vars.

import os
import json
import time
import requests
import re
import difflib
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials

# ------------- CONFIG -------------
IST = pytz.timezone("Asia/Kolkata")
TIME_BUFFER_MIN = 30
GRAPH_URL = "https://graph.facebook.com/v19.0"

# Secrets / env
GCP_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
INSTAGRAM_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
RAW_IG_MAP = json.loads(os.environ.get("INSTAGRAM_USER_IDS", "{}"))
SHEET_ID = os.environ.get("SHEET_CONTENT_URL") 

# Sheet columns
DATE_COL = 0
DAY_COL = 1
TIME_COL = 2
BRAND_COL = 3
PLATFORM_COL = 4
VIDEO_NAME_COL = 5
VIDEO_URL_COL = 6
TITLE_COL = 7
HASHTAG_COL = 8
DESC_COL = 9
STATUS_COL = 10
LIVE_URL_COL = 11
LOG_COL = 15

# Behavior tuning
MAX_IG_PROCESS_WAIT_SEC = 300
IG_POLL_INTERVAL = 10 
HTTP_TIMEOUT = 60 

# ------------- Utils -------------
def normalize_text(s: str) -> str:
    if not s: return ""
    return re.sub(r"[^a-z0-9]", "", s.lower())

def is_google_drive_link(url: str):
    return "drive.google.com" in url

def drive_direct_download(url: str):
    # Convert View Link to Direct Download Link
    # This works best for files < 100MB
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if m:
        fid = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={fid}"
    m2 = re.search(r"id=([a-zA-Z0-9_-]+)", url)
    if m2:
        return f"https://drive.google.com/uc?export=download&id={m2.group(1)}"
    return url

# ------------- Google Sheet connect -------------
def connect_sheet():
    creds = Credentials.from_service_account_info(
        json.loads(GCP_JSON),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    if SHEET_ID.startswith("http"):
        ss = gc.open_by_url(SHEET_ID)
    else:
        ss = gc.open_by_key(SHEET_ID)
    sheet = ss.get_worksheet(0)
    print("✅ Connected to sheet:", sheet.title)
    return sheet

# ------------- Instagram Helpers -------------
def ig_create_container(ig_user_id, video_url, caption):
    print(f"📡 Sending URL to Instagram: {video_url}")
    url = f"{GRAPH_URL}/{ig_user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": INSTAGRAM_TOKEN
    }
    r = requests.post(url, data=payload, timeout=HTTP_TIMEOUT)
    
    # Catching common errors
    if r.status_code != 200:
        print(f"❌ Instagram Refused: {r.text}")
        if "video_url" in r.text:
             raise Exception("Instagram couldn't download from Drive directly. Ensure Link is 'Anyone with link'")
        raise Exception(f"IG Create Error: {r.text}")
        
    return r.json().get("id")

def ig_check_status(container_id):
    url = f"{GRAPH_URL}/{container_id}"
    r = requests.get(url, params={"fields": "status_code,status", "access_token": INSTAGRAM_TOKEN}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return data.get("status_code") or data.get("status")

def ig_publish(ig_user_id, creation_id):
    url = f"{GRAPH_URL}/{ig_user_id}/media_publish"
    r = requests.post(url, data={"creation_id": creation_id, "access_token": INSTAGRAM_TOKEN}, timeout=HTTP_TIMEOUT)
    try:
        r.raise_for_status()
    except:
        print(f"❌ Publish Failed: {r.text}")
        raise
    return r.json().get("id")

# ------------- Main posting flow -------------
def post_video_to_ig(brand_name, video_url, caption, sheet, row_index):
    # Mapping logic
    ig_user_id = None
    target = normalize_text(brand_name)
    best_score = 0
    for k, v in RAW_IG_MAP.items():
        score = difflib.SequenceMatcher(None, target, normalize_text(k)).ratio()
        if score > best_score:
            best_score = score
            ig_user_id = v
    
    if not ig_user_id or best_score < 0.35:
        raise Exception(f"No IG mapping found for brand: {brand_name}")

    print(f"🎯 Posting to Brand: {brand_name} (ID: {ig_user_id})")

    # DIRECT LINK LOGIC (No Re-upload)
    if is_google_drive_link(video_url):
        public_url = drive_direct_download(video_url)
        print("🔗 Converted to Direct Drive Link")
    else:
        public_url = video_url

    # Create container
    creation_id = ig_create_container(ig_user_id, public_url, caption)
    print("📦 Container Created ID:", creation_id)

    # Poll status
    start = time.time()
    while time.time() - start < MAX_IG_PROCESS_WAIT_SEC:
        status = ig_check_status(creation_id)
        print(f"⏳ Status: {status}")
        
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise Exception("Instagram Failed to Process Video (Drive Link Rejected or Format Issue)")
        time.sleep(IG_POLL_INTERVAL)
    else:
        raise Exception("Instagram processing timeout")

    # Publish
    media_id = ig_publish(ig_user_id, creation_id)
    return f"https://www.instagram.com/reel/{media_id}/"

# ------------- Runner -------------
def main():
    print("🤖 MASTER BOT FINAL RUN (DIRECT DRIVE VERSION)")
    sheet = connect_sheet()
    rows = sheet.get_all_values()
    
    now = datetime.now(IST)
    print(f"📅 System Time: {now}")

    for i in range(1, len(rows)):
        row = rows[i]
        try:
            if len(row) <= STATUS_COL: continue
            status = (row[STATUS_COL] or "").strip().upper()
            
            if status != "PENDING":
                continue

            platform = (row[PLATFORM_COL] or "").strip().lower()
            if "insta" not in platform:
                continue
                
            brand = row[BRAND_COL]
            video_url = row[VIDEO_URL_COL]
            title = row[TITLE_COL]
            desc = row[DESC_COL]
            tags = row[HASHTAG_COL]
            caption = f"{title}\n\n{desc}\n\n{tags}"

            print(f"\n🚀 Processing Row {i+1}: {brand}")
            sheet.update_cell(i+1, LOG_COL+1, "Processing...")

            # Execute Post
            public_live = post_video_to_ig(brand, video_url, caption, sheet, i+1)

            # Success
            sheet.update_cell(i+1, STATUS_COL+1, "DONE")
            sheet.update_cell(i+1, LIVE_URL_COL+1, public_live)
            sheet.update_cell(i+1, LOG_COL+1, "SUCCESS_IG")
            print(f"✅ SUCCESS! Link: {public_live}")
            
            return 

        except Exception as e:
            print(f"❌ ERROR row {i+1}: {str(e)}")
            sheet.update_cell(i+1, STATUS_COL+1, "FAILED")
            sheet.update_cell(i+1, LOG_COL+1, str(e))
            return 

    print("💤 No tasks found.")

if __name__ == "__main__":
    main()
