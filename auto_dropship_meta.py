import os
import json
import requests
import gspread
import time
from oauth2client.service_account import ServiceAccountCredentials

# ---------------- CONFIGURATION ---------------- #
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")
SHEET_NAME = "Dropshipping_Sheet"

# 🔥 MASTER ACCOUNT DICTIONARY (તમારા સામ્રાજ્યનો નકશો)
# નામ એક્ઝેટ Google Sheet જેવા જ હોવા જોઈએ.
ACCOUNTS = {
    "Luxivibe": "17841478140648372",
    "Urban Glint": "17841479492205083",
    "Opus Elite": "17841479493645419",
    "Royal Nexus": "17841479056452004",
    "Grand Orbit": "17841479516066757",
    "Pearl Verse": "17841478822408000",
    "Diamond Dice": "17841478369307404",
    # "Emerald Edge": "AHI_ID_NAKHO" <--- આનું ID મળ્યું નથી, મળે એટલે અહીં નાખી દેજો.
}

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
    print("🚀 ACTIVATING MASTER DROPSHIP ENGINE (MULTI-ACCOUNT)...")
    
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
        print("💤 No 'PENDING' posts found. System Sleeping.")
        return

    # --- STEP 3: IDENTIFY ACCOUNT ---
    # શીટમાંથી નામ વાંચો (જેમ કે "Luxivibe")
    account_name = str(row_data.get("Account Name", "")).strip()
    caption = row_data.get("Caption", "")
    
    print(f"📝 Found Order for: {account_name}")
    
    # ડિક્શનરીમાંથી ID શોધો
    target_id = ACCOUNTS.get(account_name)
    
    if not target_id:
        print(f"❌ ERROR: Account '{account_name}' not found in code dictionary!")
        print("👉 Make sure the name in Sheet matches exactly with the code (Spelling check).")
        sheet.update_cell(row_index, 9, "ERROR_WRONG_NAME")
        return

    print(f"🎯 Target ID Found: {target_id}")

    # --- STEP 4: UPLOAD ---
    image_url = row_data.get("Video URL", "")
    
    post_url = f"https://graph.facebook.com/v19.0/{target_id}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": FB_ACCESS_TOKEN
    }

    print(f"📤 Uploading to {account_name}...")
    response = requests.post(post_url, data=payload)
    
    if response.status_code == 200:
        creation_id = response.json().get("id")
        print(f"✅ Container Ready! ID: {creation_id}")
        
        # Wait for processing
        print("⏳ Waiting 30 seconds for Instagram to process...")
        time.sleep(30)
        
        # --- STEP 5: PUBLISH ---
        publish_url = f"https://graph.facebook.com/v19.0/{target_id}/media_publish"
        pub_payload = {"creation_id": creation_id, "access_token": FB_ACCESS_TOKEN}
        
        print("🚀 Publishing now...")
        pub_res = requests.post(publish_url, data=pub_payload)
        
        if pub_res.status_code == 200:
            print(f"🏆 VICTORY! POST IS LIVE ON {account_name.upper()}! 🥳")
            sheet.update_cell(row_index, 9, "DONE")
        else:
            print(f"❌ Publish Failed: {pub_res.text}")
            sheet.update_cell(row_index, 9, "ERROR_PUBLISH")
    else:
        print(f"❌ Upload Failed: {response.text}")
        sheet.update_cell(row_index, 9, "ERROR_UPLOAD")

if __name__ == "__main__":
    post_to_instagram()
