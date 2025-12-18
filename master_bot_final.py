import os
import json
import time
import random
import requests
import re
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==============================================================================
# 1. SMART CONFIGURATION (Auto-Detect Secrets)
# ==============================================================================

def get_env_var(keys, default=None):
    """અલગ અલગ નામથી વેરીએબલ શોધે છે (Fallback Logic)"""
    for key in keys:
        val = os.environ.get(key)
        if val:
            return val
    return default

# Google Credentials (Try multiple names)
GCP_CREDENTIALS_JSON = get_env_var([
    "GCP_CREDENTIALS", 
    "GOOGLE_APPLICATION_CREDENTIALS_JSON", 
    "GOOGLE_CREDENTIALS",
    "GOOGLE_SHEETS_CREDENTIALS"
])

# Sheet ID (Try ID or URL keys)
SPREADSHEET_ID = get_env_var([
    "SPREADSHEET_ID", 
    "SHEET_CONTENT_URL", 
    "SHEET_DROPSHIPPING_URL"
])

# Tokens
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")
PINTEREST_SESSION = os.environ.get("PINTEREST_SESSION")
PINTEREST_BOARD_ID = os.environ.get("PINTEREST_BOARD_ID")

# Instagram IDs Mapping
INSTAGRAM_IDS = {
    "Emerald Edge": "17841478369307404",
    "Urban Glint": "17841479492205083",
    "Diamond Dice": "17841478369307404",
    "Grand Orbit": "17841479516066757",
    "Opus": "17841479493645419",
    "Opus Elite": "17841479493645419",
    "Pearl Verse": "17841478822408000",
    "Royal Nexus": "17841479056452004",
    "Luxivibe": "17841479492205083"
}

# YouTube Channel Mapping
YOUTUBE_PROJECT_MAP = {
    "Pearl Verse": os.environ.get("YT_PEARL_VERSE"),
    "Opus Elite": os.environ.get("YT_OPUS_ELITE"),
    "Diamond Dice": os.environ.get("YT_DIAMOND_DICE"),
    "Emerald Edge": os.environ.get("YT_EMERALD_EDGE"),
    "Royal Nexus": os.environ.get("YT_ROYAL_NEXUS"),
    "Grand Orbit": os.environ.get("YT_GRAND_ORBIT"),
    "Urban Glint": os.environ.get("YT_URBAN_GLINT"),
    "Luxivibe": os.environ.get("YT_LUXI_VIBE")
}

# ==============================================================================
# 2. HELPER FUNCTIONS
# ==============================================================================

def get_sheet_service():
    if not GCP_CREDENTIALS_JSON:
        print("❌ FATAL ERROR: GCP_CREDENTIALS secret is MISSING in GitHub Settings!")
        print("💡 Solution: Go to Settings > Secrets > Actions > New Repository Secret")
        print("   Name: GCP_CREDENTIALS")
        print("   Value: Paste your entire JSON key content here.")
        return None

    try:
        creds_dict = json.loads(GCP_CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        client = gspread.authorize(creds)
        
        # Handle Full URL or ID
        sheet_key = SPREADSHEET_ID
        if not sheet_key:
             print("❌ FATAL: SPREADSHEET_ID is missing in Secrets!")
             return None
             
        if "docs.google.com" in sheet_key:
            return client.open_by_url(sheet_key).sheet1
        else:
            return client.open_by_key(sheet_key).sheet1
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

def drive_direct_download(url):
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if m:
        return f"https://drive.google.com/uc?export=download&confirm=t&id={m.group(1)}"
    m2 = re.search(r"id=([a-zA-Z0-9_-]+)", url)
    if m2:
        return f"https://drive.google.com/uc?export=download&confirm=t&id={m2.group(1)}"
    return url

def download_video_locally(url):
    print(f"⬇️ Downloading video...")
    if "drive.google.com" in url:
        url = drive_direct_download(url)
    
    filename = f"temp_{random.randint(1000,9999)}.mp4"
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return filename
    except Exception as e:
        print(f"❌ Local Download Error: {e}")
        return None

def upload_to_catbox(local_path):
    print("🐱 Uploading to Catbox (Insta Helper)...")
    url = "https://catbox.moe/user/api.php"
    try:
        with open(local_path, "rb") as f:
            payload = {"reqtype": "fileupload", "userhash": ""}
            files = {"fileToUpload": ("video.mp4", f, "video/mp4")}
            r = requests.post(url, data=payload, files=files, timeout=300)
            if r.status_code == 200:
                return r.text.strip()
            else:
                print(f"❌ Catbox Error: {r.text}")
                return None
    except Exception as e:
        print(f"❌ Catbox Exception: {e}")
        return None

def safe_update_cell(sheet, row, col, value):
    try:
        sheet.update_cell(row, col, value)
    except Exception as e:
        print(f"⚠️ Sheet Update Failed: {e}")

# ==============================================================================
# 3. PLATFORM POSTING FUNCTIONS
# ==============================================================================

# --- INSTAGRAM ---
def instagram_post(row, row_num):
    account_name = str(row.get('Account_Name', '')).strip()
    page_id = INSTAGRAM_IDS.get(account_name)
    
    if not page_id:
        print(f"⚠️ No Instagram ID for {account_name}")
        return None 
        
    video_url = row.get('Video_URL')
    caption = row.get('Caption', '')
    tags = row.get('Tags', '')
    final_caption = f"{caption}\n\n{tags}"

    local_file = download_video_locally(video_url)
    if not local_file: return None

    catbox_url = upload_to_catbox(local_file)
    if os.path.exists(local_file): os.remove(local_file) 
    
    if not catbox_url: return None

    print(f"📸 Posting to Instagram: {account_name}...")

    try:
        url = f"https://graph.facebook.com/v19.0/{page_id}/media"
        params = {
            'access_token': FB_ACCESS_TOKEN,
            'media_type': 'REELS',
            'video_url': catbox_url,
            'caption': final_caption
        }
        res = requests.post(url, params=params).json()
        creation_id = res.get('id')

        if not creation_id:
            print(f"❌ IG Init Failed: {res}")
            return None

        print(f"⏳ Processing Instagram (Waiting 30s)...")
        time.sleep(30)
        
        pub_url = f"https://graph.facebook.com/v19.0/{page_id}/media_publish"
        pub_params = {'creation_id': creation_id, 'access_token': FB_ACCESS_TOKEN}
        pub_res = requests.post(pub_url, params=pub_params).json()
        
        if pub_res.get('id'):
            print(f"✅ IG Published! ID: {pub_res['id']}")
            return "IG_SUCCESS"
        else:
            print(f"❌ IG Publish Error: {pub_res}")
            return None

    except Exception as e:
        print(f"❌ IG Error: {e}")
        return None

# --- YOUTUBE ---
def youtube_post(row, row_num):
    account_name = str(row.get('Account_Name', '')).strip()
    token_json = YOUTUBE_PROJECT_MAP.get(account_name)
    
    if not token_json:
        print(f"❌ No YouTube Token found for '{account_name}'")
        return None

    video_url = row.get('Video_URL')
    local_file = download_video_locally(video_url)
    if not local_file: return None

    title = row.get('Caption', 'New Video')[:100]
    description = f"{row.get('Caption', '')}\n\n{row.get('Tags', '')}"
    tags = str(row.get('Tags', 'shorts')).split(',')

    try:
        creds = Credentials.from_authorized_user_info(json.loads(token_json))
        youtube = build('youtube', 'v3', credentials=creds)

        body = {
            'snippet': {'title': title, 'description': description, 'categoryId': '22', 'tags': tags},
            'status': {'privacyStatus': 'public'}
        }

        print(f"🚀 Uploading to YouTube ({account_name})...")
        media = MediaFileUpload(local_file, chunksize=-1, resumable=True)
        req = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        
        resp = None
        while resp is None:
            status, resp = req.next_chunk()
            if status: print(f"Uploading... {int(status.progress() * 100)}%")
        
        print(f"✅ YouTube Success! ID: {resp['id']}")
        if os.path.exists(local_file): os.remove(local_file)
        return f"https://youtu.be/{resp['id']}" 
    except Exception as e:
        print(f"❌ YouTube Upload Error: {e}")
        if os.path.exists(local_file): os.remove(local_file)
        return None

# --- PINTEREST ---
def pinterest_post(row, row_num):
    if not PINTEREST_SESSION or not PINTEREST_BOARD_ID:
        print("⚠️ Pinterest Secrets Missing")
        return None
    
    link_to_pin = str(row.get('Link', '')).strip()
    if not link_to_pin:
        print("⚠️ Pinterest needs a Link")
        return None

    print(f"📌 Pinning to Pinterest...")
    caption = row.get('Caption', 'Check this out!')
    image_url = "https://i.pinimg.com/736x/16/09/27/160927643666b69d9c2409748684497e.jpg" 

    session = requests.Session()
    session.cookies.set("_pinterest_sess", PINTEREST_SESSION)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "X-CSRFToken": "1234" 
    }

    try:
        session.get("https://www.pinterest.com/", headers=headers)
        headers["X-CSRFToken"] = session.cookies.get("csrftoken")

        url = "https://www.pinterest.com/resource/PinResource/create/"
        data = {
            "options": {
                "board_id": PINTEREST_BOARD_ID,
                "description": caption,
                "link": link_to_pin,
                "image_url": image_url,
                "method": "scraped",
            },
            "context": {}
        }
        resp = session.post(url, headers=headers, data={"source_url": "/", "data": json.dumps(data)})
        if resp.status_code == 200:
            print(f"✅ Pinterest Success!")
            return "PIN_SUCCESS"
        else:
            print(f"❌ Pinterest Failed: {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Pinterest Error: {e}")
        return None

# ==============================================================================
# 4. MAIN AUTOMATION ENGINE
# ==============================================================================

def run_master_automation():
    sheet = get_sheet_service()
    if not sheet: return

    try:
        data = sheet.get_all_records()
        if not data: 
            print("💤 Sheet is empty.")
            return
            
        headers = sheet.row_values(1)
        try:
            status_col_idx = headers.index('Status') + 1
            link_col_idx = headers.index('Link') + 1 
        except ValueError:
            print("❌ Error: 'Status' or 'Link' column missing in headers.")
            return

    except Exception as e:
        print(f"❌ Data Read Error: {e}")
        return

    print(f"🚀 Automation Started. Rows found: {len(data)}")

    for i, row in enumerate(data):
        row_num = i + 2
        
        current_status = str(row.get('Status', '')).strip().upper()
        platform = str(row.get('Platform', '')).strip().lower()

        if current_status == 'PENDING' and platform:
            print(f"\n--- Processing Row {row_num}: {platform} ---")
            safe_update_cell(sheet, row_num, status_col_idx, 'PROCESSING')
            
            result_link = None
            
            if 'instagram' in platform:
                result_link = instagram_post(row, row_num)
            elif 'youtube' in platform:
                result_link = youtube_post(row, row_num)
            elif 'pinterest' in platform:
                result_link = pinterest_post(row, row_num)
            
            if result_link:
                safe_update_cell(sheet, row_num, status_col_idx, 'DONE')
                if "http" in str(result_link):
                    safe_update_cell(sheet, row_num, link_col_idx, result_link)
                print(f"✅ Row {row_num} DONE.")
            else:
                safe_update_cell(sheet, row_num, status_col_idx, 'FAIL')
                print(f"❌ Row {row_num} FAILED.")

if __name__ == "__main__":
    run_master_automation()
