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
        "ig_id": "17841478140648372", 
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
        
        # 👇 UPDATED DATE PARSING LOGIC (Handles US & Indian Formats)
        formats_to_try = [
            "%d/%m/%Y %I:%M %p",  # 21/12/2025 2:30 PM (Indian)
            "%m/%d/%Y %I:%M %p",  # 12/21/2025 2:30 PM (US Style - Sheet Default)
            "%d/%m/%Y %I:%M%p",   # 21/12/2025 2:30PM
            "%m/%d/%Y %I:%M%p",   # 12/21/2025 2:30PM
            "%d/%m/%Y %H:%M",     # 24 Hour format
            "%Y-%m-%d %H:%M:%S"   # ISO Format
        ]
        
        scheduled_dt = None
        for fmt in formats_to_try:
            try:
                scheduled_dt = datetime.strptime(full_time_str, fmt)
                break # Match found, stop checking
            except ValueError:
                continue
                
        if not scheduled_dt:
            print(f"      ⚠️ Date Format Unknown: {full_time_str}")
            return False

        # Time Difference
        time_diff = (scheduled_dt - ist_now).total_seconds()
        
        print(f"      🕒 Scheduled: {scheduled_dt.strftime('%d/%m %H:%M')} | Now: {ist_now.strftime('%d/%m %H:%M')} | Gap: {int(time_diff)}s")

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

    except Exception as e:
        print(f"      ⚠️ Date/Time Error: {e}")
        return False

# =======================================================
# ⚙️ SYSTEM CORE & ANALYTICS
# =======================================================

def get_services():
    creds_json = os.environ.get("GCP_CREDENTIALS")
    if not creds_json: return None, None
    try:
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
        client = gspread.authorize(creds)
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

def get_facebook_metrics(video_id):
    """Fetches Likes for FB Video"""
    try:
        url = f"https://graph.facebook.com/v19.0/{video_id}?fields=likes.summary(true)&access_token={IG_ACCESS_TOKEN}"
        r = requests.get(url).json()
        likes = r.get("likes", {}).get("summary", {}).get("total_count", 0)
        return likes
    except: return 0

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

# =======================================================
# 🔧 UPLOAD FUNCTIONS (WITH TIMER & LINK)
# =======================================================

def upload_to_instagram_resumable(brand_name, ig_user_id, file_path, caption):
    print(f"      📸 Instagram Upload ({brand_name})...")
    start_t = time.time()
    if not ig_user_id: 
        print(f"      ⚠️ No IG ID for {brand_name}")
        return False, "", 0
    
    domain = "https://graph.facebook.com/v19.0"
    try:
        url = f"{domain}/{ig_user_id}/media"
        params = { "upload_type": "resumable", "media_type": "REELS", "caption": caption, "access_token": IG_ACCESS_TOKEN }
        init = requests.post(url, params=params).json()
        
        if "uri" not in init: return False, "", 0
        
        with open(file_path, "rb") as f:
            headers = { "Authorization": f"OAuth {IG_ACCESS_TOKEN}", "offset": "0", "file_size": str(os.path.getsize(file_path)) }
            requests.post(init["uri"], data=f, headers=headers)
        
        time.sleep(60)
        pub = requests.post(f"{domain}/{ig_user_id}/media_publish", params={"creation_id": init["id"], "access_token": IG_ACCESS_TOKEN}).json()
        
        end_t = time.time()
        duration = int(end_t - start_t)
        
        if "id" in pub:
            try:
                # Fetch Shortcode for Link
                r_get = requests.get(f"{domain}/{pub['id']}?fields=shortcode&access_token={IG_ACCESS_TOKEN}").json()
                shortcode = r_get.get("shortcode", "")
                link = f"https://www.instagram.com/reel/{shortcode}/" if shortcode else f"ID:{pub['id']}"
            except: link = "Link Error"
            return True, link, duration
        return False, "", 0
    except: return False, "", 0

def upload_to_facebook(brand_name, fb_page_id, file_path, caption):
    print(f"      📘 Facebook Upload ({brand_name})...")
    start_t = time.time()
    if not fb_page_id: return False, "", 0
    
    try:
        url = f"https://graph.facebook.com/v19.0/{fb_page_id}/videos"
        params = { "description": caption, "access_token": IG_ACCESS_TOKEN }
        with open(file_path, "rb") as f:
            r = requests.post(url, params=params, files={"source": f}).json()
        
        end_t = time.time()
        duration = int(end_t - start_t)
        
        if "id" in r:
            link = f"https://www.facebook.com/{fb_page_id}/videos/{r['id']}/"
            return True, link, duration
        return False, "", 0
    except: return False, "", 0

# =======================================================
# 🚀 MAIN EXECUTION (WITH FULL DATA ENTRY)
# =======================================================

def start_bot():
    print("-" * 50)
    print(f"⏰ DROPSHIPPING SUPER-BOT STARTED...")
    
    sheet, drive_service = get_services()
    if not sheet: return

    try:
        records = sheet.get_all_records()
        headers = sheet.row_values(1)
        # Dynamic Column Finding
        try: col_status = headers.index("Status") + 1
        except: col_status = 12 
        try: col_link = headers.index("Link") + 1
        except: col_link = 0
        try: col_duration = headers.index("Upload_Duration") + 1
        except: col_duration = 0
        try: col_views = headers.index("Views") + 1
        except: col_views = 0
        try: col_likes = headers.index("Likes") + 1
        except: col_likes = 0
        
    except: return

    count = 0

    # PART 1: UPLOAD
    for i, row in enumerate(records, start=2):
        status = str(row.get("Status", "")).strip()
        
        if status == "Pending":
            sheet_date = str(row.get("Date", "")).strip()
            sheet_time = str(row.get("Schedule_Time", "")).strip()
            brand = str(row.get("Account Name", "")).strip().upper()

            print(f"\n👉 Checking Row {i}: {brand}")

            if check_time_and_wait(sheet_date, sheet_time):
                if brand in BRAND_CONFIG:
                    ig_id = BRAND_CONFIG[brand].get("ig_id")
                    fb_id = BRAND_CONFIG[brand].get("fb_id")
                    platform = str(row.get("Platform", "")).strip()
                    
                    video_url = row.get("Video_Drive_Link", "")
                    
                    # ✅ FETCH FULL DETAILS (Title + Desc + Caption + Hashtags)
                    title = str(row.get("Title", "")).strip()
                    desc = str(row.get("Description", "")).strip()
                    caption_text = str(row.get("Caption", "")).strip()
                    hashtags = str(row.get("Hastag", "")).strip()
                    
                    # Construct Final Caption intelligently
                    parts = []
                    if title: parts.append(title)
                    if desc: parts.append(desc)
                    if caption_text: parts.append(caption_text)
                    if hashtags: parts.append(f".\n{hashtags}")
                    
                    final_caption = "\n\n".join(parts)
                    
                    local_file = download_video_securely(drive_service, video_url)
                    
                    if local_file:
                        success = False
                        final_link = ""
                        duration = 0

                        if "Instagram" in platform:
                            s, l, d = upload_to_instagram_resumable(brand, ig_id, local_file, final_caption)
                            if s: 
                                success = True
                                final_link = l
                                duration = d
                                
                        if "Facebook" in platform:
                            s, l, d = upload_to_facebook(brand, fb_id, local_file, final_caption)
                            if s:
                                success = True
                                final_link = l # If both, FB link overwrites IG link in sheet logic
                                duration = d

                        if os.path.exists(local_file): os.remove(local_file)

                        if success:
                            sheet.update_cell(i, col_status, "POSTED")
                            
                            if col_link > 0: 
                                sheet.update_cell(i, col_link, final_link)
                            if col_duration > 0: 
                                sheet.update_cell(i, col_duration, f"{duration} sec")
                                
                            print(f"      ✅ Success! Link: {final_link}")
                            count += 1
                            time.sleep(10)
            else:
                pass 

    # PART 2: ANALYTICS (Last 20)
    print("\n📊 Checking Analytics...")
    records = sheet.get_all_records()
    check_limit = 0
    for i in range(len(records), 1, -1):
        if check_limit >= 20: break
        
        row = records[i-2]
        status = str(row.get("Status", "")).strip()
        link = str(row.get("Link", "")).strip()
        
        if status == "POSTED" and link != "":
            likes = 0
            if "facebook.com" in link:
                try: vid_id = link.split("/videos/")[1].replace("/","")
                except: vid_id = ""
                if vid_id: likes = get_facebook_metrics(vid_id)
            
            if likes > 0:
                if col_likes > 0: sheet.update_cell(i, col_likes, likes)
                print(f"   🔄 Updated Likes Row {i}: {likes}")
            check_limit += 1

    if count == 0:
        print("💤 No new posts. Analytics updated.")
    else:
        print(f"🎉 Processed {count} videos.")

if __name__ == "__main__":
    start_bot()
