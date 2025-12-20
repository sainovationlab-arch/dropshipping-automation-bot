import os
import time
import json
import requests
import io
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# =======================================================
# 💎 CONFIGURATION
# =======================================================

# 1. AUTH TOKEN
IG_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")

# 2. BRAND DATABASE
# ⚠️ AHINYA TAMARA SACHA IDs CHECK KARI LEJO
BRAND_CONFIG = {
    "PEARL VERSE": { "ig_id": "17841478822408000" },
    "DIAMOND DICE": { "ig_id": "17841478369307404" },
    "EMERALD EDGE": { "ig_id": "17841478369307404" },  # <--- AHINYA SACHO ID MUKJO
    "URBAN GLINT": { "ig_id": "17841479492205083" },
    "LUXIVIBE": { "ig_id": "17841479492205083" },
    "GRAND ORBIT": { "ig_id": "17841479516066757" },
    "OPUS ELITE": { "ig_id": "17841479493645419" },
    "ROYAL NEXUS": { "ig_id": "17841479056452004" }
}

# 3. SHEET SETTINGS
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# =======================================================
# ⚙️ SYSTEM CORE (SECURE CONNECT)
# =======================================================

def get_credentials():
    """Fetches Credentials object from Env or Local File"""
    creds_json = os.environ.get("GCP_CREDENTIALS") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    
    if creds_json:
        creds_dict = json.loads(creds_json)
        return Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    
    elif os.path.exists("gkey.json"):
        return Credentials.from_service_account_file("gkey.json", scopes=SCOPES)
    
    return None

def get_services():
    """Returns authenticated Google Sheet AND Drive Service"""
    creds = get_credentials()
    if not creds:
        print("❌ CRITICAL: No Credentials Found.")
        return None, None

    # Sheet Service
    client = gspread.authorize(creds)
    if SPREADSHEET_ID:
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    else:
        sheet = client.open("Content").sheet1

    # Drive Service (For Secure Download)
    drive_service = build('drive', 'v3', credentials=creds)
    
    return sheet, drive_service

# =======================================================
# 🔧 SMART UPLOAD FUNCTIONS
# =======================================================

def download_video_securely(drive_service, drive_url):
    """Downloads video using Official Google Drive API"""
    print("      ⬇️ Downloading video securely via API...")
    temp_filename = "temp_upload_video.mp4"
    
    if os.path.exists(temp_filename):
        os.remove(temp_filename)

    # Extract File ID
    file_id = None
    if "/d/" in drive_url:
        file_id = drive_url.split('/d/')[1].split('/')[0]
    elif "id=" in drive_url:
        file_id = drive_url.split('id=')[1].split('&')[0]
    
    if not file_id:
        print("      ❌ Invalid Drive URL format.")
        return None

    try:
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.FileIO(temp_filename, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        print(f"      ✅ Download Complete! (Secure Mode)")
        return temp_filename

    except Exception as e:
        print(f"      ❌ Download Error: {e}")
        return None

def upload_to_instagram_resumable(brand_name, ig_user_id, file_path, caption):
    """Resumable Upload to bypass Timeouts"""
    print(f"      📸 Instagram Resumable Upload ({brand_name})...")
    
    if not ig_user_id or not IG_ACCESS_TOKEN:
        print("      ⚠️ Missing ID or Token.")
        return False

    domain = "https://graph.facebook.com/v19.0"
    
    try:
        # STEP 1: INITIALIZE
        url_init = f"{domain}/{ig_user_id}/media"
        params = {
            "upload_type": "resumable",
            "media_type": "REELS",
            "caption": caption,
            "access_token": IG_ACCESS_TOKEN
        }
        
        r_init = requests.post(url_init, params=params)
        data_init = r_init.json()
        
        if "id" not in data_init:
            print(f"      ❌ Init Failed: {data_init}")
            return False
            
        upload_uri = data_init["uri"]
        container_id = data_init["id"]
        print(f"      🔹 Session Created. ID: {container_id}")

        # STEP 2: UPLOAD BYTES
        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            headers = {
                "Authorization": f"OAuth {IG_ACCESS_TOKEN}",
                "offset": "0",
                "file_size": str(file_size)
            }
            print("      🔹 Uploading bytes...")
            r_upload = requests.post(upload_uri, data=f, headers=headers)
        
        if r_upload.status_code != 200:
            print(f"      ❌ Byte Upload Failed: {r_upload.text}")
            return False

        # STEP 3: PUBLISH
        print("      ⏳ Waiting for Processing (60s)...")
        time.sleep(60)
        
        url_pub = f"{domain}/{ig_user_id}/media_publish"
        pub_params = {"creation_id": container_id, "access_token": IG_ACCESS_TOKEN}
        r_pub = requests.post(url_pub, params=pub_params)
        
        if "id" in r_pub.json():
            print(f"      🎉 SUCCESS! Published ID: {r_pub.json()['id']}")
            return True
        else:
            print(f"      ❌ Publish Failed: {r_pub.json()}")
            return False

    except Exception as e:
        print(f"      ❌ Exception: {e}")
        return False

# =======================================================
# 🚀 MAIN EXECUTION (RUN ONCE & EXIT)
# =======================================================

def start_bot():
    print("-" * 50)
    print(f"⏰ BOT STARTED AT: {time.ctime()}")
    
    sheet, drive_service = get_services()
    if not sheet or not drive_service: return

    try:
        records = sheet.get_all_records()
        headers = sheet.row_values(1)
        try: col_status = headers.index("Status") + 1
        except: col_status = 5
    except Exception as e:
        print(f"❌ Error Reading Sheet: {e}")
        return

    processed_count = 0

    for i, row in enumerate(records, start=2):
        brand = str(row.get("Brand_Name") or row.get("Account_Name") or row.get("Account Name", "")).strip().upper()
        status = str(row.get("Status", "")).strip().upper()
        
        if status == "PENDING":
            if brand in BRAND_CONFIG:
                print(f"\n👉 Processing Row {i}: {row.get('Title_Hook') or row.get('Title')} | Brand: {brand}")
                
                ig_id = BRAND_CONFIG[brand]["ig_id"]
                video_url = row.get("Video_URL") or row.get("Video Link", "")
                
                # Caption
                title = row.get("Title_Hook") or row.get("Title", "")
                hashtags = row.get("Caption_Hashtags") or row.get("Hashtags", "")
                caption = f"{title}\n.\n{hashtags}"
                
                # --- SECURE DOWNLOAD & UPLOAD ---
                local_file = download_video_securely(drive_service, video_url)
                
                if local_file:
                    success = upload_to_instagram_resumable(brand, ig_id, local_file, caption)
                    
                    if os.path.exists(local_file): os.remove(local_file)

                    if success:
                        sheet.update_cell(i, col_status, "POSTED")
                        print(f"      📝 Sheet Updated: POSTED")
                        processed_count += 1
                        
                        # Safety Pause: 10 second rukse (spamming rokva)
                        time.sleep(10)
                else:
                    print("      ⚠️ Skipping: Download failed.")

    if processed_count == 0:
        print("💤 No tasks found. Exiting cleanly.")
    else:
        print(f"🎉 Job Done! Uploads in this cycle: {processed_count}")

if __name__ == "__main__":
    start_bot()
