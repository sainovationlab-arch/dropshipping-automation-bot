import os
import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------- CONFIGURATION ---------------- #
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")
# 🔥 FIX: આ ID આપણે શોધેલું સાચું ID છે (Pearl Verse)
FIXED_INSTAGRAM_ID = "17841479516066757"
SHEET_NAME = "Dropshipping_Sheet"

def get_google_sheet_client():
    # 🔥 MAZOR FIX: અહીં નામ સુધાર્યું છે! (GCP_CREDS -> GCP_CREDENTIALS)
    # હવે આ તમારા GitHub Secret સાથે 100% મેચ થશે.
    creds_json = os.environ.get("GCP_CREDENTIALS") 
    
    if not creds_json:
        print("❌ CRITICAL ERROR: 'GCP_CREDENTIALS' secret is MISSING in GitHub!")
        return None
    
    try:
        creds_dict = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"❌ JSON ERROR: Check your GCP_CREDENTIALS content. {e}")
        return None

def post_to_instagram():
    print("🚀 STARTING FINAL INSTAGRAM ENGINE...")
    
    # --- STEP 1: CONNECT TO SHEET ---
    client = get_google_sheet_client()
    if not client:
        return

    try:
        sheet = client.open(SHEET_NAME).sheet1
        records = sheet.get_all_records()
        print("✅ Connected to Google Sheet Successfully.")
    except Exception as e:
        print(f"❌ SHEET ERROR: Could not find '{SHEET_NAME}'. Check spelling! Error: {e}")
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
    
    # --- STEP 3: CHECK IMAGE LINK ---
    image_url = row_data.get("Video URL", "")
    caption = row_data.get("Caption", "")

    # ⚠️ મહત્વનું: ibb.co લિંક ઇન્સ્ટાગ્રામ પર ચાલતી નથી.
    if "ibb.co" in image_url:
        print(f"❌ BAD LINK: {image_url}")
        print("⚠️ Please use direct links (ending in .jpg/.png) like Wikimedia or Imgur direct link.")
        sheet.update_cell(row_index, 9, "ERROR_BAD_LINK")
        return

    # --- STEP 4: UPLOAD & PUBLISH ---
    target_id = FIXED_INSTAGRAM_ID
    
    # Upload Container
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
        
        # Publish Container
        pub_url = f"https://graph.facebook.com/v19.0/{target_id}/media_publish"
        pub_payload = {"creation_id": creation_id, "access_token": FB_ACCESS_TOKEN}
        pub_res = requests.post(pub_url, data=pub_payload)
        
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
