import os
import time
import json
import requests
import io
import gspread
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# =======================================================
# 💎 CONFIGURATION
# =======================================================

IG_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")
DROPSHIPPING_SHEET_ID = "1lrn-plbxc7w4wHBLYoCfP_UYIP6EVJbj79IdBUP5sgs"

# Brand IDs
BRAND_CONFIG = {
    "URBAN GLINT": { "ig_id": "17841479492205083", "fb_id": "892844607248221" },
    "GRAND ORBIT": { "ig_id": "17841479516066757", "fb_id": "817698004771102" },
    "ROYAL NEXUS": { "ig_id": "17841479056452004", "fb_id": "854486334423509" },
    "LUXIVIBE": { "ig_id": "17841479492205083", "fb_id": "777935382078740" },
    "DIAMOND DICE": { "ig_id": "17841478369307404", "fb_id": "873607589175898" },
    # Add more accounts here...
}

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# =======================================================
# 🧠 SMART TIME LOGIC (INDIA TIME)
# =======================================================

def get_ist_time():
    # GitHub servers UTC ma hoy, apanene +5:30 karia etle India time male
    utc_now = datetime.utcnow()
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    return ist_now

def is_time_to_post(sheet_date_str, sheet_time_str):
    try:
        # Current India Time
        ist_now = get_ist_time()
        
        # Sheet Data Parsing (Date: 20/12/2025, Time: 12:14)
        # Assuming Date format DD/MM/YYYY and Time HH:MM (24 hour)
        scheduled_dt_str = f"{sheet_date_str} {sheet_time_str}"
        scheduled_dt = datetime.strptime(scheduled_dt_str, "%d/%m/%Y %H:%M")
        
        print(f"      🕒 Scheduled: {scheduled_dt} | Current IST: {ist_now.strftime('%Y-%m-%d %H:%M')}")

        # Check Logic
        if ist_now >= scheduled_dt:
            return True # Time thai gayo che!
        else:
            return False # Haju vaar che
    except ValueError:
        print(f"      ⚠️ Date/Time Format Error! (Use DD/MM/YYYY and HH:MM)")
        return False # Format khotu hoy to risk nahi Levanu

# =======================================================
# ⚙️ SYSTEM CORE
# =======================================================

def get_services():
    creds_json = os.environ.get("GCP_CREDENTIALS")
    if not creds_json: return None, None
    try:
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(DROPSHIPPING_SHEET_ID).sheet1
        drive_service = build('drive', 'v3', credentials=creds)
        return sheet, drive_service
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None, None

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
# 🚀 MAIN EXECUTION (SMART MODE)
# =======================================================

def start_bot():
    print("-" * 50)
    print(f"⏰ DROPSHIPPING SMART-BOT STARTED (IST MODE)...")
    
    sheet, drive_service = get_services()
    if not sheet: return

    try:
        records = sheet.get_all_records()
        headers = sheet.row_values(1)
        try: col_status = headers.index("Status") + 1
        except: col_status = 12 
    except: return

    count = 0

    for i, row in enumerate(records, start=2):
        status = str(row.get("Status", "")).strip()
        
        # Only check rows that are PENDING
        if status == "Pending":
            brand = str(row.get("Account Name", "")).strip().upper()
            
            # 👇 NEW: Check Time & Date
            sheet_date = str(row.get("Date", "")).strip() # Column A
            sheet_time = str(row.get("Schedule_Time", "")).strip() # Column C
            
            print(f"\n👉 Checking Row {i} for {brand}...")

            if is_time_to_post(sheet_date, sheet_time):
                # Time thai gayo che! Have upload karo.
                if brand in BRAND_CONFIG:
                    ig_id = BRAND_CONFIG[brand].get("ig_id")
                    fb_id = BRAND_CONFIG[brand].get("fb_id")
                    platform = str(row.get("Platform", "")).strip()
                    
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
                            print(f"      ✅ POSTED SUCCESSFULLY!")
                            count += 1
                            time.sleep(10)
                else:
                    print(f"      ⚠️ Brand '{brand}' Config ma nathi!")
            else:
                # Time nathi thayo
                print(f"      ⏳ WAIT: Haju time nathi thayo. Skipping.")

    if count == 0:
        print("\n💤 No posts due right now.")
    else:
        print(f"🎉 Processed {count} videos.")

if __name__ == "__main__":
    start_bot()
