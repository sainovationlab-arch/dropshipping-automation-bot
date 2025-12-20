import os
import time
import json
import requests
import io
import gspread
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2.credentials import Credentials as UserCredentials
from google.auth.transport.requests import Request

# =======================================================
# 💎 CONFIGURATION (IG + FB + YOUTUBE)
# =======================================================

# 1. AUTH TOKEN (GitHub Secret)
IG_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")

# 2. YOUTUBE CREDENTIALS (Loaded from GitHub Secret)
YOUTUBE_CREDENTIALS_JSON = os.environ.get("YOUTUBE_CREDENTIALS")
YOUTUBE_CONFIG = json.loads(YOUTUBE_CREDENTIALS_JSON) if YOUTUBE_CREDENTIALS_JSON else {}

# 3. BRAND DATABASE (All IDs Updated & Verified)
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
        "ig_id": "17841478817585793", 
        "fb_id": "929305353594436" 
    },
    "URBAN GLINT": { 
        "ig_id": "17841479492205083", 
        "fb_id": "892844607248221" 
    },
    "LUXIVIBE": { 
        "ig_id": "17841478140648372", 
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

# 4. SHEET SETTINGS
SPREADSHEET_ID = "1Kdd01UAt5rz-9VYDhjFYL4Dh35gaofLipbsjyl8u8hY"
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
        
        if not date_clean or not time_clean:
            return False

        full_time_str = f"{date_clean} {time_clean}"
        
        # 👇 AM/PM Logic
        try:
            scheduled_dt = datetime.strptime(full_time_str, "%d/%m/%Y %I:%M %p")
        except ValueError:
            try:
                scheduled_dt = datetime.strptime(full_time_str, "%d/%m/%Y %I:%M%p")
            except ValueError:
                scheduled_dt = datetime.strptime(full_time_str, "%d/%m/%Y %H:%M")

        # Time Difference
        time_diff = (scheduled_dt - ist_now).total_seconds()
        
        print(f"      🕒 Scheduled: {scheduled_dt.strftime('%H:%M')} | Now: {ist_now.strftime('%H:%M')} | Gap: {int(time_diff)}s")

        if time_diff <= 0:
            return True 
        elif 0 < time_diff <= 300:
            print(f"      👀 TARGET LOCKED! Waiting {int(time_diff)}s to hit exact time...")
            time.sleep(time_diff + 2) 
            print("      🔫 BOOM! Exact Time Reached. Uploading...")
            return True
        else:
            print(f"      💤 Too early. Will check later.")
            return False 

    except ValueError:
        print(f"      ⚠️ Date/Time Skipped or Invalid (Use: 20/12/2025 & 2:30 PM)")
        return False 

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
    
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        print("✅ Sheet Connected via ID.")
    except:
        print("⚠️ ID failed, trying by name 'Content'...")
        sheet = client.open("Content").sheet1

    drive_service = build('drive', 'v3', credentials=creds)
    return sheet, drive_service

# =======================================================
# 🔧 UPLOAD FUNCTIONS (IG, FB, YOUTUBE)
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
        url_init = f"{domain}/{ig_user_id}/media"
        params = { "upload_type": "resumable", "media_type": "REELS", "caption": caption, "access_token": IG_ACCESS_TOKEN }
        r_init = requests.post(url_init, params=params)
        data_init = r_init.json()
        
        if "id" not in data_init: return False
        upload_uri = data_init["uri"]
        container_id = data_init["id"]

        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            headers = { "Authorization": f"OAuth {IG_ACCESS_TOKEN}", "offset": "0", "file_size": str(file_size) }
            r_upload = requests.post(upload_uri, data=f, headers=headers)
        
        if r_upload.status_code != 200: return False

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
    print(f"      📘 Facebook Upload ({brand_name})...")
    if not fb_page_id: return False
    url = f"https://graph.facebook.com/v19.0/{fb_page_id}/videos"
    try:
        params = { "description": caption, "access_token": IG_ACCESS_TOKEN }
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

def upload_to_youtube(brand_name, file_path, title, description, tags=[]):
    print(f"      🔴 YouTube Upload ({brand_name})...")
    
    # Check if brand exists in YouTube Config
    if brand_name not in YOUTUBE_CONFIG:
        print(f"      ⚠️ YouTube Skipped: No Config found for {brand_name}")
        return False

    try:
        # Load Credentials for specific brand
        creds_data = YOUTUBE_CONFIG[brand_name]
        creds = UserCredentials(
            None, # access_token (will refresh)
            refresh_token=creds_data["refresh_token"],
            client_id=creds_data["client_id"],
            client_secret=creds_data["client_secret"],
            token_uri="https://oauth2.googleapis.com/token"
        )

        # Refresh Token explicitly
        if not creds.valid:
            creds.refresh(Request())

        # Build YouTube Service
        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": title[:100], # YouTube Max Title Length
                "description": description[:5000],
                "tags": tags,
                "categoryId": "22" # People & Blogs (Generic)
            },
            "status": {
                "privacyStatus": "public", # Direct Public
                "selfDeclaredMadeForKids": False
            }
        }

        # Upload File
        media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"      🚀 YT Uploading: {int(status.progress() * 100)}%")

        if "id" in response:
            print(f"      ✅ YouTube Published: {response['id']}")
            return True
        else:
            print(f"      ❌ YouTube Failed: {response}")
            return False

    except Exception as e:
        print(f"      ❌ YouTube Exception: {e}")
        return False

# =======================================================
# 🚀 MAIN EXECUTION
# =======================================================

def start_bot():
    print("-" * 50)
    print(f"⏰ CONTENT SNIPER-BOT STARTED (IG + FB + YT)...")
    
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
            sheet_date = str(row.get("Schedule_Date", "")).strip()
            sheet_time = str(row.get("Schedule_Time", "")).strip()
            
            print(f"\n👉 Checking Row {i}: {row.get('Title_Hook') or row.get('Title')} | Brand: {brand}")
            
            if check_time_and_wait(sheet_date, sheet_time):
                
                if brand in BRAND_CONFIG:
                    
                    # IG & FB IDs
                    ig_id = BRAND_CONFIG[brand].get("ig_id")
                    fb_id = BRAND_CONFIG[brand].get("fb_id")
                    
                    video_url = row.get("Video_URL") or row.get("Video Link", "")
                    title = row.get("Title_Hook") or row.get("Title", "")
                    hashtags_str = row.get("Caption_Hashtags") or row.get("Hashtags", "")
                    caption = f"{title}\n.\n{hashtags_str}"
                    
                    # Prepare Tags for YouTube (Remove #)
                    yt_tags = [tag.strip().replace("#", "") for tag in hashtags_str.split() if "#" in tag]
                    
                    local_file = download_video_securely(drive_service, video_url)
                    
                    if local_file:
                        # 1. Instagram
                        ig_success = upload_to_instagram_resumable(brand, ig_id, local_file, caption)
                        
                        # 2. Facebook
                        fb_success = upload_to_facebook(brand, fb_id, local_file, caption)

                        # 3. YouTube (New Addition)
                        yt_success = upload_to_youtube(brand, local_file, title, caption, yt_tags)

                        # Cleanup
                        if os.path.exists(local_file): os.remove(local_file)

                        # Update Sheet if AT LEAST ONE succeeded
                        if ig_success or fb_success or yt_success:
                            status_parts = []
                            if ig_success: status_parts.append("IG")
                            if fb_success: status_parts.append("FB")
                            if yt_success: status_parts.append("YT")
                            
                            final_status = f"POSTED_{'_'.join(status_parts)}"
                            
                            sheet.update_cell(i, col_status, final_status)
                            print(f"      📝 Sheet Updated: {final_status}")
                            processed_count += 1
                            time.sleep(10)
                    else:
                        print("      ⚠️ Skipping: Download failed.")
            else:
                pass 

    if processed_count == 0:
        print("💤 No posts ready immediately.")
    else:
        print(f"🎉 Job Done! Uploads in this cycle: {processed_count}")

if __name__ == "__main__":
    start_bot()
