import os
import json
import time
import random
import requests
import re
import gspread
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================

def get_env_var(keys, default=None):
    for key in keys:
        val = os.environ.get(key)
        if val: return val
    return default

# Secrets
GCP_CREDENTIALS_JSON = get_env_var(["GCP_CREDENTIALS", "GOOGLE_APPLICATION_CREDENTIALS_JSON", "GOOGLE_CREDENTIALS"])
SPREADSHEET_ID = get_env_var(["SPREADSHEET_ID", "SHEET_CONTENT_URL", "SHEET_DROPSHIPPING_URL"])
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")
PINTEREST_SESSION = os.environ.get("PINTEREST_SESSION")
PINTEREST_BOARD_ID = os.environ.get("PINTEREST_BOARD_ID")

# Instagram IDs
INSTAGRAM_IDS = {
    "Emerald Edge": "17841478369307404", "Urban Glint": "17841479492205083",
    "Diamond Dice": "17841478369307404", "Grand Orbit": "17841479516066757",
    "Opus": "17841479493645419", "Opus Elite": "17841479493645419",
    "Pearl Verse": "17841478822408000", "Royal Nexus": "17841479056452004",
    "Luxivibe": "17841479492205083"
}

# YouTube Token Map
YOUTUBE_PROJECT_MAP = {
    "Pearl Verse": os.environ.get("YT_PEARL_VERSE"), "Opus Elite": os.environ.get("YT_OPUS_ELITE"),
    "Diamond Dice": os.environ.get("YT_DIAMOND_DICE"), "Emerald Edge": os.environ.get("YT_EMERALD_EDGE"),
    "Royal Nexus": os.environ.get("YT_ROYAL_NEXUS"), "Grand Orbit": os.environ.get("YT_GRAND_ORBIT"),
    "Urban Glint": os.environ.get("YT_URBAN_GLINT"), "Luxivibe": os.environ.get("YT_LUXI_VIBE")
}

# ==============================================================================
# 2. HELPER FUNCTIONS
# ==============================================================================

def get_val(row, keys):
    """Smart Column Reader"""
    normalized_row = {k.lower().replace(" ", "").replace("_", ""): v for k, v in row.items()}
    for key in keys:
        if key in row: return str(row[key]).strip()
        norm_key = key.lower().replace(" ", "").replace("_", "")
        if norm_key in normalized_row: return str(normalized_row[norm_key]).strip()
    return ""

def get_sheet_service():
    if not GCP_CREDENTIALS_JSON:
        print("❌ FATAL: GCP_CREDENTIALS missing.")
        return None
    try:
        creds = ServiceAccountCredentials.from_service_account_info(
            json.loads(GCP_CREDENTIALS_JSON), 
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        client = gspread.authorize(creds)
        if "docs.google.com" in SPREADSHEET_ID: return client.open_by_url(SPREADSHEET_ID).sheet1
        return client.open_by_key(SPREADSHEET_ID).sheet1
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

def download_video_locally(url):
    print(f"⬇️ Downloading video...")
    if "drive.google.com" in url:
        m = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
        id_val = m.group(1) if m else (re.search(r"id=([a-zA-Z0-9_-]+)", url).group(1) if re.search(r"id=([a-zA-Z0-9_-]+)", url) else None)
        if id_val: url = f"https://drive.google.com/uc?export=download&confirm=t&id={id_val}"
    
    filename = f"temp_{random.randint(1000,9999)}.mp4"
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        return filename
    except Exception as e:
        print(f"❌ Download Error: {e}")
        return None

def upload_to_catbox(local_path):
    print("🐱 Uploading to Catbox...")
    try:
        with open(local_path, "rb") as f:
            r = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"}, files={"fileToUpload": ("video.mp4", f, "video/mp4")}, timeout=300)
            return r.text.strip() if r.status_code == 200 else None
    except: return None

def safe_update_cell(sheet, row, col, value):
    try: sheet.update_cell(row, col, value)
    except: pass

# ==============================================================================
# 3. PLATFORM FUNCTIONS
# ==============================================================================

def instagram_post(row, row_num):
    account = get_val(row, ['Account_Name', 'Account Name', 'Brand', 'AccountName'])
    if not account:
        print(f"⚠️ Row {row_num}: No Account Name found.")
        return None

    page_id = INSTAGRAM_IDS.get(account)
    if not page_id: 
        print(f"⚠️ Row {row_num}: No ID for '{account}'")
        return None
    
    video_url = get_val(row, ['Video_URL', 'Video URL'])
    caption = get_val(row, ['Caption', 'Title'])
    tags = get_val(row, ['Tags', 'Hashtags'])
    
    local = download_video_locally(video_url)
    if not local: return None
    
    catbox = upload_to_catbox(local)
    if os.path.exists(local): os.remove(local)
    if not catbox: return None

    print(f"📸 Posting to Insta: {account}")
    try:
        url = f"https://graph.facebook.com/v19.0/{page_id}/media"
        res = requests.post(url, params={'access_token': FB_ACCESS_TOKEN, 'media_type': 'REELS', 'video_url': catbox, 'caption': f"{caption}\n\n{tags}"}).json()
        if not res.get('id'): 
            print(f"❌ IG Init Failed: {res}")
            return None
        
        time.sleep(30)
        pub = requests.post(f"https://graph.facebook.com/v19.0/{page_id}/media_publish", params={'creation_id': res['id'], 'access_token': FB_ACCESS_TOKEN}).json()
        return "IG_SUCCESS" if pub.get('id') else None
    except Exception as e:
        print(f"❌ IG Error: {e}")
        return None

def youtube_post(row, row_num):
    account = get_val(row, ['Account_Name', 'Account Name', 'Brand'])
    token = YOUTUBE_PROJECT_MAP.get(account)
    if not token: 
        print(f"❌ No YouTube Token for '{account}'")
        return None
    
    video_url = get_val(row, ['Video_URL', 'Video URL'])
    local = download_video_locally(video_url)
    if not local: return None
    
    try:
        # Use UserCredentials for YouTube
        creds = UserCredentials.from_authorized_user_info(json.loads(token))
        youtube = build('youtube', 'v3', credentials=creds)
        
        caption = get_val(row, ['Caption', 'Title'])
        tags = get_val(row, ['Tags', 'Hashtags'])
        
        body = {
            'snippet': {
                'title': caption[:100], 
                'description': f"{caption}\n{tags}", 
                'tags': tags.split(','), 
                'categoryId': '22'
            }, 
            'status': {
                'privacyStatus': 'public'
            }
        }
        
        media = MediaFileUpload(local, chunksize=-1, resumable=True)
        req = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        
        resp = None
        while resp is None:
            status, resp = req.next_chunk()
            if status:
                print(f"Uploading... {int(status.progress() * 100)}%")
        
        if os.path.exists(local): os.remove(local)
        return f"https://youtu.be/{resp['id']}"
    except Exception as e: 
        print(f"❌ YT Error: {e}")
        if os.path.exists(local): os.remove(local)
        return None

# ==============================================================================
# 4. MAIN ENGINE
# ==============================================================================

def run_master_automation():
    sheet = get_sheet_service()
    if not sheet: return

    try:
        all_values = sheet.get_all_values()
        if not all_values: return
            
        headers = [str(h).strip() for h in all_values[0]]
        print(f"📊 Sheet Headers: {headers}")

        def find_col(possible_names):
            for i, h in enumerate(headers):
                if h.lower().replace(" ","").replace("_","") in [p.lower().replace(" ","").replace("_","") for p in possible_names]:
                    return i + 1
            return None

        status_col = find_col(['Status', 'State'])
        link_col = find_col(['Link', 'Live Link', 'URL'])
        platform_col = find_col(['Platform', 'Social Media'])
        
        if not status_col or not platform_col:
            print(f"❌ CRITICAL: Need 'Status' and 'Platform' columns. Found: {headers}")
            return

        data = []
        for row in all_values[1:]:
            item = {}
            for i, val in enumerate(row):
                if i < len(headers): item[headers[i]] = val
            data.append(item)

    except Exception as e:
        print(f"❌ Read Error: {e}")
        return

    print(f"🚀 Started. Rows: {len(data)}")

    for i, row in enumerate(data):
        row_num = i + 2 
        
        status = get_val(row, ['Status']).upper()
        platform = get_val(row, ['Platform']).lower()

        if status == 'PENDING' and platform:
            print(f"\n--- Processing Row {row_num}: {platform} ---")
            safe_update_cell(sheet, row_num, status_col, 'PROCESSING')
            
            result = None
            if 'instagram' in platform: result = instagram_post(row, row_num)
            elif 'youtube' in platform: result = youtube_post(row, row_num)
            
            if result:
                safe_update_cell(sheet, row_num, status_col, 'DONE')
                if link_col and "http" in str(result): safe_update_cell(sheet, row_num, link_col, str(result))
                print(f"✅ Row {row_num} DONE.")
            else:
                safe_update_cell(sheet, row_num, status_col, 'FAIL')
                print(f"❌ Row {row_num} FAILED.")

if __name__ == "__main__":
    run_master_automation()
