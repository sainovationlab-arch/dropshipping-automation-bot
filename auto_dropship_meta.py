import os
import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------- CONFIGURATION ---------------- #
# ફેસબુક ટોકન
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")

# ગુગલ શીટ સેટિંગ્સ
SHEET_NAME = "Dropshipping_Sheet"  # તમારી શીટનું નામ બરાબર હોવું જોઈએ

# 🔥 HARDCODED INSTAGRAM ID (આ આપણે શોધેલું સાચું ID છે)
# હવે રોબોટ ક્યારેય રસ્તો નહીં ભૂલે.
FIXED_INSTAGRAM_ID = "17841479516066757"

def get_google_sheet_client():
    # Google Cloud ડેટા લોડ કરો
    creds_json = os.environ.get("GCP_CREDS")
    if not creds_json:
        print("❌ Error: GCP_CREDS secret not found.")
        return None
    
    creds_dict = json.loads(creds_json)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def post_to_instagram():
    print("🚀 STARTING FINAL SYSTEM (SHEET + INSTAGRAM)...")
    
    # 1. Google Sheet કનેક્ટ કરો
    client = get_google_sheet_client()
    if not client:
        return

    try:
        sheet = client.open(SHEET_NAME).sheet1
        records = sheet.get_all_records()
    except Exception as e:
        print(f"❌ Sheet Error: {e}")
        return

    # 2. PENDING લાઈન શોધો
    pending_row_index = -1
    row_data = None

    for i, row in enumerate(records):
        # ડેટા સાફ કરો (Spaces કાઢી નાખો)
        status = str(row.get("Status", "")).strip().upper()
        if status == "PENDING":
            pending_row_index = i + 2  # Google Sheet 1-based index + Header
            row_data = row
            break
    
    if not row_data:
        print("✅ No PENDING posts found via Google Sheet.")
        return

    print(f"📝 Found Pending Post: {row_data.get('Caption')}")

    # 3. ડેટા તૈયાર કરો
    image_url = row_data.get("Video URL")
    caption = row_data.get("Caption")
    
    # ⚠️ ઈમેજ લિંક ચેક
    if "drive.google.com" in image_url or "dropbox" in image_url:
        print("❌ Error: Google Drive/Dropbox links don't work directly via API.")
        return

    # 4. પોસ્ટ કરો (Direct ID થી)
    target_id = FIXED_INSTAGRAM_ID
    print(f"🎯 Posting to Pearl Verse ID: {target_id}")

    # --- Step A: Upload Container ---
    post_url = f"https://graph.facebook.com/v19.0/{target_id}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": FB_ACCESS_TOKEN
    }

    try:
        response = requests.post(post_url, data=payload)
        response_data = response.json()

        if response.status_code == 200:
            creation_id = response_data.get("id")
            print(f"✅ Container Created! ID: {creation_id}")

            # --- Step B: Publish ---
            publish_url = f"https://graph.facebook.com/v19.0/{target_id}/media_publish"
            pub_payload = {
                "creation_id": creation_id,
                "access_token": FB_ACCESS_TOKEN
            }
            pub_response = requests.post(publish_url, data=pub_payload)
            
            if pub_response.status_code == 200:
                print("🏆 SUCCESS! POST IS LIVE ON INSTAGRAM!")
                
                # 🔥 5. Sheet Update કરો
                sheet.update_cell(pending_row_index, 9, "DONE") # Column 9 = Status
                print("✍️ Updated Sheet Status to DONE.")
                
            else:
                print(f"❌ Publish Failed: {pub_response.text}")
                sheet.update_cell(pending_row_index, 9, "ERROR_PUBLISH")
        else:
            print(f"❌ Upload Failed: {response.text}")
            sheet.update_cell(pending_row_index, 9, "ERROR_UPLOAD")

    except Exception as e:
        print(f"❌ Execution Error: {e}")

if __name__ == "__main__":
    post_to_instagram()
