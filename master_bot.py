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
# 💎 CONFIGURATION (DROPSHIPPING)
# =======================================================

# 1. AUTH TOKEN
IG_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")

# 2. DROPSHIPPING SHEET ID
DROPSHIPPING_SHEET_ID = "1lrn-plbxc7w4wHBLYoCfP_UYIP6EVJbj79IdBUP5sgs"

# 3. BRAND CONFIG (All IDs Fixed & Verified)
BRAND_CONFIG = {
    "URBAN GLINT": { 
        "ig_id": "17841479492205083", 
        "fb_id": "892844607248221" 
    },
    "GRAND ORBIT": { 
        "ig_id": "17841479516066757", 
        "fb_id": "817698004771102" 
    },
    "ROYAL NEXUS": { 
        "ig_id": "17841479056452004", 
        "fb_id": "854486334423509" 
    },
    "LUXIVIBE": { 
        "ig_id": "17841478140648372",  # ✅ Fixed (Saachu ID)
        "fb_id": "777935382078740" 
    },
    "DIAMOND DICE": { 
        "ig_id": "17841478369307404", 
        "fb_id": "873607589175898" 
    },
    "PEARL VERSE": { 
        "ig_id": "17841478822408000", 
        "fb_id": "927694300421135" 
    },
    "OPUS ELITE": { 
        "ig_id": "17841479493645419", 
        "fb_id": "938320336026787" 
    }
}

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# =======================================================
# 🧠 SNIPER TIME LOGIC (SMART WAIT + AM/PM)
# =======================================================

def get_ist_time():
    utc_now = datetime.utcnow()
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    return ist_now

def check_time_and_wait(sheet_date_str, sheet_time_str):
    """
    Checks time. If < 5 mins remain, it WAITS (Sleeps).
    """
    try:
        ist_now = get_ist_time()
        
        # Clean Inputs
        date_clean = str(sheet_date_str).strip()
        time_clean = str(sheet_time_str).strip().upper()
        
        if not date_clean or not time_clean: return False

        full_time_str = f"{date_clean} {time_clean}"
        
        # Parse Time (With AM/PM support)
        try:
            scheduled_dt = datetime.strptime(full_time_str, "%d/%m/%Y %I:%M %p")
        except ValueError:
            try:
                scheduled_dt = datetime.strptime(full_time_str, "%d/%m/%Y %I:%M%p")
            except ValueError:
                # Fallback
                scheduled_dt = datetime.strptime(full_time_str, "%d/%m/%Y %H:%M")

        # Time Difference
        time_diff = (scheduled_dt - ist_now).total_seconds()
        
        print(f"      🕒 Scheduled: {scheduled_dt.strftime('%H:%M')} | Now: {ist_now.strftime('%H:%M')} | Gap: {int(time_diff)}s")

        # LOGIC 1: Time Thai Gayo Che (Already Late or Exact)
        if time_diff <= 0:
            return True 
        
        # LOGIC 2: SNIPER WAIT (Within 5 Mins)
        elif 0 < time_diff <= 300:
            print(f"      👀 TARGET LOCKED! Waiting {int(time_diff)}s to hit exact time...")
            time.sleep(time_diff + 2) 
            print("      🔫 BOOM! Exact Time. Uploading...")
            return True
            
        # LOGIC 3: Too Early
        else:
            print(f"      💤 Too early. Sleeping.")
            return False

    except ValueError:
        print(f"      ⚠️ Date/Time Error.")
        return False

# =======================================================
# ⚙️ SYSTEM CORE
# =======================================================

def get_services():
    creds_json = os.environ.get("GCP_CREDENTIALS")
    if not creds_json: return None, None
    try:
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
        client = gspread.authorize(creds)
        
        # Open Dropshipping Sheet
        try:
            sheet = client.open_by_key(DROPSHIPPING_SHEET_ID).sheet1
            print("✅ Dropshipping Sheet Connected.")
        except:
            print("❌ Sheet ID Invalid.")
            return None, None

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

def upload_to_instagram_resumable(brand_name, ig_user_id, file_path, caption):
    print(f"      📸 Instagram Upload ({brand_name})...")
    if not ig_user_id: 
        print(f"      ⚠️ No IG ID for {brand_name}")
        return False
    domain = "https://graph.facebook.com/v19.0"
    try:
        url = f"{domain}/{ig_user_id}/media"
        params = { "upload_type": "resumable", "media_type": "REELS", "caption": caption, "access_token": IG_ACCESS_TOKEN }
        init = requests.post(url, params=params).json()
        if "uri" not in init: return False
        with open(file_path, "rb") as f:
            headers = { "Authorization": f"OAuth {IG_ACCESS_TOKEN}", "offset": "0", "file_size": str(os.path.getsize(file_path)) }
            requests.post(init["uri"], data=f, headers=headers)
        time.sleep(60)
        pub = requests.post(f"{domain}/{ig_user_id}/media_publish", params={"creation_id": init["id"], "access_token": IG_ACCESS_TOKEN})
        return "id" in pub.json()
    except: return False

def upload_to_facebook(brand_name, fb_page_id, file_path, caption):
    print(f"      📘 Facebook Upload ({brand_name})...")
    if not fb_page_id: return False
    try:
        url = f"https://graph.facebook.com/v19.0/{fb_page_id}/videos"
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
    print(f"⏰ DROPSHIPPING SNIPER-BOT STARTED...")
    
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
        
        if status == "Pending":
            # Dropshipping uses 'Date' column
            sheet_date = str(row.get("Date", "")).strip()
            sheet_time = str(row.get("Schedule_Time", "")).strip()
            brand = str(row.get("Account Name", "")).strip().upper()

            print(f"\n👉 Checking Row {i}: {brand}")

            # SNIPER CHECK
            if check_time_and_wait(sheet_date, sheet_time):
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
                            ig_success = upload_to_instagram_resumable(brand, ig_id, local_file, final_caption)
                        if "Facebook" in platform:
                            fb_success = upload_to_facebook(brand, fb_id, local_file, final_caption)
                        
                        if os.path.exists(local_file): os.remove(local_file)

                        if ig_success or fb_success:
                            sheet.update_cell(i, col_status, "POSTED")
                            print(f"      ✅ Success!")
                            count += 1
                            time.sleep(10)
            else:
                pass 

    if count == 0:
        print("💤 No posts ready.")
    else:
        print(f"🎉 Processed {count} videos.")

if __name__ == "__main__":
    start_bot()
