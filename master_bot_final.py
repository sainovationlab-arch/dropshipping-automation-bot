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
# 💎 CONFIGURATION (IG + FB IDs)
# =======================================================

# 1. AUTH TOKEN
IG_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")

# 2. BRAND DATABASE
# 👉 Tamaru SACHU IG ID niche Emerald Edge ma mukvanu bhulta nahi.
BRAND_CONFIG = {
    "PEARL VERSE": { 
        "ig_id": "17841478822408000", 
        "fb_id": "927694300421135" 
    },
    "DIAMOND DICE": { 
        "ig_id": "17841478369307404", 
        "fb_id": "873607589175898" 
    },
    "EMERALD EDGE": { 
        "ig_id": "AHIYA_SACHU_IG_ID_NAKHO",  # <--- ⚠️ AHINYA SACHU IG ID MUKJO
        "fb_id": "929305353594436"         # ✅ FB ID Added
    },
    "URBAN GLINT": { 
        "ig_id": "17841479492205083", 
        "fb_id": "892844607248221" 
    },
    "LUXIVIBE": { 
        "ig_id": "17841479492205083", 
        "fb_id": "777935382078740" 
    },
    "GRAND ORBIT": { 
        "ig_id": "17841479516066757", 
        "fb_id": "817698004771102" 
    },
    "OPUS ELITE": { 
        "ig_id": "17841479493645419", 
        "fb_id": "938320336026787" 
    },
    "ROYAL NEXUS": { 
        "ig_id": "17841479056452004", 
        "fb_id": "854486334423509" 
    }
}

# 3. SHEET SETTINGS
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# =======================================================
# ⚙️ SYSTEM CORE (SECURE CONNECT)
# =======================================================

def get_credentials():
    creds_json = os.environ.get("GCP_CREDENTIALS") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if creds_json:
        creds_dict = json.loads(creds_json)
        return Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    elif os.path.exists("gkey.json"):
        return Credentials.from_service_account_file("gkey.json", scopes=SCOPES)
    return None

def get_services():
    creds = get_credentials()
    if not creds: return None, None
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1 if SPREADSHEET_ID else client.open("Content").sheet1
    drive_service = build('drive', 'v3', credentials=creds)
    return sheet, drive_service

# =======================================================
# 🔧 UPLOAD FUNCTIONS (IG & FB)
# =======================================================

def download_video_securely(drive_service, drive_url):
    print("      ⬇️ Downloading video securely via API...")
    temp_filename = "temp_upload_video.mp4"
    if os.path.exists(temp_filename): os.remove(temp_filename)

    file_id = None
    if "/d/" in drive_url: file_id = drive_url.split('/d/')[1].split('/')[0]
    elif "id=" in drive_url: file_id = drive_url.split('id=')[1].split('&')[0]
    
    if not file_id: return None

    try:
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.FileIO(temp_filename, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False: status, done = downloader.next_chunk()
        return temp_filename
    except Exception as e:
        print(f"      ❌ Download Error: {e}")
        return None

def upload_to_instagram_resumable(brand_name, ig_user_id, file_path, caption):
    print(f"      📸 Instagram Upload ({brand_name})...")
    if not ig_user_id or "AHIYA" in ig_user_id: 
        print("      ⚠️ IG ID Invalid/Missing.")
        return False
    
    domain = "https://graph.facebook.com/v19.0"
    try:
        # Init
        url_init = f"{domain}/{ig_user_id}/media"
        params = { "upload_type": "resumable", "media_type": "REELS", "caption": caption, "access_token": IG_ACCESS_TOKEN }
        r_init = requests.post(url_init, params=params)
        data_init = r_init.json()
        
        if "id" not in data_init: return False
        upload_uri = data_init["uri"]
        container_id = data_init["id"]

        # Upload
        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            headers = { "Authorization": f"OAuth {IG_ACCESS_TOKEN}", "offset": "0", "file_size": str(file_size) }
            r_upload = requests.post(upload_uri, data=f, headers=headers)
        
        if r_upload.status_code != 200: return False

        # Publish
        print("      ⏳ Processing IG (60s)...")
        time.sleep(60)
        url_pub = f"{domain}/{ig_user_id}/media_publish"
        r_pub = requests.post(url_pub, params={"creation_id": container_id, "access_token": IG_ACCESS_TOKEN})
        
        if "id" in r_pub.json():
            print(f"      ✅ IG Published: {r_pub.json()['id']}")
            return True
        else:
            return False
    except Exception as e:
        print(f"      ❌ IG Error: {e}")
        return False

def upload_to_facebook(brand_name, fb_page_id, file_path, caption):
    """Uploads video directly to Facebook Page"""
    print(f"      📘 Facebook Upload ({brand_name})...")
    
    if not fb_page_id:
        print("      ⚠️ No FB ID found.")
        return False
        
    url = f"https://graph.facebook.com/v19.0/{fb_page_id}/videos"
    
    try:
        # FB Direct Upload (Simpler than IG)
        params = {
            "description": caption,
            "access_token": IG_ACCESS_TOKEN
        }
        
        with open(file_path, "rb") as f:
            files = {"source": f}
            r = requests.post(url, params=params, files=files)
            
        data = r.json()
        
        if "id" in data:
            print(f"      ✅ FB Published: {data['id']}")
            return True
        else:
            print(f"      ❌ FB Failed: {data}")
            return False
            
    except Exception as e:
        print(f"      ❌ FB Exception: {e}")
        return False

# =======================================================
# 🚀 MAIN EXECUTION
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
                
                # IDs
                ig_id = BRAND_CONFIG[brand].get("ig_id")
                fb_id = BRAND_CONFIG[brand].get("fb_id")
                
                video_url = row.get("Video_URL") or row.get("Video Link", "")
                title = row.get("Title_Hook") or row.get("Title", "")
                hashtags = row.get("Caption_Hashtags") or row.get("Hashtags", "")
                caption = f"{title}\n.\n{hashtags}"
                
                local_file = download_video_securely(drive_service, video_url)
                
                if local_file:
                    # 1. Try Instagram
                    ig_success = upload_to_instagram_resumable(brand, ig_id, local_file, caption)
                    
                    # 2. Try Facebook
                    fb_success = upload_to_facebook(brand, fb_id, local_file, caption)

                    # Cleanup
                    if os.path.exists(local_file): os.remove(local_file)

                    # Update Sheet if AT LEAST ONE succeeded
                    if ig_success or fb_success:
                        final_status = "POSTED"
                        if ig_success and fb_success: final_status = "POSTED_BOTH"
                        elif ig_success: final_status = "POSTED_IG_ONLY"
                        elif fb_success: final_status = "POSTED_FB_ONLY"
                        
                        sheet.update_cell(i, col_status, final_status)
                        print(f"      📝 Sheet Updated: {final_status}")
                        processed_count += 1
                        time.sleep(10) # Safety Pause
                else:
                    print("      ⚠️ Skipping: Download failed.")

    if processed_count == 0:
        print("💤 No tasks found. Exiting cleanly.")
    else:
        print(f"🎉 Job Done! Uploads in this cycle: {processed_count}")

if __name__ == "__main__":
    start_bot()
