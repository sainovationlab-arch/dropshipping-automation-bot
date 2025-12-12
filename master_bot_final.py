import gspread
import requests
import json
import random
import os
import time
import gdown
from tenacity import retry, stop_after_attempt, wait_fixed
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials

# ==============================================================================
# 1. CONFIGURATION & SETUP
# ==============================================================================

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
GCP_CREDENTIALS_JSON = os.environ.get("GCP_CREDENTIALS")
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")
PINTEREST_SESSION = os.environ.get("PINTEREST_SESSION")
PINTEREST_BOARD_ID = os.environ.get("PINTEREST_BOARD_ID")

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
    try:
        if not GCP_CREDENTIALS_JSON: return None
        creds_dict = json.loads(GCP_CREDENTIALS_JSON)
        creds = ServiceAccountCredentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID).sheet1
    except Exception as e:
        print(f"❌ Sheet Error: {e}")
        return None

def get_youtube_service(account_name):
    try:
        clean_name = str(account_name).strip()
        token_json = YOUTUBE_PROJECT_MAP.get(clean_name)
        if not token_json: return None
        token_dict = json.loads(token_json)
        creds = UserCredentials.from_authorized_user_info(token_dict)
        return build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ YouTube Auth Error: {e}")
        return None

def safe_update_cell(sheet, row, col, value):
    try: sheet.update_cell(row, col, value)
    except: pass

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def download_video(url):
    print(f"⬇️ Downloading: {url}")
    output_file = f"video_{random.randint(1000, 9999)}.mp4"
    try:
        if "drive.google.com" in url:
            gdown.download(url, output_file, quiet=False, fuzzy=True)
        else:
            response = requests.get(url, stream=True)
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
        if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
            return output_file
        return None
    except:
        if os.path.exists(output_file): os.remove(output_file)
        raise

# ==============================================================================
# 3. PINTEREST FUNCTION (NEW) 📌
# ==============================================================================

def pinterest_post(row, row_num):
    # જો પિન્ટરેસ્ટ સેશન અથવા બોર્ડ આઈડી ન હોય તો આગળ વધો
    if not PINTEREST_SESSION or not PINTEREST_BOARD_ID:
        print("⚠️ Pinterest details missing (Skipping)")
        return None

    # આપણે વિડિયો સીધો અપલોડ નથી કરતા (તે અઘરું છે)
    # આપણે YouTube લિંકને પિન કરીએ છીએ (સ્માર્ટ રીત)
    link_col_val = str(row.get('Link', '')).strip()
    
    # જો YouTube લિંક ન હોય, તો પિન ન બની શકે
    if "youtu" not in link_col_val:
        print("⚠️ No YouTube link found to Pin on Pinterest.")
        return None

    print(f"📌 Pinning to Pinterest Board: {PINTEREST_BOARD_ID}...")
    
    caption = row.get('Caption', 'Check this out!')
    video_link = link_col_val
    image_url = row.get('Thumbnail_URL', '') # ઓપ્શનલ: જો શીટમાં થમ્બનેલ હોય તો

    # જો થમ્બનેલ ન હોય તો ડિફોલ્ટ પ્લેસહોલ્ડર (અથવા વિડિયો લિંક જ વાપરો)
    if not image_url: image_url = "https://i.pinimg.com/736x/16/09/27/160927643666b69d9c2409748684497e.jpg"

    session = requests.Session()
    session.cookies.set("_pinterest_sess", PINTEREST_SESSION)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": session.cookies.get("csrftoken", "1234") # Dummy fallback
    }

    try:
        # First connect to get valid CSRF
        session.get("https://www.pinterest.com/", headers=headers)
        headers["X-CSRFToken"] = session.cookies.get("csrftoken")

        # Create Pin API (Internal)
        url = "https://www.pinterest.com/resource/PinResource/create/"
        data = {
            "options": {
                "board_id": PINTEREST_BOARD_ID,
                "description": caption,
                "link": video_link,
                "image_url": image_url,
                "method": "scraped",
                "section": None
            },
            "context": {}
        }
        
        resp = session.post(url, headers=headers, data={"source_url": "/", "data": json.dumps(data)})
        resp_json = resp.json()

        if "resource_response" in resp_json and "data" in resp_json["resource_response"]:
            pin_id = resp_json["resource_response"]["data"]["id"]
            print(f"✅ Pinterest Success! Pin ID: {pin_id}")
            return f"https://pinterest.com/pin/{pin_id}"
        else:
            print(f"❌ Pinterest Failed: {resp_json}")
            return None

    except Exception as e:
        print(f"❌ Pinterest Error: {e}")
        return None

# ==============================================================================
# 4. MAIN AUTOMATION
# ==============================================================================

def instagram_post(row, row_num):
    # (જૂનો ઇન્સ્ટાગ્રામ કોડ અહીં જેમ છે તેમ રાખો - હું ટૂંકાવી રહ્યો છું સ્પેસ માટે)
    # ... (તમારો ઓરિજિનલ ઇન્સ્ટાગ્રામ કોડ અહીં આવશે) ...
    return "IG_DONE" # Placeholder

def youtube_post(row, row_num):
    # (જૂનો યુટ્યુબ કોડ અહીં જેમ છે તેમ રાખો)
    # ... (તમારો ઓરિજિનલ યુટ્યુબ કોડ અહીં આવશે) ...
    return "YT_DONE" # Placeholder

def run_master_automation():
    sheet = get_sheet_service()
    if not sheet: return
    data = sheet.get_all_records()
    if not data: return
    headers = list(data[0].keys())
    sheet_headers = sheet.row_values(1)
    
    def get_col_idx(name):
        try: return next(i for i, v in enumerate(sheet_headers) if v.lower() == name.lower()) + 1
        except: return None

    status_col_idx = get_col_idx('Status')
    link_col_idx = get_col_idx('Link')

    print(f"🚀 Automation Started. Rows: {len(data)}")

    for i, row in enumerate(data):
        row_num = i + 2
        status = str(row.get('Status', '')).strip().upper()
        platform = str(row.get('Platform', '')).strip().lower()

        if status in ['PENDING', 'FAIL'] and platform:
            print(f"Processing Row {row_num}: {platform}")
            result = None
            
            if 'instagram' in platform or 'facebook' in platform:
                # Instagram કોડ (તમારો જૂનો કોડ વાપરવો)
                pass 
            elif 'youtube' in platform:
                # YouTube કોડ (તમારો જૂનો કોડ વાપરવો)
                pass
            
            # 👇 PINTEREST MAGIC: જો પ્લેટફોર્મ 'pinterest' હોય
            elif 'pinterest' in platform:
                result = pinterest_post(row, row_num)

            if result:
                safe_update_cell(sheet, row_num, status_col_idx, 'DONE')
                if link_col_idx: safe_update_cell(sheet, row_num, link_col_idx, result)
