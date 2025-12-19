import os
import json
import time
import requests
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 1. CONFIGURATION & CREDENTIALS SETUP
# ==========================================

# Google Cloud Scope
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_google_client():
    """Securely fetches Google Credentials from GitHub Secrets"""
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    
    if not creds_json:
        raise ValueError("❌ Error: 'GOOGLE_SHEETS_CREDENTIALS' secret not found in environment variables.")
    
    try:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except json.JSONDecodeError:
        raise ValueError("❌ Error: The JSON in 'GOOGLE_SHEETS_CREDENTIALS' is invalid (malformed).")

# Instagram Credentials from Secrets
IG_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
IG_USER_ID = os.environ.get("INSTAGRAM_ACCOUNT_ID")

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def convert_drive_link_to_direct(url):
    """Converts a standard Google Drive View link to a Direct Download link for Instagram API"""
    if "drive.google.com" in url and "/d/" in url:
        try:
            file_id = url.split('/d/')[1].split('/')[0]
            # Instagram API requires a direct streamable link
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        except IndexError:
            return url
    return url

def post_reel_to_instagram(video_url, caption):
    """Uploads a video as a Reel to Instagram using the Official Graph API"""
    
    if not IG_ACCESS_TOKEN or not IG_USER_ID:
        print("⚠️ Instagram Credentials missing! Skipping Instagram upload.")
        return False

    domain = "https://graph.facebook.com/v18.0"
    
    # Step 1: Create Media Container (Upload Request)
    print(f"🚀 Initializing Upload for: {video_url[:30]}...")
    url_create = f"{domain}/{IG_USER_ID}/media"
    payload_create = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": IG_ACCESS_TOKEN
    }
    
    response = requests.post(url_create, data=payload_create)
    result = response.json()
    
    if "id" not in result:
        print(f"❌ Error Creating Container: {result}")
        return False
    
    creation_id = result["id"]
    print(f"✅ Container Created ID: {creation_id}")

    # Step 2: Wait for Media Processing (Crucial Step)
    print("⏳ Waiting for Instagram to process the video...")
    status_url = f"{domain}/{creation_id}"
    
    for _ in range(10):  # Check status 10 times (every 10 seconds)
        time.sleep(10)
        status_response = requests.get(status_url, params={"fields": "status_code", "access_token": IG_ACCESS_TOKEN})
        status_data = status_response.json()
        
        status_code = status_data.get("status_code", "")
        print(f"   Status: {status_code}")
        
        if status_code == "FINISHED":
            break
        elif status_code == "ERROR":
            print("❌ Video Processing Failed by Instagram.")
            return False
    else:
        print("⚠️ Timeout: Video took too long to process.")
        return False

    # Step 3: Publish the Media
    print("🚀 Publishing Media...")
    publish_url = f"{domain}/{IG_USER_ID}/media_publish"
    publish_payload = {
        "creation_id": creation_id,
        "access_token": IG_ACCESS_TOKEN
    }
    
    pub_response = requests.post(publish_url, data=publish_payload)
    pub_data = pub_response.json()
    
    if "id" in pub_data:
        print(f"🎉 SUCCESS! Reel Published. ID: {pub_data['id']}")
        return True
    else:
        print(f"❌ Error Publishing: {pub_data}")
        return False

# ==========================================
# 3. MAIN BOT LOGIC
# ==========================================

def main():
    print("🤖 Master Bot Started...")
    
    try:
        client = get_google_client()
        # Change 'Content' to your actual Sheet Name if different
        sheet = client.open("Content").sheet1 
        print("✅ Google Sheet Connected Successfully")
    except Exception as e:
        print(f"❌ Critical Error Connecting to Sheet: {e}")
        return

    # Fetch all records
    data = sheet.get_all_records()
    
    # Find headers to identify columns
    headers = sheet.row_values(1)
    try:
        status_col_index = headers.index("Status") + 1
    except ValueError:
        print("❌ Error: 'Status' column not found in Sheet.")
        return

    rows_processed = 0

    for i, row in enumerate(data, start=2):  # Start from row 2 (skipping header)
        status = row.get("Status", "").strip().upper()
        platform = row.get("Platform", "").strip().upper() # Optional: Filter by Platform
        
        if status == "PENDING":
            print(f"\nExample Row Found at #{i}: {row['Title']}")
            
            video_link_raw = row.get("Video Link", "")
            caption = f"{row.get('Title', '')}\n\n{row.get('Hashtags', '')}"
            
            # Convert Drive link for Instagram
            direct_video_url = convert_drive_link_to_direct(video_link_raw)
            
            # --- ACTION: POST TO INSTAGRAM ---
            success = post_reel_to_instagram(direct_video_url, caption)
            
            if success:
                # Update Status in Sheet
                sheet.update_cell(i, status_col_index, "POSTED")
                print(f"✅ Sheet Updated for Row {i}")
                rows_processed += 1
            else:
                print(f"⚠️ Failed to process Row {i}")

    if rows_processed == 0:
        print("\nℹ️ No 'PENDING' posts found to process.")
    else:
        print(f"\n✅ Total Rows Processed: {rows_processed}")

if __name__ == "__main__":
    main()
