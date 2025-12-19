import os
import time
import json
import requests
import gspread
from google.oauth2.service_account import Credentials

# =======================================================
# 💎 ULTIMATE CONFIGURATION (Extracted from your GitHub File)
# =======================================================

# 1. AUTH TOKEN (GitHub Secret માંથી લેશે)
# જો લોકલ ટેસ્ટ કરતા હોવ, તો અહીં ટોકન લખી શકો છો.
IG_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")

# 2. BRAND DATABASE (તમારી ફાઈલ મુજબના IDs)
BRAND_CONFIG = {
    "PEARL VERSE": {
        "ig_id": "17841478822408000"  # 
    },
    "DIAMOND DICE": {
        "ig_id": "17841478369307404"  # 
    },
    "EMERALD EDGE": {
        "ig_id": "17841478369307404"  #  (Note: Same as Diamond Dice in your file)
    },
    "URBAN GLINT": {
        "ig_id": "17841479492205083"  # 
    },
    "LUXIVIBE": {
        "ig_id": "17841479492205083"  #  (Note: Same as Urban Glint in your file)
    },
    "GRAND ORBIT": {
        "ig_id": "17841479516066757"  # 
    },
    "OPUS ELITE": {
        "ig_id": "17841479493645419"  # 
    },
    "ROYAL NEXUS": {
        "ig_id": "17841479056452004"  # 
    }
}

# 3. Google Sheet Name & ID
# તમારી ફાઈલમાં SPREADSHEET_ID env variable વપરાય છે 
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID") 

# =======================================================
# ⚙️ SYSTEM CORE
# =======================================================

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_sheet_connection():
    """Connects to Google Sheet via GitHub Secret OR Local File"""
    
    # Priority 1: GitHub Secret (GCP_CREDENTIALS as per your file [cite: 31])
    creds_json = os.environ.get("GCP_CREDENTIALS") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    
    if creds_json:
        print("🔐 Auth: Connecting via GitHub Secrets...")
        try:
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            client = gspread.authorize(creds)
            
            # Open by ID if available (Best practice from your file [cite: 32])
            if SPREADSHEET_ID:
                return client.open_by_key(SPREADSHEET_ID).sheet1
            else:
                return client.open("Content").sheet1
        except Exception as e:
            print(f"❌ Secret Error: {e}")
            return None

    # Priority 2: Local File (Testing)
    elif os.path.exists("gkey.json"):
        print("📂 Auth: Connecting via Local 'gkey.json'...")
        creds = Credentials.from_service_account_file("gkey.json", scopes=SCOPES)
        client = gspread.authorize(creds)
        if SPREADSHEET_ID:
            return client.open_by_key(SPREADSHEET_ID).sheet1
        return client.open("Content").sheet1
    
    else:
        print("❌ CRITICAL ERROR: No Credentials Found.")
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

def upload_to_instagram(brand_name, ig_user_id, video_url, caption):
    print(f"      📸 Instagram Upload ({brand_name})...")
    
    if not ig_user_id:
        print(f"      ⚠️ Skipping: Instagram ID missing for {brand_name}")
        return False
        
    if not IG_ACCESS_TOKEN:
        print("      ❌ Error: FB_ACCESS_TOKEN not found in environment.")
        return False

    domain = "https://graph.facebook.com/v19.0" # Updated to v19.0 per your file [cite: 38]
    
    # 1. Create Container (Reels)
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
        print(f"      ⏳ Waiting for Instagram Processing (45s)...")
        time.sleep(45) # Increased wait time for safety
        
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
    print("\n🤖 GITHUB AUTOMATION BOT STARTED (Based on Uploaded File)...")
    print("-" * 50)
    
    sheet = get_sheet_connection()
    if not sheet: return

    try:
        records = sheet.get_all_records()
        headers = sheet.row_values(1)
        # Dynamic Column Finding
        try:
            col_status = headers.index("Status") + 1
        except:
            # Fallback based on your file logic (Col 5 / E is common) [cite: 7]
            col_status = 5 
    except Exception as e:
        print(f"❌ Error Reading Sheet: {e}")
        return

    processed_count = 0

    for i, row in enumerate(records, start=2):
        # Flexible Key Access (Handle 'Account Name' or 'Brand_Name')
        brand = str(row.get("Brand_Name") or row.get("Account_Name") or row.get("Account Name", "")).strip().upper()
        status = str(row.get("Status", "")).strip().upper()
        platform = str(row.get("Platform", "")).strip().upper()
        
        if status == "PENDING":
            # બ્રાન્ડ ડેટાબેઝ ચેક કરો
            if brand in BRAND_CONFIG:
                print(f"\n👉 Processing Row {i}: {row.get('Title_Hook') or row.get('Title')} | Brand: {brand}")
                
                ig_id = BRAND_CONFIG[brand]["ig_id"]
                
                # Link handling
                video_url = convert_drive_link(row.get("Video_URL") or row.get("Video Link", ""))
                
                # Caption handling
                title = row.get("Title_Hook") or row.get("Title", "")
                hashtags = row.get("Caption_Hashtags") or row.get("Hashtags", "")
                caption = f"{title}\n.\n{hashtags}"
                
                success = False
                
                if "INSTAGRAM" in platform:
                    success = upload_to_instagram(brand, ig_id, video_url, caption)
                
                elif "FACEBOOK" in platform:
                     # જો FB અને Insta લિંક હોય તો આ જ ID થી ચાલી શકે, નહીંતર પેજ ID જોઈએ
                     # તમારી ફાઈલમાં પેજ ID મળ્યા નથી, એટલે IG મેથડ જ વાપરીએ છીએ
                     success = upload_to_instagram(brand, ig_id, video_url, caption)
                
                else:
                    print(f"      ⚠️ Platform '{platform}' skipped in this run.")

                if success:
                    sheet.update_cell(i, col_status, "POSTED")
                    print(f"      📝 Sheet Updated: POSTED")
                    processed_count += 1
            else:
                 # જો બ્રાન્ડ લિસ્ટમાં ન હોય
                 if brand:
                    print(f"⚠️ Brand '{brand}' not in config. Available: {list(BRAND_CONFIG.keys())}")

    if processed_count == 0:
        print("\n💤 No PENDING tasks found for configured brands.")
    else:
        print(f"\n🎉 Job Done! Total Uploads: {processed_count}")

if __name__ == "__main__":
    start_bot()
