import os
import json
import time
import requests
import re
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# ==============================================================================
# 1. SETUP & CONFIGURATION
# ==============================================================================

def get_env_var(keys):
    """Find secret from environment variables safely"""
    for key in keys:
        val = os.getenv(key)
        if val: return str(val).strip()
    return None

def get_sheet_service():
    """Connect to Google Sheet"""
    print("🔌 Connecting to Google Sheets...")
    creds_json = get_env_var(["GCP_CREDENTIALS", "GOOGLE_CREDENTIALS"])
    if not creds_json:
        print("❌ FATAL: GCP_CREDENTIALS missing in .env file.")
        return None
    
    try:
        creds = Credentials.from_service_account_info(
            json.loads(creds_json), 
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        client = gspread.authorize(creds)
        sheet_id = get_env_var(["SHEET_CONTENT_URL", "SPREADSHEET_ID"])
        if "docs.google.com" in sheet_id:
            return client.open_by_url(sheet_id).sheet1
        return client.open_by_key(sheet_id).sheet1
    except Exception as e:
        print(f"❌ Sheet Connection Error: {e}")
        return None

# ==============================================================================
# 2. INSTAGRAM LOGIC (DETAILED DEBUGGING)
# ==============================================================================

def upload_to_catbox(file_path):
    """Uploads video to Catbox to get a public URL"""
    print("🐱 Uploading to Catbox (for Instagram compatibility)...")
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload", "userhash": ""},
                files={"fileToUpload": f},
                timeout=120
            )
        if response.status_code == 200:
            url = response.text.strip()
            print(f"✅ Catbox URL: {url}")
            return url
        else:
            print(f"❌ Catbox Failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Catbox Error: {e}")
        return None

def post_to_instagram(brand, video_path, caption):
    """Posts Reel to Instagram with FULL ERROR REPORTING"""
    print(f"📸 Starting Instagram Upload for: {brand}")
    
    # 1. Get Credentials
    brand_key = brand.upper().replace(" ", "_")
    ig_user_id = get_env_var([f"INSTAGRAM_ACCOUNT_ID_{brand_key}", "INSTAGRAM_ACCOUNT_ID"])
    access_token = get_env_var([f"INSTAGRAM_ACCESS_TOKEN_{brand_key}", "INSTAGRAM_ACCESS_TOKEN"])

    if not ig_user_id or not access_token:
        print(f"❌ MISSING CREDENTIALS: Check .env for INSTAGRAM_ACCOUNT_ID_{brand_key}")
        return False

    # 2. Get Public URL (Catbox)
    public_url = upload_to_catbox(video_path)
    if not public_url: return False

    # 3. Create Container
    print("⏳ Sending Video to Instagram API...")
    url_create = f"https://graph.facebook.com/v18.0/{ig_user_id}/media"
    payload = {
        "video_url": public_url,
        "media_type": "REELS",
        "caption": caption,
        "access_token": access_token
    }

    r = requests.post(url_create, data=payload)
    
    # --- CRITICAL DEBUGGING BLOCK ---
    if r.status_code != 200:
        print("\n❌ ❌ INSTAGRAM API REFUSED UPLOAD ❌ ❌")
        print(f"👉 Status Code: {r.status_code}")
        try:
            error_details = r.json()
            print(f"👉 Error Message: {error_details['error']['message']}")
            print(f"👉 Error Type: {error_details['error']['type']}")
            if "OAuthException" in error_details['error']['type']:
                print("💡 HINT: Tamaro Token Expire thai gayo che. Navo Token Generate karo.")
            if "marketing_api" in error_details['error']['type']:
                print("💡 HINT: Video format kharab che (Too long? Wrong aspect ratio?).")
        except:
            print(f"👉 Raw Error: {r.text}")
        print("-" * 40)
        return False
    # --------------------------------

    creation_id = r.json()['id']
    print(f"✅ Container Created ID: {creation_id}")

    # 4. Wait for Processing
    print("⏳ Instagram is processing the video (Waiting 60s)...")
    time.sleep(60)

    # 5. Publish
    print("🚀 Publishing...")
    url_publish = f"https://graph.facebook.com/v18.0/{ig_user_id}/media_publish"
    pub_payload = {"creation_id": creation_id, "access_token": access_token}
    
    pub = requests.post(url_publish, data=pub_payload)
    
    if pub.status_code == 200:
        print("✅✅ INSTAGRAM POST SUCCESS!")
        return True
    else:
        print(f"❌ Publish Failed: {pub.text}")
        return False

# ==============================================================================
# 3. HELPER: DOWNLOAD VIDEO
# ==============================================================================

def download_video(url, filename):
    print(f"⬇️ Downloading video...")
    if "drive.google.com" in url:
        file_id = url.split("/d/")[1].split("/")[0] if "/d/" in url else url.split("id=")[1]
        url = f"https://drive.google.com/uc?export=download&confirm=t&id={file_id}"
    
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        return True
    except Exception as e:
        print(f"❌ Download Error: {e}")
        return False

# ==============================================================================
# 4. MAIN BOT LOOP
# ==============================================================================

def run_bot():
    print("🚀 Master Automation Bot Started...")
    sheet = get_sheet_service()
    if not sheet: return

    try:
        data = sheet.get_all_values()
        headers = data[0]
        status_col = headers.index("Status") + 1
        
        # Loop through rows
        for i, row in enumerate(data[1:]):
            row_num = i + 2
            status = row[headers.index("Status")]
            platform = row[headers.index("Platform")].lower()
            brand = row[headers.index("Brand_Name")]
            
            # Filter for PENDING/FAIL rows
            if status in ["PENDING", "FAIL", "fail", "Pending"]:
                print(f"\n--- Processing Row {row_num}: {platform} ({brand}) ---")
                
                video_url = row[headers.index("Video_URL")]
                caption = row[headers.index("Description")]
                
                # --- INSTAGRAM ---
                if "instagram" in platform:
                    temp_file = "temp_video.mp4"
                    if download_video(video_url, temp_file):
                        sheet.update_cell(row_num, status_col, "PROCESSING")
                        
                        if post_to_instagram(brand, temp_file, caption):
                            sheet.update_cell(row_num, status_col, "DONE")
                        else:
                            # Error is already printed in console by the function above
                            sheet.update_cell(row_num, status_col, "FAIL_API")
                        
                        if os.path.exists(temp_file): os.remove(temp_file)
                    else:
                        sheet.update_cell(row_num, status_col, "FAIL_DL")

    except Exception as e:
        print(f"❌ SYSTEM CRASH: {e}")

if __name__ == "__main__":
    run_bot()
