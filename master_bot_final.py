import os
import json
import gspread
import requests
import random
import time
import gdown
from tenacity import retry, stop_after_attempt, wait_fixed
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==============================================================================
# 🤖 WORLD'S BEST AUTOMATION BOT (VERSION 5.0)
# ==============================================================================

def get_env_variable(var_name):
    """ Smartly fetches secrets and cleans them """
    val = os.environ.get(var_name)
    if val:
        return val.strip() # Remove spaces/newlines
    return None

# --- CONFIGURATION ---
SPREADSHEET_ID = get_env_variable("SPREADSHEET_ID")
FB_ACCESS_TOKEN = get_env_variable("FB_ACCESS_TOKEN")

# --- INSTAGRAM IDS ---
INSTAGRAM_IDS = {
    "Emerald Edge": "17841478369307404", "Urban Glint": "17841479492205083",
    "Diamond Dice": "17841478369307404", "Grand Orbit": "17841479516066757",
    "Opus": "17841479493645419", "Opus Elite": "17841479493645419",
    "Pearl Verse": "17841478822408000", "Royal Nexus": "17841479056452004",
    "Luxivibe": "17841479492205083"
}

# --- YOUTUBE MAPPING ---
YOUTUBE_PROJECT_MAP = {
    "Pearl Verse": get_env_variable("YT_PEARL_VERSE"),
    "Opus Elite": get_env_variable("YT_OPUS_ELITE"),
    "Diamond Dice": get_env_variable("YT_DIAMOND_DICE"),
    "Emerald Edge": get_env_variable("YT_EMERALD_EDGE"),
    "Royal Nexus": get_env_variable("YT_ROYAL_NEXUS"),
    "Grand Orbit": get_env_variable("YT_GRAND_ORBIT"),
    "Urban Glint": get_env_variable("YT_URBAN_GLINT"),
    "Luxivibe": get_env_variable("YT_LUXI_VIBE")
}

# ==============================================================================
# 🛠️ DIAGNOSTIC SYSTEM (આ ભૂલ શોધશે)
# ==============================================================================
def check_system_health():
    print("\n🔍 SYSTEM DIAGNOSTICS RUNNING...")
    
    # Check 1: Key Existence
    key = get_env_variable("GCP_CREDENTIALS")
    if key:
        print(f"✅ GCP_CREDENTIALS Found! (Length: {len(key)})")
    else:
        print("❌ CRITICAL: GCP_CREDENTIALS Secret is MISSING or EMPTY.")
        print("💡 TIP: GitHub Secrets ma 'GCP_CREDENTIALS' naam thi key add karo.")

    # Check 2: Sheet ID
    if SPREADSHEET_ID:
        print(f"✅ Spreadsheet ID Found: {SPREADSHEET_ID}")
    else:
        print("⚠️ WARNING: Spreadsheet ID missing. Bot cannot read tasks.")

# ==============================================================================
# 🔌 CONNECTION FUNCTIONS
# ==============================================================================

def get_sheet_service():
    print("🔄 Connecting to Google Cloud...")
    creds_json = get_env_variable("GCP_CREDENTIALS")
    
    if not creds_json:
        return None

    try:
        creds_dict = json.loads(creds_json)
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        if SPREADSHEET_ID:
            return client.open_by_key(SPREADSHEET_ID).sheet1
        return None
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

def get_youtube_service(account_name):
    try:
        token_json = YOUTUBE_PROJECT_MAP.get(account_name)
        if not token_json: return None
        creds = UserCredentials.from_authorized_user_info(json.loads(token_json))
        return build('youtube', 'v3', credentials=creds)
    except: return None

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def download_video(url):
    print(f"⬇️ Downloading: {url}")
    output_file = f"video_{random.randint(1000,9999)}.mp4"
    try:
        if "drive.google.com" in url:
            gdown.download(url, output_file, quiet=False, fuzzy=True)
        else:
            with open(output_file, 'wb') as f:
                f.write(requests.get(url, stream=True).content)
        if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
            return output_file
        return None
    except: return None

# ==============================================================================
# 🚀 POSTING ENGINES
# ==============================================================================

def instagram_post(row):
    acc = row.get('Account_Name', '').strip()
    page_id = INSTAGRAM_IDS.get(acc)
    if not page_id: return None
    
    video = download_video(row.get('Video_URL'))
    if not video: return None
    
    try:
        # Init
        url = f"https://graph.facebook.com/v19.0/{page_id}/media"
        res = requests.post(url, params={'access_token': FB_ACCESS_TOKEN, 'media_type': 'REELS', 'caption': row.get('Caption', '')}).json()
        vid_id = res.get('id')
        
        # Upload
        with open(video, 'rb') as f:
            requests.post(res['uri'], data=f, headers={'Authorization': f'OAuth {FB_ACCESS_TOKEN}', 'offset': '0', 'file_size': str(os.path.getsize(video))})
            
        time.sleep(60) # Wait for processing
        
        # Publish
        pub = requests.post(f"https://graph.facebook.com/v19.0/{page_id}/media_publish", params={'creation_id': vid_id, 'access_token': FB_ACCESS_TOKEN}).json()
        
        if os.path.exists(video): os.remove(video)
        if pub.get('id'): return "IG_SUCCESS"
    except Exception as e:
        print(f"❌ IG Error: {e}")
        if os.path.exists(video): os.remove(video)
    return None

def youtube_post(row):
    acc = row.get('Account_Name', '').strip()
    yt = get_youtube_service(acc)
    if not yt: return None
    
    video = download_video(row.get('Video_URL'))
    if not video: return None
    
    try:
        body = {
            'snippet': {'title': row.get('Base_Title', 'New Video')[:100], 'description': row.get('Caption', ''), 'categoryId': '22', 'tags': str(row.get('Tags', '')).split(',')},
            'status': {'privacyStatus': 'public'}
        }
        media = MediaFileUpload(video, chunksize=-1, resumable=True)
        req = yt.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        
        resp = None
        while resp is None: stat, resp = req.next_chunk()
        
        if os.path.exists(video): os.remove(video)
        return f"https://youtu.be/{resp['id']}"
    except Exception as e:
        print(f"❌ YT Error: {e}")
        if os.path.exists(video): os.remove(video)
    return None

# ==============================================================================
# 🎮 MAIN CONTROLLER
# ==============================================================================

def run_automation():
    check_system_health() # <--- આ તમારી ભૂલ પકડશે
    
    sheet = get_sheet_service()
    if not sheet:
        print("🛑 SYSTEM HALTED: Connection Failed.")
        return

    try:
        data = sheet.get_all_records()
        headers = [h.lower() for h in sheet.row_values(1)]
        status_col = headers.index('status') + 1
        link_col = headers.index('link') + 1 if 'link' in headers else None
    except:
        print("❌ Sheet Read Error or Empty Sheet")
        return

    print(f"⚡ Processing {len(data)} Tasks...")
    
    for i, row in enumerate(data):
        row_num = i + 2
        status = str(row.get('Status', '')).strip().upper()
        platform = str(row.get('Platform', '')).strip().lower()

        if status in ['PENDING', 'FAIL'] and platform:
            print(f"▶️ Row {row_num}: {platform}...")
            res = None
            
            if 'instagram' in platform or 'facebook' in platform:
                res = instagram_post(row)
            elif 'youtube' in platform:
                res = youtube_post(row)
            
            if res:
                sheet.update_cell(row_num, status_col, 'DONE')
                if link_col: sheet.update_cell(row_num, link_col, res)
                print(f"✅ Row {row_num} SUCCESS")
            else:
                sheet.update_cell(row_num, status_col, 'FAIL')
                print(f"❌ Row {row_num} FAILED")

if __name__ == "__main__":
    run_automation()
