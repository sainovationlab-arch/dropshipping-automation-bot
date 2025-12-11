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
        # તમારા રિયલ ટોકન્સ અહીં હોવા જોઈએ
        "Luxivibe": {"page_id": "YOUR_PAGE_ID", "access_token": "YOUR_ACCESS_TOKEN"},
    },
    "youtube_channels": {
        "Luxivibe": "luxivibe_yt.json",
        "Urban Glint": "urbanglint_yt.json",
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
# 3. Posting Functions
# ==============================================================================

def instagram_post(post_data, config, row_num):
    # અત્યારે આ કોડ સિમ્યુલેશન મોડમાં છે જેથી આપણે પહેલા શીટમાં DONE લખેલું જોઈ શકીએ.
    # એકવાર DONE લખાઈ જાય, પછી આપણે અહીં તમારો રિયલ કોડ મૂકીશું.
    print(f"✅ Instagram posting successful for {post_data['Account_Name']}")
    return True 

def youtube_post(post_data, config, row_num):
    account_name = post_data['Account_Name']
    try:
        creds_file = PLATFORM_CONFIG["youtube_channels"].get(account_name)
        if not creds_file:
            print(f"❌ No credential file found for {account_name}")
            return False
            
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
# 4. Main Automation Logic (Bug Fixed)
# ==============================================================================

def run_master_automation():
    if not SPREADSHEET_ID:
        print("FATAL ERROR: SPREADSHEET_ID missing.")
        return
        
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        
        # --- FIX: Headers અલગથી મેળવો ---
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
        
        if row.get('Status') == 'PENDING':
            platform = row.get('Platform', '').strip()
            account_name = row.get('Account_Name', '').strip()
            
            success = False
            if platform.lower() == 'instagram':
                success = instagram_post(row, PLATFORM_CONFIG, row_num)
            elif platform.lower() == 'youtube':
                success = youtube_post(row, PLATFORM_CONFIG, row_num)
            
            if success:
                # --- FIX: સાચા કોલમ નંબરનો ઉપયોગ ---
                sheet.update_cell(row_num, status_col, 'DONE')
                print(f"STATUS UPDATED: Row {row_num} marked as DONE.")
            else:
                sheet.update_cell(row_num, status_col, 'FAIL')
                print(f"STATUS UPDATED: Row {row_num} marked as FAIL.")

if __name__ == "__main__":
    run_master_automation()
