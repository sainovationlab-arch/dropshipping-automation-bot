import os
import json
import requests
import gspread
import time  # <--- આ નવું હથિયાર છે (Time)
from oauth2client.service_account import ServiceAccountCredentials

# ---------------- CONFIGURATION ---------------- #
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")
FIXED_INSTAGRAM_ID = "17841479516066757" # Pearl Verse ID
SHEET_NAME = "Dropshipping_Sheet"

def get_google_sheet_client():
    creds_json = os.environ.get("GCP_CREDENTIALS") 
    if not creds_json:
        print("❌ CRITICAL ERROR: 'GCP_CREDENTIALS' secret is MISSING!")
        return None
    try:
        creds_dict = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"❌ JSON ERROR: {e}")
        return None

def post_to_instagram():
    print("🚀 ACTIVATING UNIVERSAL DROPSHIP ENGINE...")
    
    # --- STEP 1: CONNECT TO SHEET ---
    client = get_google_sheet_client()
    if not client: return

    try:
        sheet = client.open(SHEET_NAME).sheet1
        records = sheet.get_all_records()
        print("✅ Connected to Google Sheet Successfully.")
    except Exception as e:
        print(f"❌ SHEET ERROR: Could not find '{SHEET_NAME}'. {e}")
        return

    # --- STEP 2: FIND PENDING POST ---
    row_data = None
    row_index = -1

    for i, row in enumerate(records):
        status = str(row.get("Status", "")).strip().upper()
        if status == "PENDING":
            row_data = row
            row_index = i + 2
            break
    
    if not row_data:
        print("💤 No 'PENDING' posts found via Google Sheet.")
        return

    print(f"📝 Processing Row {row_index}: {row_data.get('Caption')}")
    
    # --- STEP 3: UPLOAD ---
    image_url = row_data.get("Video URL", "")
    caption = row_data.get("Caption", "")
    target_id = FIXED_INSTAGRAM_ID
    
    post_url = f"https://graph.facebook.com/v19.0/{target_id}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": FB_ACCESS_TOKEN
    }

    print("📤 Uploading to Instagram...")
    response = requests.post(post_url, data=payload)
    
    if response.status_code == 200:
        creation_id = response.json().get("id")
        print(f"✅ Container Ready! ID: {creation_id}")
        
        # 🔥 CRITICAL STEP: WAIT FOR PROCESSING 🔥
        print("⏳ Waiting 30 seconds for Instagram to process the image...")
        time.sleep(30) # રોબોટ હવે 30 સેકન્ડ આરામ કરશે
        
        # --- STEP 4: PUBLISH ---
        publish_url = f"https://graph.facebook.com/v19.0/{target_id}/media_publish"
        pub_payload = {"creation_id": creation_id, "access_token": FB_ACCESS_TOKEN}
        
        print("🚀 Publishing now...")
        pub_res = requests.post(publish_url, data=pub_payload)
        
        if pub_res.status_code == 200:
            print("🏆 VICTORY! POST IS LIVE ON INSTAGRAM! 🥳")
            sheet.update_cell(row_index, 9, "DONE")
        else:
            print(f"❌ Publish Failed: {pub_res.text}")
            sheet.update_cell(row_index, 9, "ERROR_PUBLISH")
    else:
        print(f"❌ Upload Failed: {response.text}")
        sheet.update_cell(row_index, 9, "ERROR_UPLOAD")

if __name__ == "__main__":
    post_to_instagram()
