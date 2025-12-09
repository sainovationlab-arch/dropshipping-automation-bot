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

        # DATA MAPPING
        account_name = str(row_values[2]).strip()   # Col C: Account Name
        platform = str(row_values[3]).strip().lower() # Col D
        media_url = str(row_values[4]).strip()      # Col E
        caption = str(row_values[5]).strip()        # Col F
        
        # Status Handling
        if len(row_values) > 8:
            status = str(row_values[8]).strip().upper() # Col I
        else:
            status = "UNKNOWN"

        # Check PENDING status
        if "PENDING" not in status:
            print(f"😴 Status is '{status}', skipping.")
            return

        print(f"🎯 Target Page from Sheet: '{account_name}'") # Debug print

        # 3. FACEBOOK API: GET PAGE ACCESS TOKEN
        user_access_token = os.environ.get('FB_ACCESS_TOKEN')
        if not user_access_token:
            print("❌ FB Token Missing")
            return

        # Fetch Pages
        resp = requests.get(f"https://graph.facebook.com/v18.0/me/accounts?access_token={user_access_token}")
        if resp.status_code != 200:
            print(f"❌ Failed to fetch pages. API Error: {resp.text}")
            return
        
        pages_data = resp.json().get('data', [])
        
        # 👇 DEBUGGING: Available Pages Print કરો
        available_pages = [p.get('name') for p in pages_data]
        print(f"👀 FOUND PAGES IN FACEBOOK: {available_pages}")
        
        page_token = None
        page_id = None

        # Find Page (Case Insensitive Check)
        for page in pages_data:
            if page.get('name').strip().lower() == account_name.lower():
                page_token = page.get('access_token')
                page_id = page.get('id')
                print(f"✅ Match Found! ID: {page_id}")
                break
        
        if not page_token:
            print(f"❌ ERROR: Could not find '{account_name}' in the list above.")
            return

        # 4. PUBLISH POST (REAL)
        print(f"📤 Uploading to {account_name}...")
        
        if ".mp4" in media_url or "video" in media_url:
            post_url = f"https://graph.facebook.com/v18.0/{page_id}/videos"
            payload = {'file_url': media_url, 'description': caption, 'access_token': page_token}
        else:
            post_url = f"https://graph.facebook.com/v18.0/{page_id}/photos"
            payload = {'url': media_url, 'caption': caption, 'access_token': page_token}

        post_resp = requests.post(post_url, data=payload)
        
        if post_resp.status_code == 200:
            post_id = post_resp.json().get('id')
            # Construct Link
            if "instagram" in platform:
                 post_link = f"https://instagram.com/p/{post_id}" # Simplification
            else:
                 post_link = f"https://facebook.com/{post_id}"

            print(f"🎉 SUCCESS! Posted. ID: {post_id}")
            
            # 5. UPDATE SHEET
            sheet.update_cell(2, 9, "DONE") 
            sheet.update_cell(2, 10, post_link) # Save link in Scheduled Time/Log col
        else:
            print(f"❌ Upload Failed: {post_resp.text}")
            sheet.update_cell(2, 9, "ERROR")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
