import os
import time
import json
import requests
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# =======================================================
# 💎 ULTIMATE CONFIGURATION (તમારો ડેટા અહીં સેટ છે)
# =======================================================

# 1. AUTH TOKEN (Expires Feb 2026) - મેં તમારો નવો ટોકન અહીં સેટ કર્યો છે
IG_ACCESS_TOKEN = "EAAbqjYTHyh0BQDtDRgZB5fR8lxFUdObqebzMv3rOm38RhYmOVZBHkzZATgiQMEbpoYok3xrj9l2oFzX0w07uBEkzrZBwbz5vVIrAewxR3ymPEfI2lcgtIkkfzhDcmBPCKRORfJnqV3aO1rBBZBzsRqggnHTAGJML3gspbPsuDrtJFxlhEcs1oZAngUIRrmpk0z"

# 2. BRAND DATABASE (The Super Brain)
# Bot અહીંથી જોશે કે કઈ બ્રાન્ડનું કામ કરવાનું છે.
BRAND_CONFIG = {
    "PEARL VERSE": {
        "fb_id": "927694300421135",       # ✅ Facebook ID (Done)
        "ig_id": "PLACE_YOUR_178_ID_HERE" # ⚠️ Instagram ID (178...) અહીં નાખો
    },
    "EMERALD EDGE": {
        "fb_id": "929305353594436",
        "ig_id": "PLACE_YOUR_178_ID_HERE"
    },
    "DIAMOND DICE": {
        "fb_id": "873607589175898",
        "ig_id": "PLACE_YOUR_178_ID_HERE"
    },
    "URBAN GLINT": {
        "fb_id": "892844607248221",
        "ig_id": "PLACE_YOUR_178_ID_HERE"
    },
    "OPUS ELITE": {
        "fb_id": "938320336026787",
        "ig_id": "PLACE_YOUR_178_ID_HERE"
    }
}

# 3. Google Sheet Name
SHEET_NAME = "Content"

# =======================================================
# ⚙️ SYSTEM CORE (Do Not Touch)
# =======================================================

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_sheet_connection():
    """Connects to Google Sheet via Local File or GitHub Secret"""
    # Try GitHub Secret first
    if os.environ.get("GOOGLE_SHEETS_CREDENTIALS"):
        print("🔐 Auth: Using GitHub Secrets...")
        creds_dict = json.loads(os.environ.get("GOOGLE_SHEETS_CREDENTIALS"))
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(creds).open(SHEET_NAME).sheet1

    # Try Local File
    elif os.path.exists("gkey.json"):
        print("📂 Auth: Using Local 'gkey.json'...")
        creds = Credentials.from_service_account_file("gkey.json", scopes=SCOPES)
        return gspread.authorize(creds).open(SHEET_NAME).sheet1
    
    else:
        print("❌ CRITICAL ERROR: No Credentials Found (Missing gkey.json or Secret)")
        return None

# =======================================================
# 🔧 SMART FUNCTIONS
# =======================================================

def convert_drive_link(url):
    """Google Drive Link -> Direct Download Link"""
    if "drive.google.com" in url and "/d/" in url:
        try:
            file_id = url.split('/d/')[1].split('/')[0]
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        except:
            return url
    return url

def upload_to_facebook(brand_name, fb_page_id, video_url, description):
    print(f"      🔵 Facebook Upload ({brand_name})...")
    
    if not fb_page_id or "PLACE_YOUR" in fb_page_id:
        print(f"      ⚠️ Skipping: Facebook ID missing for {brand_name}")
        return False

    url = f"https://graph.facebook.com/v18.0/{fb_page_id}/videos"
    payload = {
        "file_url": video_url,
        "description": description,
        "access_token": IG_ACCESS_TOKEN 
    }
    
    try:
        r = requests.post(url, data=payload)
        result = r.json()
        if "id" in result:
            print(f"      ✅ Facebook Success! ID: {result['id']}")
            return True
        else:
            print(f"      ❌ Facebook Error: {result}")
            return False
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return False

def upload_to_instagram(brand_name, ig_user_id, video_url, caption):
    print(f"      📸 Instagram Upload ({brand_name})...")
    
    if not ig_user_id or "PLACE_YOUR" in ig_user_id:
        print(f"      ⚠️ Skipping: Instagram ID missing for {brand_name}")
        return False

    domain = "https://graph.facebook.com/v18.0"
    
    # 1. Create Container
    url_create = f"{domain}/{ig_user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": IG_ACCESS_TOKEN
    }
    
    try:
        r = requests.post(url_create, data=payload)
        if "id" not in r.json():
            print(f"      ❌ IG Container Error: {r.json()}")
            return False
            
        creation_id = r.json()["id"]
        print(f"      ⏳ Waiting for Instagram Processing (30s)...")
        time.sleep(30)
        
        # 2. Publish
        url_pub = f"{domain}/{ig_user_id}/media_publish"
        r_pub = requests.post(url_pub, data={"creation_id": creation_id, "access_token": IG_ACCESS_TOKEN})
        
        if "id" in r_pub.json():
            print(f"      ✅ Instagram Success! ID: {r_pub.json()['id']}")
            return True
        else:
            print(f"      ❌ IG Publish Error: {r_pub.json()}")
            return False
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return False

# =======================================================
# 🚀 MAIN EXECUTION
# =======================================================

def start_bot():
    print("\n🤖 MULTI-BRAND MASTER BOT STARTED...")
    print("-" * 50)
    
    sheet = get_sheet_connection()
    if not sheet: return

    try:
        records = sheet.get_all_records()
        headers = sheet.row_values(1)
        col_status = headers.index("Status") + 1
    except Exception as e:
        print(f"❌ Error Reading Sheet: {e}")
        return

    processed_count = 0

    for i, row in enumerate(records, start=2):
        status = str(row.get("Status", "")).strip().upper()
        
        if status == "PENDING":
            # 1. Get Details
            brand = str(row.get("Brand_Name", "")).strip().upper()
            platform = str(row.get("Platform", "")).strip().upper()
            
            print(f"\n👉 Found Task Row {i}: {row.get('Title_Hook', 'No Title')} | Brand: {brand}")

            # 2. Check if Brand exists in our Database
            if brand not in BRAND_CONFIG:
                print(f"      ⚠️ Warning: Brand '{brand}' not found in BRAND_CONFIG settings. Skipping.")
                continue
            
            # 3. Get IDs for this specific brand
            ids = BRAND_CONFIG[brand]
            fb_id = ids["fb_id"]
            ig_id = ids["ig_id"]
            
            # 4. Prepare Data
            video_url = convert_drive_link(row.get("Video_URL", ""))
            caption = f"{row.get('Title_Hook', '')}\n.\n{row.get('Caption_Hashtags', '')}"
            
            success = False
            
            # 5. Execute based on Platform
            if platform == "FACEBOOK":
                success = upload_to_facebook(brand, fb_id, video_url, caption)
                
            elif platform == "INSTAGRAM":
                success = upload_to_instagram(brand, ig_id, video_url, caption)
            
            elif platform == "YOUTUBE":
                print("      ⚠️ YouTube requires separate login (Skipping).")
            
            else:
                print(f"      ❓ Unknown Platform: {platform}")

            # 6. Update Sheet
            if success:
                sheet.update_cell(i, col_status, "POSTED")
                print(f"      📝 Sheet Updated: POSTED")
                processed_count += 1

    if processed_count == 0:
        print("\n💤 No PENDING tasks found. Bot is resting.")
    else:
        print(f"\n🎉 Job Done! Total Uploads: {processed_count}")

if __name__ == "__main__":
    start_bot()
