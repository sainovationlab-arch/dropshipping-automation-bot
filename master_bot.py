import gspread
import requests
import json
import random
import os
import base64
from io import BytesIO
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import time

# ==============================================================================
# 1. ROBUST CONFIGURATION (No Files Needed - Direct Memory Access)
# ==============================================================================

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
GCP_CREDENTIALS_JSON = os.environ.get("GCP_CREDENTIALS")

def get_credentials():
    """Securely fetch credentials from memory, bypassing file creation errors."""
    try:
        if not GCP_CREDENTIALS_JSON:
            raise ValueError("FATAL: GCP_CREDENTIALS secret is missing in GitHub!")
        
        creds_dict = json.loads(GCP_CREDENTIALS_JSON)
        return Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/youtube.force-ssl']
        )
    except json.JSONDecodeError:
        print("❌ FATAL ERROR: GitHub Secret is corrupted. Please re-paste the JSON code in Secrets.")
        return None
    except Exception as e:
        print(f"❌ Credential Error: {e}")
        return None

# 👇 તમારી સાચી ID અને Token અહીં નાખો (આ ભૂલતા નહીં!)
PLATFORM_CONFIG = {
    "instagram_tokens": {
        "Luxivibe": {"page_id": "YOUR_PAGE_ID", "access_token": "YOUR_ACCESS_TOKEN"},
        "Urban Glint": {"page_id": "YOUR_PAGE_ID", "access_token": "YOUR_ACCESS_TOKEN"},
        "Royal Nexus": {"page_id": "YOUR_PAGE_ID", "access_token": "YOUR_ACCESS_TOKEN"},
        # ... બાકીના એકાઉન્ટ્સ અહીં ઉમેરો
    }
}

# ==============================================================================
# 2. Logic Functions
# ==============================================================================

def generate_varied_title(base_title, account_name):
    keywords = ["Best", "Top", "Amazing", "Awesome", "New", "Latest"]
    title_parts = base_title.split()
    if title_parts and title_parts[0] in keywords:
        title_parts[0] = random.choice([k for k in keywords if k != title_parts[0]])
    return f"{' '.join(title_parts)} | {account_name}"[:100]

def instagram_post(post_data, config, row_num):
    account_name = post_data.get('Account_Name')
    tokens = config["instagram_tokens"].get(account_name)
    
    if not tokens:
        print(f"⚠️ Skipping Instagram for {account_name} (No tokens found in Code).")
        return False
        
    print(f"✅ Instagram Posting Simulation Successful for {account_name}")
    # (નોંધ: રિયલ પોસ્ટિંગ માટે અહીં તમારો જૂનો Graph API કોડ મૂકી શકાય, અત્યારે ટેસ્ટ મોડ છે)
    return True

def youtube_post(post_data, creds, row_num):
    account_name = post_data.get('Account_Name')
    try:
        # સીધા મેમરીમાંથી ક્રેડેન્શિયલ વાપરે છે (No JSON file needed)
        youtube = build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ YouTube Auth Failed: {e}")
        return False

    video_url = post_data.get('Video_URL')
    print(f"Downloading video from {video_url}...")
    try:
        video_response = requests.get(video_url)
        video_response.raise_for_status()
    except Exception as e:
        print(f"❌ Download Failed: {e}")
        return False
        
    title = generate_varied_title(post_data.get('Base_Title', 'New Video'), account_name)
    description = post_data.get('Caption', '')
    
    body = {
        'snippet': {
            'title': title, 
            'description': description, 
            'categoryId': '22', 
            'tags': ['shorts', account_name.replace(" ", "")]
        },
        'status': {'privacyStatus': 'public'}
    }
    
    media = MediaIoBaseUpload(BytesIO(video_response.content), 'video/*', chunksize=-1, resumable=False)
    
    try:
        insert_request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        response = insert_request.execute()
        print(f"✅ YouTube Upload Success! ID: {response.get('id')}")
        return True
    except Exception as e:
        print(f"❌ YouTube Upload Failed: {e}")
        return False

# ==============================================================================
# 3. Main Automation Engine
# ==============================================================================

def run_master_automation():
    if not SPREADSHEET_ID:
        print("FATAL ERROR: SPREADSHEET_ID is missing in Workflow file.")
        return
    
    # 1. Credentials (Memory Only)
    creds = get_credentials()
    if not creds: return

    try:
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        
        # Headers Validation
        headers = sheet.row_values(1)
        if 'Status' not in headers:
            print("ERROR: 'Status' column is missing in Sheet.")
            return
        status_col = headers.index('Status') + 1
            
        data = sheet.get_all_records()
    except Exception as e:
        print(f"FATAL ERROR: Sheet Connection Failed: {e}")
        return

    print(f"Master Automation Started. Found {len(data)} rows.")
    
    for i, row in enumerate(data):
        row_num = i + 2 
        current_status = row.get('Status')
        
        if current_status == 'PENDING' or current_status == 'FAIL':
            platform = str(row.get('Platform', '')).strip().lower()
            if current_status == 'DONE': continue

            success = False
            if 'instagram' in platform:
                success = instagram_post(row, PLATFORM_CONFIG, row_num)
            elif 'youtube' in platform:
                success = youtube_post(row, creds, row_num)
            
            if success:
                sheet.update_cell(row_num, status_col, 'DONE')
                print(f"STATUS UPDATED: Row {row_num} marked as DONE.")
            else:
                sheet.update_cell(row_num, status_col, 'FAIL')
                print(f"STATUS UPDATED: Row {row_num} marked as FAIL.")

if __name__ == "__main__":
    run_master_automation()
