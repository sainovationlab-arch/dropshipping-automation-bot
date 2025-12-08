import os
import json
import gspread
import requests
import gdown
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATION ---
SHEET_NAME = "Master_Scheduler"

# ID Mapping (Directly here for safety)
INSTAGRAM_IDS = {
    "Emerald Edge": "17841478369307404",
    "Urban Glint": "17841479492205083",
    "Diamond Dice": "17841478369307404",
    "Grand Orbit": "17841479516066757",
    "Opus": "17841479493645419",
    "Opal Elite": "17841479493645419",
    "Pearl Verse": "17841478822408000",
    "Royal Nexus": "17841479056452004",
    "Luxivibe": "17841479492205083"
}

def main():
    print("📸 INSTAGRAM/FB BOT STARTED...")
    
    # 1. CONNECT TO SHEET
    try:
        creds_json = os.environ.get('GCP_CREDENTIALS')
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scope)
        gc = gspread.authorize(creds)
        sheet = gc.open(SHEET_NAME).get_worksheet(0)
    except Exception as e:
        print(f"❌ Sheet Error: {e}")
        return

    # 2. READ DATA
    rows = sheet.get_all_records()
    
    for i, row in enumerate(rows):
        row_num = i + 2
        platform = str(row.get('Platform', '')).strip().lower()
        status = str(row.get('Status', '')).strip().upper()
        account_name = str(row.get('Account Name', '')).strip()

        # Instagram/Facebook અને PENDING હોય તો
        if ("instagram" in platform or "facebook" in platform) and status == "PENDING":
            print(f"🚀 Processing {account_name}...")

            # ID શોધો
            insta_id = INSTAGRAM_IDS.get(account_name)
            if not insta_id:
                print(f"❌ ID not found for {account_name}")
                sheet.update_cell(row_num, 8, "ID ERROR")
                continue

            video_url = row.get('Video URL', '')
            caption = row.get('Caption', 'New Collection')
            access_token = os.environ.get('FB_ACCESS_TOKEN') # Secret માંથી

            # Download Image/Video
            temp_file = "post_content.jpg"
            sheet.update_cell(row_num, 8, "Downloading...")
            
            try:
                gdown.download(video_url, temp_file, quiet=False, fuzzy=True)
                
                # Upload to Instagram (Graph API)
                url = f"https://graph.facebook.com/v19.0/{insta_id}/media"
                params = {'caption': caption, 'access_token': access_token}
                files = {'image': open(temp_file, 'rb')}
                
                # 1. Create Container
                resp = requests.post(url, data=params, files=files).json()
                creation_id = resp.get('id')

                if creation_id:
                    # 2. Publish Container
                    pub_url = f"https://graph.facebook.com/v19.0/{insta_id}/media_publish"
                    pub_params = {'creation_id': creation_id, 'access_token': access_token}
                    requests.post(pub_url, params=pub_params)
                    
                    sheet.update_cell(row_num, 8, "DONE")
                    print("✅ Posted Successfully!")
                else:
                    print(f"❌ Upload Failed: {resp}")
                    sheet.update_cell(row_num, 8, "API ERROR")
                
                if os.path.exists(temp_file): os.remove(temp_file)

            except Exception as e:
                print(f"❌ Error: {e}")
                sheet.update_cell(row_num, 8, f"ERROR: {e}")

if __name__ == "__main__":
    main()
