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
# 1. CONFIGURATION & SECRETS SETUP
# ==============================================================================

# General Secrets - SMART AUTHENTICATION (Banne naam try karshe)
# Pehla 'GCP_CREDENTIALS' shodhshe, na male to 'GOOGLE_SHEETS_CREDENTIALS' vaparshe
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
GCP_CREDENTIALS_JSON = os.environ.get("GCP_CREDENTIALS") or os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")

# Instagram IDs (Account Name -> ID)
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

# YouTube 8-Channel Mapping
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
    """ Authenticates with Google Sheets using ANY available secret """
    print("🔄 Connecting to Google Sheet...")
    try:
        # Check if we found ANY key
        if not GCP_CREDENTIALS_JSON:
            print("❌ FATAL: Koi pan Secret Key (GCP_CREDENTIALS ke GOOGLE_SHEETS_CREDENTIALS) mali nathi!")
            return None
        
        creds_dict = json.loads(GCP_CREDENTIALS_JSON)
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        if not SPREADSHEET_ID:
             print("❌ FATAL: 'SPREADSHEET_ID' missing che!")
             return None

        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        print("✅ Connected to Sheet Successfully!")
        return sheet
        
    except Exception as e:
        print(f"❌ Sheet Connection Error: {e}")
        return None

def get_youtube_service(account_name):
    try:
        clean_name = str(account_name).strip()
        token_json = YOUTUBE_PROJECT_MAP.get(clean_name)
        if not token_json:
            print(f"❌ No YouTube Token found for '{clean_name}'.")
            return None
        token_dict = json.loads(token_json)
        creds = UserCredentials.from_authorized_user_info(token_dict)
        return build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ YouTube Auth Error: {e}")
        return None

def safe_update_cell(sheet, row, col, value):
    try: sheet.update_cell(row, col, value)
    except Exception as e: print(f"⚠️ Sheet Update Failed: {e}")

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
    except Exception as e:
        print(f"❌ Download Error: {e}")
        if os.path.exists(output_file): os.remove(output_file)
        raise e

# ==============================================================================
# 3. PLATFORM FUNCTIONS
# ==============================================================================

def instagram_post(row, row_num):
    # (Same Instagram Logic as before)
    account_name = str(row.get('Account_Name', '')).strip()
    page_id = INSTAGRAM_IDS.get(account_name)
    if not page_id: return None 
    
    local_file = download_video(row.get('Video_URL'))
    if not local_file: return None

    try:
        url = f"https://graph.facebook.com/v19.0/{page_id}/media"
        params = {'access_token': FB_ACCESS_TOKEN, 'upload_type': 'resumable', 'media_type': 'REELS', 'caption': row.get('Caption', '')}
        init_res = requests.post(url, params=params).json()
        
        video_id = init_res.get('id')
        upload_uri = init_res.get('uri')
        if not video_id: return None

        with open(local_file, 'rb') as f:
            requests.post(upload_uri, data=f, headers={'Authorization': f'OAuth {FB_ACCESS_TOKEN}', 'offset': '0', 'file_size': str(os.path.getsize(local_file))})
        
        time.sleep(60)
        requests.post(f"https://graph.facebook.com/v19.0/{page_id}/media_publish", params={'creation_id': video_id, 'access_token': FB_ACCESS_TOKEN})
        
        if os.path.exists(local_file): os.remove(local_file)
        return "IG_SUCCESS"
    except:
        if os.path.exists(local_file): os.remove(local_file)
        return None

def youtube_post(row, row_num):
    # (Same YouTube Logic as before)
    account_name = str(row.get('Account_Name', '')).strip()
    youtube = get_youtube_service(account_name)
    if not youtube: return None

    local_file = download_video(row.get('Video_URL'))
    if not local_file: return None

    body = {
        'snippet': {'title': f"{row.get('Base_Title', 'New Video')}"[:100], 'description': row.get('Caption', ''), 'categoryId': '22', 'tags': str(row.get('Tags', '')).split(',')},
        'status': {'privacyStatus': 'public'}
    }
    media = MediaFileUpload(local_file, chunksize=-1, resumable=True)
    try:
        req = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        resp = None
        while resp is None: status, resp = req.next_chunk()
        if os.path.exists(local_file): os.remove(local_file)
        return f"https://youtu.be/{resp['id']}"
    except:
        if os.path.exists(local_file): os.remove(local_file)
        return None

# ==============================================================================
# 4. MAIN ENGINE
# ==============================================================================

def run_master_automation():
    print("--- 🤖 MASTER AUTOMATION BOT STARTED (SMART MODE) 🤖 ---")
    sheet = get_sheet_service()
    if not sheet: return

    try:
        data = sheet.get_all_records()
        headers = list(data[0].keys())
        sheet_headers = sheet.row_values(1)
        
        def get_col_idx(name):
            try: return next(i for i, v in enumerate(sheet_headers) if v.lower() == name.lower()) + 1
            except: return None

        status_col_idx = get_col_idx('Status')
        link_col_idx = get_col_idx('Link')
        
    except Exception as e:
        print(f"❌ Data Error: {e}")
        return

    for i, row in enumerate(data):
        row_num = i + 2
        status_key = next((h for h in headers if h.lower() == 'status'), None)
        platform_key = next((h for h in headers if h.lower() == 'platform'), None)
        
        current_status = str(row.get(status_key, '')).strip().upper()
        platform = str(row.get(platform_key, '')).strip().lower()

        if current_status in ['PENDING', 'FAIL'] and platform:
            print(f"⚡ Processing Row {row_num}: {platform}")
            result = None
            
            if 'instagram' in platform or 'facebook' in platform:
                result = instagram_post(row, row_num)
            elif 'youtube' in platform:
                result = youtube_post(row, row_num)
            
            if result:
                safe_update_cell(sheet, row_num, status_col_idx, 'DONE')
                if link_col_idx and "http" in str(result): safe_update_cell(sheet, row_num, link_col_idx, result)
                print(f"✅ Row {row_num} DONE")
            else:
                safe_update_cell(sheet, row_num, status_col_idx, 'FAIL')
                print(f"❌ Row {row_num} FAIL")

if __name__ == "__main__":
    run_master_automation()
