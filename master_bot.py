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

IG_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")

# 👇 TAMARU SHEET ID (Confirm karjo aa j che)
DROPSHIPPING_SHEET_ID = "1lrn-plbxc7w4wHBLYOcFP_UYIP6EVJbj79IdBUP5sgs"

BRAND_CONFIG = {
    "URBAN GLINT": { "ig_id": "17841479492205083", "fb_id": "892844607248221" },
    "GRAND ORBIT": { "ig_id": "17841479516066757", "fb_id": "817698004771102" },
    "ROYAL NEXUS": { "ig_id": "17841479056452004", "fb_id": "854486334423509" },
    "LUXIVIBE": { "ig_id": "17841479492205083", "fb_id": "777935382078740" },
    "DIAMOND DICE": { "ig_id": "17841478369307404", "fb_id": "873607589175898" },
}

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# =======================================================
# ⚙️ SYSTEM CORE (DIAGNOSTIC MODE)
# =======================================================

def get_services():
    print("\n" + "="*50)
    print("🕵️ CHECKING CREDENTIALS...")
    
    creds_json = os.environ.get("GCP_CREDENTIALS")
    if not creds_json: 
        print("❌ GCP Credentials Not Found!")
        return None, None
    
    try:
        # 👇 AA JADU CHE: Ahiya saachu email print thase
        creds_dict = json.loads(creds_json)
        actual_email = creds_dict.get("client_email", "Unknown")
        
        print(f"🔑 BOT IS USING THIS EMAIL:  {actual_email}")
        print("👉 (Aa Email ne Sheet ma 'Editor' banavo!)")
        print("="*50 + "\n")

        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        
        # Open Sheet
        sheet = client.open_by_key(DROPSHIPPING_SHEET_ID).sheet1
        print("✅ CONNECTION SUCCESSFUL! (Sheet Mali Gai)")

        drive_service = build('drive', 'v3', credentials=creds)
        return sheet, drive_service
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print(f"⚠️ Haju pan permission nathi! Upar je '{actual_email}' chapyu te add karo.")
        return None, None

# =======================================================
# 🔧 UPLOAD FUNCTIONS
# =======================================================

def download_video_securely(drive_service, drive_url):
    print("      ⬇️ Downloading video...")
    temp_filename = "temp_drop_video.mp4"
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
    except: return None

def upload_to_instagram(ig_id, file_path, caption):
    print(f"      📸 Uploading to Instagram...")
    if not ig_id: return False
    domain = "https://graph.facebook.com/v19.0"
    try:
        url = f"{domain}/{ig_id}/media"
        params = { "upload_type": "resumable", "media_type": "REELS", "caption": caption, "access_token": IG_ACCESS_TOKEN }
        init = requests.post(url, params=params).json()
        if "uri" not in init: return False
        
        with open(file_path, "rb") as f:
            headers = { "Authorization": f"OAuth {IG_ACCESS_TOKEN}", "offset": "0", "file_size": str(os.path.getsize(file_path)) }
            requests.post(init["uri"], data=f, headers=headers)
        
        time.sleep(60)
        pub = requests.post(f"{domain}/{ig_id}/media_publish", params={"creation_id": init["id"], "access_token": IG_ACCESS_TOKEN})
        return "id" in pub.json()
    except: return False

def upload_to_facebook(fb_id, file_path, caption):
    print(f"      📘 Uploading to Facebook...")
    if not fb_id: return False
    try:
        url = f"https://graph.facebook.com/v19.0/{fb_id}/videos"
        params = { "description": caption, "access_token": IG_ACCESS_TOKEN }
        with open(file_path, "rb") as f:
            r = requests.post(url, params=params, files={"source": f})
        return "id" in r.json()
    except: return False

# =======================================================
# 🚀 MAIN EXECUTION
# =======================================================

def start_bot():
    print("-" * 50)
    print(f"⏰ DROPSHIPPING BOT STARTED...")
    
    sheet, drive_service = get_services()
    if not sheet: return

    try:
        records = sheet.get_all_records()
        headers = sheet.row_values(1)
        try: col_status = headers.index("Status") + 1
        except: col_status = 12 
    except Exception as e:
        print(f"❌ Error Reading Data: {e}")
        return

    count = 0

    for i, row in enumerate(records, start=2):
        brand = str(row.get("Account Name", "")).strip().upper()
        status = str(row.get("Status", "")).strip()
        platform = str(row.get("Platform", "")).strip()
        
        if status == "Pending": 
            if brand in BRAND_CONFIG:
                print(f"\n👉 Processing: {brand} | Platform: {platform}")
                
                ig_id = BRAND_CONFIG[brand].get("ig_id")
                fb_id = BRAND_CONFIG[brand].get("fb_id")
                
                video_url = row.get("Video_Drive_Link", "")
                caption_text = row.get("Caption", "")
                hashtags = row.get("Hastag", "")
                final_caption = f"{caption_text}\n.\n{hashtags}"
                
                local_file = download_video_securely(drive_service, video_url)
                
                if local_file:
                    ig_success = False
                    fb_success = False

                    if "Instagram" in platform:
                        ig_success = upload_to_instagram(ig_id, local_file, final_caption)
                    if "Facebook" in platform:
                        fb_success = upload_to_facebook(fb_id, local_file, final_caption)
                    
                    if os.path.exists(local_file): os.remove(local_file)

                    if ig_success or fb_success:
                        sheet.update_cell(i, col_status, "POSTED")
                        print(f"      ✅ Success!")
                        count += 1
                        time.sleep(10)

    if count == 0:
        print("💤 No tasks found.")
    else:
        print(f"🎉 Processed {count} videos.")

if __name__ == "__main__":
    start_bot()
