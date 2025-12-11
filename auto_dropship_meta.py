import gspread
import requests
import json
import random
from io import BytesIO
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import time

# ==============================================================================
# 1. Configuration (તમારો ડેટા અહીં છે)
# ==============================================================================

# Google Sheet Setup
# Service Account Key Path - તમારા GitHub Secrets માં નાખેલું JSON File
SERVICE_ACCOUNT_FILE = 'service_account_key.json' 
SPREADSHEET_ID = 'તમારી_શીટ_ID_અહીં_નાખો' 

# Platform API Keys & Tokens
PLATFORM_CONFIG = {
    # INSTAGRAM/FACEBOOK (પહેલાનું સેટઅપ)
    "instagram_tokens": {
        "Luxivibe": {"page_id": "YOUR_PAGE_ID", "access_token": "YOUR_ACCESS_TOKEN"},
        # બાકીના 7 એકાઉન્ટ અહીં ઉમેરો
        "Royal Nexus": {"page_id": "17841479056452004", "access_token": "EAA..."}, 
        # ...
    },
    # YOUTUBE (તમારા 8 YouTube Channels ના API credentials અહીં)
    "youtube_channels": {
        "Channel 1": "youtube_channel_1_client_secrets.json", # જેમ કે 'Luxivibe'
        "Channel 2": "youtube_channel_2_client_secrets.json", # જેમ કે 'Grand Orbit'
        # ...
    }
}

# ==============================================================================
# 2. Smart AI Logic Functions (નવું સ્માર્ટ લોજિક)
# ==============================================================================

def generate_varied_title(base_title, account_name):
    """
    ટાઇટલમાં ફેરફાર લાવવા માટેનું AI લોજિક. આનાથી Google ને શંકા નહીં જાય.
    """
    
    # 1. Base keywords / synonyms
    keywords = ["Best", "Top", "Amazing", "Awesome", "New", "Latest"]
    
    # 2. Simple variation logic
    
    # જો ટાઇટલમાં 'Best' કે 'New' હોય, તો તેને બદલો.
    title_parts = base_title.split()
    if title_parts[0] in ["Best", "Top", "Amazing", "Awesome", "New", "Latest"]:
        title_parts[0] = random.choice([k for k in keywords if k != title_parts[0]])
    
    # અકાઉન્ટનું નામ ઉમેરો (બધી ચેનલના ટાઇટલ એકસરખા ન લાગે તે માટે)
    if "2025" in base_title:
        final_title = f"{' '.join(title_parts)}. Shop Now!"
    else:
        final_title = f"{' '.join(title_parts)} | {account_name}"

    return final_title[:100] # YouTube title limit

# ==============================================================================
# 3. Platform Specific Posting Functions
# ==============================================================================

def instagram_post(post_data, config, row_num):
    # (તમારો જૂનો, સફળ Instagram Posting Code અહીં પેસ્ટ કરો)
    # ...
    # (લોજિક જે Instagram / Facebook API દ્વારા ફોટો/વિડિયો અપલોડ કરે છે)
    # ...
    print(f"✅ Instagram post successful for {post_data['Account_Name']}")
    return True # જો સફળ થાય તો True

def youtube_post(post_data, config, row_num):
    """
    YouTube પર Shorts/Video Upload કરે છે અને Pinned Comment ઉમેરે છે.
    """
    account_name = post_data['Account_Name']
    
    # 1. Authentication (YouTube API)
    # તમારે દરેક ચેનલ માટે credential file બનાવવી પડશે અને GitHub Secrets માં મૂકવી પડશે.
    try:
        creds = Credentials.from_service_account_file(
            PLATFORM_CONFIG["youtube_channels"][account_name],
            scopes=['https://www.googleapis.com/auth/youtube.force-ssl']
        )
        youtube = build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ YouTube API Authentication failed for {account_name}: {e}")
        return False

    # 2. Download Video
    video_url = post_data['Video_URL']
    print(f"Downloading video from {video_url}")
    try:
        video_response = requests.get(video_url)
        video_response.raise_for_status() # Check for errors
    except Exception as e:
        print(f"❌ Error downloading video: {e}")
        return False
        
    # 3. Smart Title Generation
    title = generate_varied_title(post_data['Base_Title'], account_name)
    description = post_data['Caption']
    
    # 4. Check for Shorts (If not provided by API, we assume the user follows the format)
    # The API will automatically treat it as a Short if it's < 60s and vertical.
    # We set the tags and category for optimization.
    
    body=dict(
        snippet=dict(
            title=title,
            description=description,
            # Gaming (20) or Howto (26) or People & Blogs (22) - Category ID
            categoryId="22", 
            tags=['shorts', 'viral', 'dropshipping', account_name.lower().replace(" ", "")]
        ),
        status=dict(
            privacyStatus="public", # public, private, or unlisted
            # MadeForKids=False 
        )
    )

    # 5. Upload Video
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

        # 6. Pinned Comment Logic
        if post_data.get('Pinned_Comment'):
            time.sleep(5) # Wait for video to process
            comment_text = post_data['Pinned_Comment']
            
            # Insert comment
            comment_insert = youtube.commentThreads().insert(
                part='snippet',
                body={
                    'snippet': {
                        'videoId': video_id,
                        'topLevelComment': {
                            'snippet': {'textOriginal': comment_text}
                        }
                    }
                }
            ).execute()
            
            # Get the comment ID for pinning
            comment_id = comment_insert['snippet']['topLevelComment']['id']

            # Pin the comment
            youtube.videos().update(
                part='snippet',
                body={
                    'id': video_id,
                    'snippet': {
                        'title': title, # title must be included in update
                        'defaultAudioLanguage': 'en',
                        'defaultLanguage': 'en',
                        'categoryId': '22',
                        'tags': ['shorts', 'viral', 'dropshipping', account_name.lower().replace(" ", "")],
                        'description': description,
                        'liveBroadcastContent': 'none',
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
    # 1. Google Sheet Authentication
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        data = sheet.get_all_records()
    except Exception as e:
        print(f"FATAL ERROR: Could not connect to Google Sheet. Check ID and Keys. Error: {e}")
        return

    print(f"Master Automation Started. Found {len(data)} rows.")
    
    for i, row in enumerate(data):
        row_num = i + 2 # Sheet row number (1-based, excluding header)
        
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
                # Pinterest Code અહીં ઉમેરાશે (જ્યારે આપણે p_auth ટોકન મેળવી લઈશું)
                print(f"Pinterest is currently on hold. Skipping row {row_num}.")
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
