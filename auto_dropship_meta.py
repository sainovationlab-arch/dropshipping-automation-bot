import os
import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------- CONFIGURATION ---------------- #
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")
FIXED_INSTAGRAM_ID = "17841479516066757" # Pearl Verse ID (100% Verified)
SHEET_NAME = "Dropshipping_Sheet"

def get_google_sheet_client():
    # 🔥 POWER CHECK 1: Check for Google Key
    creds_json = os.environ.get("GCP_CREDS")
    if not creds_json:
        print("❌ CRITICAL ERROR: 'GCP_CREDS' secret is MISSING in GitHub!")
        print("👉 Solution: Go to GitHub Settings > Secrets > Add 'GCP_CREDS' with your JSON content.")
        return None
    
    try:
        creds_dict = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"❌ JSON ERROR: Your GCP_CREDS key is invalid. {e}")
        return None

def post_to_instagram():
    print("🚀 ACTIVATING UNIVERSAL DROPSHIP ENGINE...")
    
    # --- STEP 1: CONNECT TO SHEET ---
    client = get_google_sheet_client()
    if not client:
        return # Stop if no key

    try:
        sheet = client.open(SHEET_NAME).sheet1
        records = sheet.get_all_records()
        print("✅ Connected to Google Sheet Successfully.")
    except Exception as e:
        print(f"❌ SHEET ERROR: Could not open '{SHEET_NAME}'. Check exact spelling! Error: {e}")
        return

    # --- STEP 2: FIND PENDING POST ---
    row_data = None
    row_index = -1

    for i, row in enumerate(records):
        status = str(row.get("Status", "")).strip().upper()
        if status == "PENDING":
            row_data = row
            row_index = i + 2 # Header + 1-based index
            break
    
    if not row_data:
        print("💤 No 'PENDING' posts found. System Sleeping.")
        return

    print(f"📝 Processing Post: {row_data.get('Caption')}")
    
    # --- STEP 3: DATA VALIDATION (WEAPON 2) ---
    image_url = row_data.get("Video URL", "")
    caption = row_data.get("Caption", "")

    # Check for bad links
    if "ibb.co" in image_url or "drive.google" in image_url:
        print(f"❌ INVALID IMAGE LINK DETECTED: {image_url}")
        print("⚠️ Instagram requires direct links ending in .jpg or .png. ibb.co/drive links WILL FAIL.")
        sheet.update_cell(row_index, 9, "ERROR_BAD_LINK")
        return

    # --- STEP 4: INSTAGRAM UPLOAD ---
    post_url = f"https://graph.facebook.com/v19.0/{FIXED_INSTAGRAM_ID}/media"
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
        
        # Publish
        pub_url = f"https://graph.facebook.com/v19.0/{FIXED_INSTAGRAM_ID}/media_publish"
        pub_payload = {"creation_id": creation_id, "access_token": FB_ACCESS_TOKEN}
        pub_res = requests.post(pub_url, data=pub_payload)
        
        if pub_res.status_code == 200:
            print("🏆 VICTORY! POST IS LIVE! 🚀")
            sheet.update_cell(row_index, 9, "DONE")
        else:
            print(f"❌ Publish Failed: {pub_res.text}")
            sheet.update_cell(row_index, 9, "ERROR_PUBLISH")
    else:
        print(f"❌ Upload Failed: {response.text}")
        sheet.update_cell(row_index, 9, "ERROR_UPLOAD")

if __name__ == "__main__":
    post_to_instagram()
