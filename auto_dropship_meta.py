import gspread
import requests
import json
import random
from io import BytesIO
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import time
import os # <--- આ લાઇન નવી ઉમેરાઈ છે

# ==============================================================================
# 1. Configuration (તમારો ડેટા અહીં છે)
# ==============================================================================

# Google Sheet Setup
# Service Account Key Path - તમારા GitHub Secrets માં નાખેલું JSON File
SERVICE_ACCOUNT_FILE = 'service_account_key.json' 
# SPREADSHEET_ID હવે GitHub Actions માંથી વાંચવામાં આવશે.
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID") 

# Platform API Keys & Tokens
PLATFORM_CONFIG = {
    # INSTAGRAM/FACEBOOK (તમારા 8 એકાઉન્ટનો ડેટા અહીં અપડેટ કરો)
    "instagram_tokens": {
        "Luxivibe": {"page_id": "YOUR_PAGE_ID_1", "access_token": "YOUR_ACCESS_TOKEN_1"},
        "Urban Glint": {"page_id": "YOUR_PAGE_ID_2", "access_token": "YOUR_ACCESS_TOKEN_2"},
        # બાકીના 6 એકાઉન્ટ અહીં ઉમેરો...
    },
    # YOUTUBE (તમારા 8 YouTube Channels ના Service Account File Names અહીં)
    "youtube_channels": {
        "Luxivibe": "luxivibe_yt.json", # ઉદાહરણ તરીકે
        "Urban Glint": "urbanglint_yt.json", 
        # બાકીના 6 એકાઉન્ટ અહીં ઉમેરો...
    }
}

# = આ સિવાયનો કોડ તમારા માટે ઓટોમેટેડ છે અને તેને બદલવાની જરૂર નથી = #

# ==============================================================================
# 2. Smart AI Logic Functions
# ==============================================================================

def generate_varied_title(base_title, account_name):
    """
    ટાઇટલમાં ફેરફાર લાવવા માટેનું AI લોજિક (Anti-Google Detection)
    """
    keywords = ["Best", "Top", "Amazing", "Awesome", "New", "Latest"]
    
    # Simple variation logic
    title_parts = base_title.split()
    if title_parts and title_parts[0] in keywords:
        # ટાઇટલનો પહેલો શબ્દ બદલો
        title_parts[0] = random.choice([k for k in keywords if k != title_parts[0]])
    
    # અકાઉન્ટનું નામ ઉમેરો
    final_title = f"{' '.join(title_parts)} | {account_name}"

    return final_title[:100]

# ==============================================================================
# 3. Platform Specific Posting Functions
# ==============================================================================

def instagram_post(post_data, config, row_num):
    # (તમારો જૂનો, સફળ Instagram Posting Code અહીં ચાલશે)
    # અત્યારે આને Dummy રાખીશું, કારણ કે તમારો કોડ સફળ થઈ ગયો છે.
    print(f"✅ Instagram posting simulation successful for {post_data['Account_Name']}")
    return True 

def youtube_post(post_data, config, row_num):
    """
    YouTube પર Shorts/Video Upload કરે છે, Smart Title વાપરે છે અને Pinned Comment ઉમેરે છે.
    """
    account_name = post_data['Account_Name']
    
    # 1. Authentication (YouTube API)
    try:
        creds_file = PLATFORM_CONFIG["youtube_channels"][account_name]
        creds = Credentials.from_service_account_file(
            creds_file,
            scopes=['https://www.googleapis.com/auth/youtube.force-ssl']
        )
        youtube = build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ YouTube API Authentication failed for {account_name} (Check file {creds_file}): {e}")
        return False

    # 2. Download Video (Assuming Video_URL is a direct link or public Google Drive link)
    video_url = post_data['Video_URL']
    print(f"Downloading video from {video_url}")
    try:
        video_response = requests.get(video_url)
        video_response.raise_for_status() 
    except Exception as e:
        print(f"❌ Error downloading video: {e}")
        return False
        
    # 3. Smart Title Generation
    title = generate_varied_title(post_data['Base_Title'], account_name)
    description = post_data['Caption']
    
    # The API will automatically handle Shorts if the video is < 60s and vertical.
    body=dict(
        snippet=dict(
            title=title,
            description=description,
            categoryId="22", # People & Blogs is general category
            tags=['shorts', 'viral', 'dropshipping', account_name.lower().replace(" ", "")]
        ),
        status=dict(
            privacyStatus="public", 
        )
    )

    # 4. Upload Video
    media = MediaIoBaseUpload(BytesIO(video_response.content), 'video/*', chunksize=-1, resumable=False)
    
    try:
        insert_request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        response = insert_request.execute()
        video_id = response.get('id')
        print(f"✅ YouTube video uploaded successfully! Video ID: {video_id}")

        # 5. Pinned Comment Logic
        if post_data.get('Pinned_Comment'):
            time.sleep(5) 
            comment_text = post_data['Pinned_Comment']
            
            # 5a. Insert comment
            comment_insert = youtube.commentThreads().insert(
                part='snippet',
                body={'snippet': {'videoId': video_id, 'topLevelComment': {'snippet': {'textOriginal': comment_text}}}}
            ).execute()
            
            comment_id = comment_insert['snippet']['topLevelComment']['id']

            # 5b. Pin the comment (Update video metadata)
            youtube.videos().update(
                part='snippet',
                body={
                    'id': video_id,
                    'snippet': {
                        'title': title, 
                        'categoryId': '22',
                        'description': description,
                        'tags': ['shorts', 'viral', 'dropshipping', account_name.lower().replace(" ", "")],
                        'pinnedCommentId': comment_id
                    }
                }
            ).execute()
            print(f"✅ Pinned comment added and pinned successfully!")

        return True

    except Exception as e:
        print(f"❌ YouTube upload or comment failed: {e}")
        return False


# ==============================================================================
# 4. Main Integrator Logic (Master Code)
# ==============================================================================

def run_master_automation():
    if not SPREADSHEET_ID:
        print("FATAL ERROR: SPREADSHEET_ID environment variable is missing. Check your .yml file.")
        return
        
    # 1. Google Sheet Authentication
    try:
        # GCP_CREDENTIALS હવે os.environ માંથી વંચાશે.
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        data = sheet.get_all_records()
    except Exception as e:
        print(f"FATAL ERROR: Could not connect to Google Sheet (ID: {SPREADSHEET_ID}). Check ID and Keys. Error: {e}")
        return

    print(f"Master Automation Started for Sheet ID: {SPREADSHEET_ID}. Found {len(data)} rows.")
    
    for i, row in enumerate(data):
        row_num = i + 2 
        
        if row.get('Status') == 'PENDING':
            
            platform = row.get('Platform', '').strip()
            account_name = row.get('Account_Name', '').strip()
            
            if not platform or not account_name:
                print(f"Skipping row {row_num}: Platform or Account_Name is missing.")
                continue

            success = False
            
            # --- PLATFORM SELECTION LOGIC ---
            if platform.lower() == 'instagram':
                print(f"Processing Instagram for {account_name}...")
                success = instagram_post(row, PLATFORM_CONFIG, row_num)
                
            elif platform.lower() == 'youtube':
                print(f"Processing YouTube for {account_name}...")
                success = youtube_post(row, PLATFORM_CONFIG, row_num)

            elif platform.lower() == 'pinterest':
                # Pinterest Code અહીં ઉમેરાશે 
                print(f"Pinterest is on hold. Skipping row {row_num}.")
                continue
                
            else:
                print(f"Skipping row {row_num}: Unknown Platform '{platform}'.")
                continue

            # --- UPDATE STATUS LOGIC ---
            if success:
                sheet.update_cell(row_num, data[0].index('Status') + 1, 'DONE')
                print(f"STATUS UPDATED: Row {row_num} marked as DONE.")
            else:
                sheet.update_cell(row_num, data[0].index('Status') + 1, 'FAIL')
                print(f"STATUS UPDATED: Row {row_num} marked as FAIL.")

    print("Master Automation Finished.")

if __name__ == "__main__":
    run_master_automation()
