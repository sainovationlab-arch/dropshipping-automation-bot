import gspread
import requests
import json
import random
from io import BytesIO
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import time
import os

# ==============================================================================
# 1. Configuration
# ==============================================================================

SERVICE_ACCOUNT_FILE = 'service_account_key.json' 
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID") 

# Platform Configuration
PLATFORM_CONFIG = {
    "instagram_tokens": {
        # અહી તમારા સાચા Page ID અને Token નાખવાનું ભૂલતા નહીં!
        "Luxivibe": {"page_id": "YOUR_PAGE_ID", "access_token": "YOUR_ACCESS_TOKEN"},
        "Urban Glint": {"page_id": "YOUR_PAGE_ID", "access_token": "YOUR_ACCESS_TOKEN"},
        # ... બાકીના બધા એકાઉન્ટ્સ
    },
    "youtube_channels": {
        # હવે બધી ચેનલ માટે એક જ ફાઈલ વપરાશે
        "Luxivibe": "service_account_key.json",
        "Urban Glint": "service_account_key.json",
        "Royal Nexus": "service_account_key.json",
        "Grand Orbit": "service_account_key.json",
        "Opus Elite": "service_account_key.json",
        "Pearl Verse": "service_account_key.json",
        "Diamond Dice": "service_account_key.json",
        "Emerald Edge": "service_account_key.json"
    }
}

# ==============================================================================
# 2. Smart AI Functions
# ==============================================================================

def generate_varied_title(base_title, account_name):
    keywords = ["Best", "Top", "Amazing", "Awesome", "New", "Latest"]
    title_parts = base_title.split()
    if title_parts and title_parts[0] in keywords:
        title_parts[0] = random.choice([k for k in keywords if k != title_parts[0]])
    return f"{' '.join(title_parts)} | {account_name}"[:100]

# ==============================================================================
# 3. Posting Functions (REAL MODE ACTIVATED)
# ==============================================================================

def instagram_post(post_data, config, row_num):
    account_name = post_data['Account_Name']
    
    # 1. Get Tokens
    tokens = config["instagram_tokens"].get(account_name)
    if not tokens:
        print(f"❌ No Instagram tokens found for {account_name}")
        # જો ટોકન ન હોય તો પણ આપણે કોડ ચાલવા દઈશું (YouTube માટે)
        return False
        
    page_id = tokens["page_id"]
    access_token = tokens["access_token"]
    video_url = post_data['Video_URL']
    caption = post_data['Caption']

    # 2. Upload Video
    try:
        url = f"https://graph.facebook.com/v18.0/{page_id}/media"
        payload = {
            'media_type': 'REELS',
            'video_url': video_url,
            'caption': caption,
            'access_token': access_token
        }
        response = requests.post(url, data=payload)
        result = response.json()
        
        if 'id' not in result:
            print(f"❌ Init failed: {result}")
            return False
            
        creation_id = result['id']
        print(f"Media Container Created: {creation_id}")
        
        print("Waiting for video processing...")
        time.sleep(20) # થોડી વધુ રાહ જોઈએ
        
        publish_url = f"https://graph.facebook.com/v18.0/{page_id}/media_publish"
        publish_payload = {
            'creation_id': creation_id,
            'access_token': access_token
        }
        publish_response = requests.post(publish_url, data=publish_payload)
        publish_result = publish_response.json()
        
        if 'id' in publish_result:
            print(f"✅ Instagram REEL Published Successfully! ID: {publish_result['id']}")
            return True
        else:
            print(f"❌ Publish failed: {publish_result}")
            return False
            
    except Exception as e:
        print(f"❌ Instagram Error: {e}")
        return False

def youtube_post(post_data, config, row_num):
    account_name = post_data['Account_Name']
    try:
        # ફિક્સ: હવે માસ્ટર કી જ વપરાશે
        creds_file = 'service_account_key.json'
        
        creds = Credentials.from_service_account_file(
            creds_file,
            scopes=['https://www.googleapis.com/auth/youtube.force-ssl']
        )
        youtube = build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ YouTube Auth failed: {e}")
        return False

    video_url = post_data['Video_URL']
    print(f"Downloading video from {video_url}")
    try:
        video_response = requests.get(video_url)
        video_response.raise_for_status() 
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False
        
    title = generate_varied_title(post_data['Base_Title'], account_name)
    description = post_data['Caption']
    
    body=dict(
        snippet=dict(title=title, description=description, categoryId="22", tags=['shorts', account_name]),
        status=dict(privacyStatus="public")
    )
    media = MediaIoBaseUpload(BytesIO(video_response.content), 'video/*', chunksize=-1, resumable=False)
    
    try:
        insert_request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        response = insert_request.execute()
        print(f"✅ YouTube Upload Success! ID: {response.get('id')}")
        return True
    except Exception as e:
        print(f"❌ YouTube Upload failed: {e}")
        return False

# ==============================================================================
# 4. Main Automation Logic
# ==============================================================================

def run_master_automation():
    if not SPREADSHEET_ID:
        print("FATAL ERROR: SPREADSHEET_ID missing.")
        return
        
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        
        headers = sheet.row_values(1)
        try:
            status_col = headers.index('Status') + 1
        except ValueError:
            print("ERROR: 'Status' column not found in sheet.")
            return
            
        data = sheet.get_all_records()
    except Exception as e:
        print(f"FATAL ERROR: Sheet Connection Failed: {e}")
        return

    print(f"Master Automation Started. Found {len(data)} rows.")
    
    for i, row in enumerate(data):
        row_num = i + 2 
        
        current_status = row.get('Status')
        # PENDING અથવા FAIL હોય તો જ ફરી કરો
        if current_status == 'PENDING' or current_status == 'FAIL':
            
            platform = row.get('Platform', '').strip()
            if current_status == 'DONE': continue

            success = False
            if platform.lower() == 'instagram':
                success = instagram_post(row, PLATFORM_CONFIG, row_num)
            elif platform.lower() == 'youtube':
                success = youtube_post(row, PLATFORM_CONFIG, row_num)
            
            if success:
                sheet.update_cell(row_num, status_col, 'DONE')
                print(f"STATUS UPDATED: Row {row_num} marked as DONE.")
            else:
                sheet.update_cell(row_num, status_col, 'FAIL')
                print(f"STATUS UPDATED: Row {row_num} marked as FAIL.")

if __name__ == "__main__":
    run_master_automation()
