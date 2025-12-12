import gspread
import requests
import json
import random
import os
import time
from io import BytesIO
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
GCP_CREDENTIALS_JSON = os.environ.get("GCP_CREDENTIALS")
YOUTUBE_TOKEN_JSON = os.environ.get("YOUTUBE_TOKEN_JSON")
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")

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

def get_sheet_service():
    try:
        if not GCP_CREDENTIALS_JSON:
            print("❌ FATAL: GCP_CREDENTIALS secret is missing!")
            return None
        creds_dict = json.loads(GCP_CREDENTIALS_JSON)
        creds = ServiceAccountCredentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID).sheet1
    except Exception as e:
        print(f"❌ Sheet Connection Error: {e}")
        return None

def get_youtube_service():
    try:
        if not YOUTUBE_TOKEN_JSON:
            print("❌ YouTube Token Missing in Secrets!")
            return None
        token_dict = json.loads(YOUTUBE_TOKEN_JSON)
        creds = UserCredentials.from_authorized_user_info(token_dict)
        return build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ YouTube Auth Error: {e}")
        return None

# ==============================================================================
# 2. POSTING FUNCTIONS
# ==============================================================================

def instagram_post(row, row_num):
    account_name = str(row.get('Account_Name', '')).strip()
    page_id = INSTAGRAM_IDS.get(account_name)
    
    if not page_id:
        print(f"⚠️ No Instagram ID found for {account_name}")
        return False
        
    video_url = row.get('Video_URL')
    caption = row.get('Caption', '')
    
    print(f"📸 Posting to Instagram: {account_name}...")

    try:
        # 1. Container Create
        url = f"https://graph.facebook.com/v19.0/{page_id}/media"
        params = {
            'access_token': FB_ACCESS_TOKEN,
            'caption': caption,
            'media_type': 'REELS',
            'video_url': video_url 
        }
        response = requests.post(url, data=params).json()
        creation_id = response.get('id')

        if not creation_id:
            print(f"❌ IG Init Failed: {response}")
            return False

        print(f"   - Container Created: {creation_id}. Waiting 60s for processing...")
        
        # 2. Wait & Publish (Increased to 60s)
        time.sleep(60) 
        
        pub_url = f"https://graph.facebook.com/v19.0/{page_id}/media_publish"
        pub_params = {'creation_id': creation_id, 'access_token': FB_ACCESS_TOKEN}
        
        pub_res = requests.post(pub_url, params=pub_params).json()
        
        if pub_res.get('id'):
            print(f"✅ IG Published! ID: {pub_res['id']}")
            return True
        else:
            print(f"❌ IG Publish Failed: {pub_res}")
            return False

    except Exception as e:
        print(f"❌ IG Error: {e}")
        return False

def youtube_post(row, row_num):
    youtube = get_youtube_service()
    if not youtube: return False

    video_url = row.get('Video_URL')
    print(f"🎥 Downloading video for YouTube from {video_url}...")
    
    try:
        video_response = requests.get(video_url)
        video_response.raise_for_status()
    except Exception as e:
        print(f"❌ Download Failed: {e}")
        return False

    base_title = row.get('Base_Title', 'New Video')
    keywords = ["Best", "Top", "Amazing", "Awesome", "New", "Latest"]
    title_parts = base_title.split()
    if title_parts and title_parts[0] in keywords:
        title_parts[0] = random.choice([k for k in keywords if k != title_parts[0]])
    final_title = f"{' '.join(title_parts)} | {row.get('Account_Name')}"[:100]

    description = row.get('Caption', '')
    tags = str(row.get('Tags', 'shorts,viral')).split(',')

    body = {
        'snippet': {
            'title': final_title,
            'description': description,
            'categoryId': '22',
            'tags': tags
        },
        'status': {'privacyStatus': 'public'}
    }

    media = MediaIoBaseUpload(BytesIO(video_response.content), 'video/*', chunksize=-1, resumable=True)
    
    try:
        req = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        resp = None
        while resp is None:
            status, resp = req.next_chunk()
            if status:
                print(f"   - Uploading {int(status.progress() * 100)}%...")
        
        print(f"✅ YouTube Upload Success! ID: {resp.get('id')}")
        return True
    except Exception as e:
        print(f"❌ YouTube Upload Error: {e}")
        return False

# ==============================================================================
# 3. MAIN AUTOMATION ENGINE
# ==============================================================================

def run_master_automation():
    sheet = get_sheet_service()
    if not sheet: return

    try:
        data = sheet.get_all_records()
        if not data:
            print("No data found in sheet.")
            return
            
        headers = list(data[0].keys())
        status_key = next((h for h in headers if h.lower() == 'status'), None)
        
        if not status_key:
            print("❌ Error: 'Status' column not found.")
            return

        sheet_headers = sheet.row_values(1)
        try:
            status_col_idx = next(i for i, v in enumerate(sheet_headers) if v.lower() == 'status') + 1
        except:
            print("Could not find Status column index.")
            return

    except Exception as e:
        print(f"❌ Data Read Error: {e}")
        return

    print(f"🚀 Automation Started. Rows found: {len(data)}")

    for i, row in enumerate(data):
        row_num = i + 2
        current_status = str(row.get(status_key, '')).strip().upper()
        
        # PENDING કે FAIL હોય તો ફરી ટ્રાય કરો
        if current_status == 'PENDING' or current_status == 'FAIL':
            
            platform = ""
            for key in row.keys():
                if key.lower() == 'platform':
                    platform = str(row.get(key, '')).strip().lower()
                    break
            
            if not platform: continue
            if current_status == 'DONE': continue

            print(f"Processing Row {row_num}: {platform}")
            success = False
            
            if 'instagram' in platform or 'facebook' in platform:
                success = instagram_post(row, row_num)
            elif 'youtube' in platform:
                success = youtube_post(row, row_num)
            
            if success:
                sheet.update_cell(row_num, status_col_idx, 'DONE')
                print(f"✅ Row {row_num} DONE")
            else:
                sheet.update_cell(row_num, status_col_idx, 'FAIL')
                print(f"❌ Row {row_num} FAIL")

if __name__ == "__main__":
    run_master_automation()
