import os
import json
import gspread
import requests
from google.oauth2.service_account import Credentials

# 👇 શીટનું નામ
SHEET_NAME = "Dropshipping_Sheet"

def main():
    print("🚀 REAL MODE: DROPSHIPPING META BOT STARTED...")
    
    # 1. SETUP GOOGLE SHEETS
    try:
        creds_json = os.environ.get('GCP_CREDENTIALS')
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open(SHEET_NAME).get_worksheet(0)
    except Exception as e:
        print(f"❌ Sheet Connection Error: {e}")
        return

    # 2. GET ROW 2 DATA
    try:
        row_values = sheet.row_values(2)
        if not row_values or len(row_values) < 9:
            print("❌ Row 2 incomplete.")
            return

        # DATA MAPPING (તમારી શીટ મુજબ)
        account_name = str(row_values[2]).strip()   # Col C: Account Name (e.g., Pearl Verse)
        platform = str(row_values[3]).strip().lower() # Col D
        media_url = str(row_values[4]).strip()      # Col E (Video/Image URL)
        caption = str(row_values[5]).strip()        # Col F
        status = str(row_values[8]).strip().upper() # Col I (Index 8)

        # Check PENDING status
        if "PENDING" not in status:
            print(f"😴 Status is '{status}', skipping.")
            return

        # Check Platform (Facebook Only for this test)
        if "facebook" not in platform:
            print("⚠️ This test is for Facebook. Please check Platform column.")
            return

        print(f"🎯 Preparing to post to Facebook Page: {account_name}")

        # 3. FACEBOOK API: GET PAGE ACCESS TOKEN
        user_access_token = os.environ.get('FB_ACCESS_TOKEN')
        if not user_access_token:
            print("❌ FB Token Missing")
            return

        # બધા પેજનું લિસ્ટ મંગાવો
        resp = requests.get(f"https://graph.facebook.com/v18.0/me/accounts?access_token={user_access_token}")
        if resp.status_code != 200:
            print(f"❌ Failed to fetch pages: {resp.text}")
            return
        
        pages_data = resp.json().get('data', [])
        page_token = None
        page_id = None

        # સાચું પેજ શોધો (Pearl Verse)
        for page in pages_data:
            if page.get('name') == account_name:
                page_token = page.get('access_token')
                page_id = page.get('id')
                break
        
        if not page_token:
            print(f"❌ Could not find page: '{account_name}' in your connected accounts.")
            return

        print(f"✅ Found Page ID: {page_id}")

        # 4. PUBLISH POST (REAL)
        print("📤 Uploading to Facebook...")
        
        # જો URL માં .mp4 હોય તો Video, નહીંતર Photo ગણશે
        if ".mp4" in media_url or "video" in media_url:
            post_url = f"https://graph.facebook.com/v18.0/{page_id}/videos"
            payload = {'file_url': media_url, 'description': caption, 'access_token': page_token}
        else:
            post_url = f"https://graph.facebook.com/v18.0/{page_id}/photos"
            payload = {'url': media_url, 'caption': caption, 'access_token': page_token}

        # API Call (The Real Attack!)
        post_resp = requests.post(post_url, data=payload)
        
        if post_resp.status_code == 200:
            post_id = post_resp.json().get('id')
            print(f"🎉 SUCCESS! Posted to FB. ID: {post_id}")
            
            # 5. UPDATE SHEET
            sheet.update_cell(2, 9, "DONE") # Status -> DONE
            sheet.update_cell(2, 10, f"Posted! ID: {post_id}") # Scheduled Time column update as Log
        else:
            print(f"❌ Upload Failed: {post_resp.text}")
            sheet.update_cell(2, 9, "ERROR")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
