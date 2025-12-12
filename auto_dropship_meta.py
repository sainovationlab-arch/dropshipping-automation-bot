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
# 1. ROBUST CONFIGURATION (No Files Needed)
# ==============================================================================

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
GCP_CREDENTIALS_JSON = os.environ.get("GCP_CREDENTIALS") # સીધું Secret માંથી વાંચશે

# આ ફંક્શન ગેરંટી આપે છે કે ચાવી સાચી રીતે વંચાય
def get_credentials():
    try:
        if not GCP_CREDENTIALS_JSON:
            raise ValueError("GCP_CREDENTIALS secret is missing in GitHub!")
        
        # JSON લોડ કરો
        creds_dict = json.loads(GCP_CREDENTIALS_JSON)
        return Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/youtube.force-ssl']
        )
    except json.JSONDecodeError:
        print("❌ FATAL ERROR: Your GitHub Secret 'GCP_CREDENTIALS' is not a valid JSON.")
        print("Please delete it and paste the content of your .json file exactly as is.")
        return None
    except Exception as e:
        print(f"❌ Credential Error: {e}")
        return None

# Platform Configuration
PLATFORM_CONFIG = {
    "instagram_tokens": {
        "Luxivibe": {"page_id": "YOUR_PAGE_ID", "access_token": "YOUR_ACCESS_TOKEN"},
        "Urban Glint": {"page_id": "YOUR_PAGE_ID", "access_token": "YOUR_ACCESS_TOKEN"},
        # ... બાકીના બધા એકાઉન્ટ્સ અહીં
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
    # (તમારો સ્ટાન્ડર્ડ Instagram કોડ)
    print(f"✅ Instagram posting simulation for {post_data['Account_Name']}")
    return True 

def youtube_post(post_data, creds, row_num):
    account_name = post_data['Account_Name']
    
    # અહી કોઈ ફાઈલની જરૂર નથી, આપણે સીધા creds વાપરીશું
    try:
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
    
    # ૧. ક્રેડેન્શિયલ મેળવો (ડાયરેક્ટ)
    creds = get_credentials()
    if not creds: return

    try:
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        
        headers = sheet.row_values(1)
        try:
            status_col = headers.index('Status') + 1
        except ValueError:
            print("ERROR: 'Status' column not found in sheet. Check headers (Status vs Status ).")
            return
            
        data = sheet.get_all_records()
    except Exception as e:
        print(f"FATAL ERROR: Sheet Connection Failed: {e}")
        return

    print(f"Master Automation Started. Found {len(data)} rows.")
    
    for i, row in enumerate(data):
        row_num = i + 2 
        current_status = row.get('Status')
        
        if current_status == 'PENDING' or current_status == 'FAIL':
            platform = row.get('Platform', '').strip()
            if current_status == 'DONE': continue

            success = False
            if platform.lower() == 'instagram':
                success = instagram_post(row, PLATFORM_CONFIG, row_num)
            elif platform.lower() == 'youtube':
                # YouTube માટે હવે આપણે સીધા creds પાસ કરીએ છીએ
                success = youtube_post(row, creds, row_num)
            
            if success:
                sheet.update_cell(row_num, status_col, 'DONE')
                print(f"STATUS UPDATED: Row {row_num} marked as DONE.")
            else:
                sheet.update_cell(row_num, status_col, 'FAIL')
                print(f"STATUS UPDATED: Row {row_num} marked as FAIL.")

if __name__ == "__main__":
    run_master_automation()
