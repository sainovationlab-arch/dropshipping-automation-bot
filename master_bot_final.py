import gspread
import requests
import json
import random
import os
import time
import gdown  # <--- સ્પેશિયલ ડાઉનલોડર
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

# ==============================================================================
# 2. HELPER FUNCTIONS
# ==============================================================================

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

def download_video(url):
    """ડ્રાઈવ લિંક અને ડાયરેક્ટ લિંક બંનેને હેન્ડલ કરે છે."""
    print(f"⬇️ Downloading video from: {url}")
    output_file = "temp_video.mp4"
    
    try:
        # જો Google Drive લિંક હોય તો gdown વાપરો
        if "drive.google.com" in url:
            # fuzzy=True એટલે પરમિશનના ઈશ્યુ હોય તો પણ પ્રયત્ન કરશે
            gdown.download(url, output_file, quiet=False, fuzzy=True)
        else:
            # સાદી લિંક હોય તો requests વાપરો
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        # ફાઈલ ચેક કરો
        if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
            print(f"✅ Download Successful! Size: {os.path.getsize(output_file)} bytes")
            return output_file
        else:
            print("❌ Download Failed: File is empty or too small.")
            return None
            
    except Exception as e:
        print(f"❌ Download Error: {e}")
        return None

# ==============================================================================
# 3. POSTING FUNCTIONS
# ==============================================================================

def instagram_post(row, row_num):
    account_name = str(row.get('Account_Name', '')).strip()
    page_id = INSTAGRAM_IDS.get(account_name)
    
    if not page_id:
        print(f"⚠️ No Instagram ID found for {account_name}")
        return None 
        
    video_url = row.get('Video_URL')
    caption = row.get('Caption', '')
    
    # ઈન્સ્ટાગ્રામ માટે આપણને પબ્લિક URL જોઈએ, પણ જો ડ્રાઈવ લિંક હોય તો તે ડાયરેક્ટ ચાલતી નથી.
    # ગ્રાફ API માટે વિડિયો પબ્લિક હોવો જરૂરી છે. 
    # અહીં આપણે ડાઉનલોડ કરીને અપલોડ કરવાની કોશિશ કરીએ છીએ (Container Upload logic slightly different for local file)
    # અત્યારે આપણે ડાયરેક્ટ URL જ વાપરીશું, પણ જો તે ડ્રાઈવની હોય તો ફેલ થશે.
    # ઇન્સ્ટાગ્રામ માટે તમારે 'Direct Download Link' વાપરવી પડે અથવા વિડિયો કોઈ પબ્લિક સર્વર પર હોવો જોઈએ.
    # ગૂગલ ડ્રાઈવની લિંક ઇન્સ્ટાગ્રામ API સીધી સ્વીકારતું નથી.
    
    # જો કે, YouTube માટે આપણે ફાઈલ ડાઉનલોડ કરીને મોકલી શકીએ છીએ.
    # ઇન્સ્ટાગ્રામ માટે આપણે ડ્રાઈવ લિંકને 'Direct Link' માં ફેરવવી પડે.
    
    print(f"📸 Posting to Instagram: {account_name}...")

    # ડ્રાઈવ લિંક ફિક્સ (Hack for Drive Links on Insta API)
    if "drive.google.com" in video_url and "/view" in video_url:
        video_url = video_url.replace("/view", "/preview").replace("file/d/", "uc?export=download&id=")
        # આ એક પ્રયાસ છે, પણ ડ્રાઈવ લિંક ઇન્સ્ટા પર અઘરી છે.

    try:
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
            return None

        print(f"   - Container Created: {creation_id}. Waiting 60s...")
        time.sleep(60) 
        
        pub_url = f"https://graph.facebook.com/v19.0/{page_id}/media_publish"
        pub_params = {'creation_id': creation_id, 'access_token': FB_ACCESS_TOKEN}
        pub_res = requests.post(pub_url, params=pub_params).json()
        
        if pub_res.get('id'):
            print(f"✅ IG Published! ID: {pub_res['id']}")
            return "IG_SUCCESS"
        else:
            print(f"❌ IG Publish Failed: {pub_res}")
            return None

    except Exception as e:
        print(f"❌ IG Error: {e}")
        return None

def youtube_post(row, row_num):
    youtube = get_youtube_service()
    if not youtube: return None

    video_url = row.get('Video_URL')
    
    # --- ફિક્સ: સાચો વિડિયો ડાઉનલોડ કરો ---
    local_file = download_video(video_url)
    if not local_file: return None

    base_title = row.get('Base_Title', 'New Video')
    final_title = f"{base_title} | {row.get('Account_Name')}"[:100]
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

    media = MediaIoBaseUpload(local_file, 'video/*', chunksize=-1, resumable=True)
    
    try:
        req = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        resp = None
        while resp is None:
            status, resp = req.next_chunk()
            if status:
                print(f"   - Uploading {int(status.progress() * 100)}%...")
        
        video_id = resp.get('id')
        print(f"✅ YouTube Upload Success! ID: {video_id}")
        
        # ક્લીનઅપ
        if os.path.exists(local_file):
            os.remove(local_file)
            
        return f"https://youtu.be/{video_id}" 
        
    except Exception as e:
        print(f"❌ YouTube Upload Error: {e}")
        if os.path.exists(local_file): os.remove(local_file)
        return None

# ==============================================================================
# 3. MAIN AUTOMATION ENGINE
# ==============================================================================

def run_master_automation():
    sheet = get_sheet_service()
    if not sheet: return

    try:
        data = sheet.get_all_records()
        headers = list(data[0].keys()) if data else []
        sheet_headers = sheet.row_values(1)
        
        def get_col_idx(name):
            try: return next(i for i, v in enumerate(sheet_headers) if v.lower() == name.lower()) + 1
            except: return None

        status_col_idx = get_col_idx('Status')
        link_col_idx = get_col_idx('Link')

        if not status_col_idx:
            print("❌ Error: 'Status' column not found.")
            return

    except Exception as e:
        print(f"❌ Data Read Error: {e}")
        return

    print(f"🚀 Automation Started. Rows found: {len(data)}")

    for i, row in enumerate(data):
        row_num = i + 2
        
        status_key = next((h for h in headers if h.lower() == 'status'), None)
        current_status = str(row.get(status_key, '')).strip().upper()
        
        if current_status == 'PENDING' or current_status == 'FAIL':
            
            platform_key = next((h for h in headers if h.lower() == 'platform'), None)
            platform = str(row.get(platform_key, '')).strip().lower()
            
            if not platform: continue
            if current_status == 'DONE': continue

            print(f"Processing Row {row_num}: {platform}")
            result_link = None
            
            if 'instagram' in platform or 'facebook' in platform:
                result_link = instagram_post(row, row_num)
            elif 'youtube' in platform:
                result_link = youtube_post(row, row_num)
            
            if result_link:
                sheet.update_cell(row_num, status_col_idx, 'DONE')
                if link_col_idx and "http" in str(result_link):
                    sheet.update_cell(row_num, link_col_idx, result_link)
                print(f"✅ Row {row_num} DONE. Link: {result_link}")
            else:
                sheet.update_cell(row_num, status_col_idx, 'FAIL')
                print(f"❌ Row {row_num} FAIL")

if __name__ == "__main__":
    run_master_automation()
