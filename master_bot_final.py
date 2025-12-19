import os
import time
import json
import requests
import gspread
import gdown  
from google.oauth2.service_account import Credentials

# =======================================================
# 💎 CONFIGURATION
# =======================================================

# 1. AUTH TOKEN
IG_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")

# 2. BRAND DATABASE
BRAND_CONFIG = {
    "PEARL VERSE": { "ig_id": "17841478822408000" },
    "DIAMOND DICE": { "ig_id": "17841478369307404" },
    "EMERALD EDGE": { "ig_id": "17841478369307404" },
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
# ⚙️ SYSTEM CORE
# =======================================================

def get_sheet_connection():
    """Connects to Google Sheet via GitHub Secret"""
    creds_json = os.environ.get("GCP_CREDENTIALS") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    
    if creds_json:
        try:
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            client = gspread.authorize(creds)
            
            if SPREADSHEET_ID:
                return client.open_by_key(SPREADSHEET_ID).sheet1
            else:
                return client.open("Content").sheet1
        except Exception as e:
            print(f"❌ Auth Error: {e}")
            return None
    
    print("❌ CRITICAL: No Credentials Found.")
    return None

# =======================================================
# 🔧 SMART UPLOAD FUNCTIONS (HEADER FIX APPLIED)
# =======================================================

def download_video_locally(drive_url):
    """Downloads Google Drive video to a local temp file"""
    print("      ⬇️ Downloading video locally to bypass Google block...")
    temp_filename = "temp_upload_video.mp4"
    
    if os.path.exists(temp_filename):
        os.remove(temp_filename)

    try:
        output = gdown.download(drive_url, temp_filename, quiet=False, fuzzy=True)
        
        if output and os.path.exists(temp_filename):
            size = os.path.getsize(temp_filename)
            print(f"      ✅ Downloaded ({size / 1024 / 1024:.2f} MB)")
            return temp_filename
        else:
            print("      ❌ Download failed (File not found).")
            return None
    except Exception as e:
        print(f"      ❌ Download Exception: {e}")
        return None

def upload_to_instagram_resumable(brand_name, ig_user_id, file_path, caption):
    """
    FIXED: Uses correct headers ('offset' instead of 'file_offset')
    """
    print(f"      📸 Instagram Resumable Upload ({brand_name})...")
    
    if not ig_user_id or not IG_ACCESS_TOKEN:
        print("      ⚠️ Missing ID or Token.")
        return False

    domain = "https://graph.facebook.com/v19.0"
    
    try:
        # STEP 1: INITIALIZE UPLOAD SESSION
        url_init = f"{domain}/{ig_user_id}/media"
        params = {
            "upload_type": "resumable",
            "media_type": "REELS",
            "caption": caption,
            "access_token": IG_ACCESS_TOKEN
        }
        
        r_init = requests.post(url_init, params=params)
        data_init = r_init.json()
        
        upload_uri = data_init.get("uri")
        container_id = data_init.get("id")
        
        if not upload_uri or not container_id:
            print(f"      ❌ Init Failed: {data_init}")
            return False
            
        print(f"      🔹 Session Created. ID: {container_id}")

        # STEP 2: UPLOAD THE FILE BYTES (HEADER FIX HERE)
        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            headers = {
                "Authorization": f"OAuth {IG_ACCESS_TOKEN}",
                "offset": "0",              # <--- SUNDAYO: 'file_offset' hatu te 'offset' karyu
                "file_size": str(file_size)
            }
            print("      🔹 Uploading bytes to Instagram...")
            r_upload = requests.post(upload_uri, data=f, headers=headers)
        
        if r_upload.status_code != 200:
            print(f"      ❌ Byte Upload Failed: {r_upload.text}")
            return False

        # STEP 3: PUBLISH THE CONTAINER
        print("      ⏳ Waiting for Media Processing (60s)...")
        time.sleep(60) 
        
        url_pub = f"{domain}/{ig_user_id}/media_publish"
        pub_params = {
            "creation_id": container_id,
            "access_token": IG_ACCESS_TOKEN
        }
        
        r_pub = requests.post(url_pub, params=pub_params)
        data_pub = r_pub.json()
        
        if "id" in data_pub:
            print(f"      🎉 SUCCESS! Published Reel ID: {data_pub['id']}")
            return True
        else:
            print(f"      ❌ Publish Failed: {data_pub}")
            return False

    except Exception as e:
        print(f"      ❌ Exception: {e}")
        return False

# =======================================================
# 🚀 MAIN EXECUTION
# =======================================================

def start_bot():
    print("\n🤖 GITHUB AUTOMATION BOT (FINAL HEADER FIX) STARTED...")
    print("-" * 50)
    
    sheet = get_sheet_connection()
    if not sheet: return

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
                
                # Download -> Upload
                local_file = download_video_locally(video_url)
                
                if local_file:
                    success = upload_to_instagram_resumable(brand, ig_id, local_file, caption)
                    
                    if os.path.exists(local_file):
                        os.remove(local_file)

                    if success:
                        sheet.update_cell(i, col_status, "POSTED")
                        print(f"      📝 Sheet Updated: POSTED")
                        processed_count += 1
                else:
                    print("      ⚠️ Skipping: Could not download video.")

    if processed_count == 0:
        print("\n💤 No PENDING tasks found.")
    else:
        print(f"\n🎉 Job Done! Total Uploads: {processed_count}")

if __name__ == "__main__":
    start_bot()
