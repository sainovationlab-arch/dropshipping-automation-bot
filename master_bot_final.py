# master_bot_final.py
# Paste this exact file into your repo (replace old file).
# Requires secrets: GOOGLE_APPLICATION_CREDENTIALS_JSON, INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_IDS
# Run in GitHub Actions where the secrets are injected as env vars.

import os
import json
import time
import requests
import tempfile
import re
import difflib
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials

# ------------- CONFIG -------------
IST = pytz.timezone("Asia/Kolkata")
TIME_BUFFER_MIN = 30  # Increased tolerance to 30 mins
GRAPH_URL = "https://graph.facebook.com/v19.0"

# Secrets / env
GCP_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
INSTAGRAM_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
RAW_IG_MAP = json.loads(os.environ.get("INSTAGRAM_USER_IDS", "{}"))
SHEET_ID = os.environ.get("SHEET_CONTENT_URL") 

# transfer.sh fallback (no auth)
TRANSFER_SH_BASE = "https://transfer.sh"

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
MAX_IG_PROCESS_WAIT_SEC = 300  # Increased wait time to 5 mins
IG_POLL_INTERVAL = 10 
HTTP_TIMEOUT = 60 

# ------------- Utils -------------
def normalize_text(s: str) -> str:
    if not s: return ""
    return re.sub(r"[^a-z0-9]", "", s.lower())

def fuzzy_find_ig(brand_name: str, threshold=0.35):
    target = normalize_text(brand_name)
    best = None
    best_score = 0.0
    for k, v in RAW_IG_MAP.items():
        score = difflib.SequenceMatcher(None, target, normalize_text(k)).ratio()
        if score > best_score:
            best_score = score
            best = v
    if best_score >= threshold:
        return best
    return None

def is_google_drive_link(url: str):
    return "drive.google.com" in url

def drive_direct_download(url: str):
    # Added confirm=t to bypass large file warnings
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if m:
        fid = m.group(1)
        return f"https://drive.google.com/uc?export=download&confirm=t&id={fid}"
    m2 = re.search(r"id=([a-zA-Z0-9_-]+)", url)
    if m2:
        return f"https://drive.google.com/uc?export=download&confirm=t&id={m2.group(1)}"
    return url

def download_to_temp(url: str, max_mb=300):
    print(f"⬇ Downloading from: {url}")
    tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    total = 0
    try:
        with requests.get(url, stream=True, timeout=HTTP_TIMEOUT) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if not chunk: break
                tmpf.write(chunk)
                total += len(chunk)
                if total > max_mb * 1024 * 1024:
                    tmpf.close()
                    raise Exception("File too large")
        tmpf.close()
        
        # Validation: Check if file is too small (likely HTML error page)
        file_size = os.path.getsize(tmpf.name)
        if file_size < 10000: # Less than 10KB
            with open(tmpf.name, 'r', errors='ignore') as f:
                content = f.read(200)
            raise Exception(f"Download failed (File too small). Content sample: {content}")
            
        print(f"✅ Downloaded locally ({round(file_size/1024/1024, 2)} MB)")
        return tmpf.name
    except Exception as e:
        if os.path.exists(tmpf.name):
            os.remove(tmpf.name)
        raise e

def upload_transfer_sh(local_path):
    print("⬆ Uploading to transfer.sh for Instagram access...")
    filename = os.path.basename(local_path)
    with open(local_path, "rb") as f:
        r = requests.put(f"{TRANSFER_SH_BASE}/{filename}", data=f, timeout=300)
        r.raise_for_status()
        public_url = r.text.strip()
        print(f"🌍 Public Link Generated: {public_url}")
        return public_url

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
    url = f"{GRAPH_URL}/{ig_user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": INSTAGRAM_TOKEN
    }
    r = requests.post(url, data=payload, timeout=HTTP_TIMEOUT)
    try:
        r.raise_for_status()
    except:
        print(f"❌ Creation Failed: {r.text}")
        raise
    return r.json().get("id")

def ig_check_status(container_id):
    url = f"{GRAPH_URL}/{container_id}"
    r = requests.get(url, params={"fields": "status_code", "access_token": INSTAGRAM_TOKEN}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json().get("status_code")

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
def ensure_public_video(url):
    # Always force download to temp and re-upload to transfer.sh
    # This ensures Google Drive cookie issues don't break Instagram
    if is_google_drive_link(url):
        url = drive_direct_download(url)

    # Download locally
    local = download_to_temp(url)
    try:
        # Upload to public server
        public_url = upload_transfer_sh(local)
        return public_url
    finally:
        try:
            os.remove(local)
        except:
            pass

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

    # Get a fresh public link
    public_url = ensure_public_video(video_url)

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
            raise Exception("Instagram rejected the video file (Encoding or Format issue)")
        time.sleep(IG_POLL_INTERVAL)
    else:
        raise Exception("Instagram processing timeout")

    # Publish
    media_id = ig_publish(ig_user_id, creation_id)
    return f"https://www.instagram.com/reel/{media_id}/"

# ------------- Runner -------------
def main():
    print("🤖 MASTER BOT FINAL RUN (GUJARATI FIX VERSION)")
    sheet = connect_sheet()
    rows = sheet.get_all_values()
    
    # Time Config
    now = datetime.now(IST)
    today = now.date()
    day_name = now.strftime("%A").lower()
    
    print(f"📅 System Time: {now} | Day: {day_name}")

    for i in range(1, len(rows)):
        row = rows[i]
        try:
            # Check Status
            if len(row) <= STATUS_COL: continue
            status = (row[STATUS_COL] or "").strip().upper()
            
            if status != "PENDING":
                continue

            # Check Platform
            platform = (row[PLATFORM_COL] or "").strip().lower()
            if "insta" not in platform:
                continue
                
            # Basic Data
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
            
            # Stop after 1 successful post to prevent overload (remove return if you want all at once)
            return 

        except Exception as e:
            print(f"❌ ERROR row {i+1}: {str(e)}")
            sheet.update_cell(i+1, STATUS_COL+1, "FAILED")
            sheet.update_cell(i+1, LOG_COL+1, str(e))
            return # Stop on error to debug

    print("💤 No tasks found.")

if __name__ == "__main__":
    main()
