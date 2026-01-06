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
        "ig_id": "17841479527122900", 
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

def get_page_access_token(page_id):
    """
    🔥 FIX: Exchanges User Token for Page Token (Fixes Permission Error)
    """
    try:
        url = f"https://graph.facebook.com/v19.0/{page_id}?fields=access_token&access_token={IG_ACCESS_TOKEN}"
        r = requests.get(url).json()
        if "access_token" in r:
            return r["access_token"]
        return IG_ACCESS_TOKEN 
    except: return IG_ACCESS_TOKEN

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
# 🔧 UPLOAD FUNCTIONS (WITH TIMER, LINK & AUTO-COMMENT)
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
    if not fb_page_id: return False, "", 0, ""
    
    # 👇 Fix: Auto-Fetch Page Token
    page_token = get_page_access_token(fb_page_id)
    
    try:
        url = f"https://graph.facebook.com/v19.0/{fb_page_id}/videos"
        params = { "description": caption, "access_token": page_token } # Uses Page Token
        with open(file_path, "rb") as f:
            r = requests.post(url, params=params, files={"source": f}).json()
        
        end_t = time.time()
        duration = int(end_t - start_t)
        
        if "id" in r:
            link = f"https://www.facebook.com/{fb_page_id}/videos/{r['id']}/"
            # 🔥 NEW: Return Video ID also (for commenting)
            return True, link, duration, r['id']
        return False, "", 0, ""
    except: return False, "", 0, ""

def post_facebook_comment(object_id, message, page_id):
    """
    🔥 NEW: Posts a comment on the video with the link
    """
    print(f"      💬 Posting Auto-Comment on FB...")
    page_token = get_page_access_token(page_id)
    try:
        url = f"https://graph.facebook.com/v19.0/{object_id}/comments"
        params = { "message": message, "access_token": page_token }
        r = requests.post(url, params=params).json()
        if "id" in r:
            print("      ✅ Comment Posted Successfully!")
            return True
        else:
            print(f"      ⚠️ Comment Failed: {r}")
            return False
    except Exception as e:
        print(f"      ❌ Comment Error: {e}")
        return False

# =======================================================
# 🧠 SMART INSTAGRAM AUTO-DM (MATCHING PRODUCTS)
# =======================================================

def run_instagram_auto_dm(sheet):
    print("\n🤖 === STARTING SMART DM CHECK (Limit 50) ===") 
    
    # 1. Sheet Read Logic
    try:
        all_records = sheet.get_all_records()
        product_map = {} 
        
        for row in all_records:
            uploaded_link = str(row.get("Link", "")).strip()
            # Handle "Product Link" (Space) or "Product_Link" (Underscore)
            buying_link = str(row.get("Product Link", "")).strip()
            if not buying_link: buying_link = str(row.get("Product_Link", "")).strip()

            if uploaded_link and buying_link and "instagram.com" in uploaded_link:
                try:
                    parts = uploaded_link.split("/reel/")
                    if len(parts) > 1:
                        shortcode = parts[1].split("/")[0]
                        product_map[shortcode] = buying_link
                except: pass
                    
        print(f"   📊 Loaded {len(product_map)} products from sheet.")
    except Exception as e:
        print(f"   ⚠️ Sheet Read Error: {e}")
        return

    # 2. Log Book
    try:
        log_sheet = sheet.worksheet("DM_Logs")
    except:
        log_sheet = sheet.add_worksheet(title="DM_Logs", rows="2000", cols="4")
        log_sheet.append_row(["Comment_ID", "User", "Message_Sent", "Time"])
    
    replied_ids = log_sheet.col_values(1)
    keywords = ["BUY", "LINK", "SHOP", "PRICE", "ORDER", "WANT", "PP", "INTERESTED"]
    default_link = "https://solanki-art.myshopify.com"

    # 3. Scanning Logic
    for brand, config in BRAND_CONFIG.items():
        ig_id = config.get("ig_id")
        if not ig_id: continue
        
        print(f"   🔍 Scanning {brand} (Limit 50)...")
        url = f"https://graph.facebook.com/v19.0/{ig_id}/media?fields=shortcode,comments{{text,username,id}}&limit=50&access_token={IG_ACCESS_TOKEN}"
        
        try:
            r = requests.get(url).json()
            if "data" not in r: continue
            
            new_replies = []
            for media in r["data"]:
                media_shortcode = media.get("shortcode")
                final_link = product_map.get(media_shortcode, default_link)
                
                if "comments" in media:
                    for comment in media["comments"]["data"]:
                        c_id = comment["id"]
                        c_text = comment["text"].upper()
                        c_user = comment.get("username", "Unknown")
                        
                        if any(k in c_text for k in keywords) and c_id not in replied_ids:
                            print(f"      💡 {c_user} wants {media_shortcode}. Sending link...")
                            reply_url = f"https://graph.facebook.com/v19.0/{ig_id}/messages"
                            payload = {
                                "recipient": {"comment_id": c_id},
                                "message": {"text": f"Hey {c_user}! 👋 Here is the link you asked for: {final_link}"}
                            }
                            headers = {"Authorization": f"OAuth {IG_ACCESS_TOKEN}"}
                            send = requests.post(reply_url, json=payload, headers=headers).json()
                            
                            if "recipient_id" in send:
                                print(f"      ✅ DM SENT!")
                                new_replies.append([c_id, c_user, "Sent", str(datetime.now())])
                                replied_ids.append(c_id)
            
            if new_replies:
                for row in new_replies:
                    log_sheet.append_row(row)
                    time.sleep(1)
        except Exception as e:
            print(f"      ⚠️ Error in {brand}: {e}")
    print("🤖 === SMART DM FINISHED ===\n")

# =======================================================
# 🚀 MAIN EXECUTION (ULTRA SHORT CAPTION + FULL FB DESC)
# =======================================================

def start_bot():
    print("-" * 50)
    print(f"⏰ SUPER-BOT STARTED (Ultra Short Insta + Full FB)...")
    
    # 👇 MAIN STORE LINK (For Facebook)
    MAIN_STORE_URL = "https://solanki-art.myshopify.com"
    
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
                    
                    # ✅ FETCH FULL DETAILS
                    title = str(row.get("Title_Hook", "")).strip()
                    desc = str(row.get("Discription", "")).strip()
                    hashtags = str(row.get("Hastag", "")).strip()
                    
                    # Fetch Link (Try both spellings)
                    product_link = str(row.get("Product Link", "")).strip()
                    if not product_link:
                        product_link = str(row.get("Product_Link", "")).strip()
                    
                    # ---------------------------------------------------------
                    # 🔥 SMART CAPTION LOGIC (NEW STRATEGY)
                    # ---------------------------------------------------------
                    
                    # 1. FACEBOOK (Title + Link + Main Link + Desc + Hashtags)
                    # આમાં બધું જ નાખ્યું છે. ગ્રાહકને બધું મળે.
                    fb_caption = f"""🔥 {title}

🛒 BUY HERE: {product_link}

🏠 STORE: {MAIN_STORE_URL}

{desc}

{hashtags}"""

                    # 2. INSTAGRAM (Ultra Short & Punchy)
                    # ટાઈટલ પણ કાઢી નાખ્યું. માત્ર "Buy" અને "Link".
                    ig_caption = f"💬 Comment 'BUY' for Link! 🔗\nOr Link in Bio 🏠\n.\n{hashtags}"
                    
                    # ---------------------------------------------------------
                    
                    local_file = download_video_securely(drive_service, video_url)
                    
                    if local_file:
                        success = False
                        final_link = ""
                        duration = 0

                        # --- INSTAGRAM UPLOAD ---
                        if "Instagram" in platform:
                            s, l, d = upload_to_instagram_resumable(brand, ig_id, local_file, ig_caption)
                            if s: 
                                success = True
                                final_link = l
                                duration = d
                                
                        # --- FACEBOOK UPLOAD ---
                        if "Facebook" in platform:
                            s, l, d, vid_id = upload_to_facebook(brand, fb_id, local_file, fb_caption)
                            if s:
                                success = True
                                final_link = l 
                                duration = d
                                
                                # 🔥 AUTO-COMMENT FEATURE
                                if product_link and vid_id:
                                    print("      ⏳ Waiting 10s before commenting...")
                                    time.sleep(10)
                                    comment_msg = f"🛍️ Grab yours here! 👇\n{product_link}\n\n🔥 Limited Stock!"
                                    post_facebook_comment(vid_id, comment_msg, fb_id)

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

    # 🔥 RUN AUTO-DM BOT (INSTAGRAM ONLY)
    run_instagram_auto_dm(sheet)

if __name__ == "__main__":
    start_bot()
