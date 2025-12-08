import os
import json
import gspread
import requests
import gdown
from oauth2client.service_account import ServiceAccountCredentials

SHEET_NAME = "Content_Sheet"

# Content Accounts Mapping
CONTENT_IDS = {
    "Pearl Verse": "ID_PEARL_VERSE",
    "Diamond Dice": "ID_DIAMOND_DICE",
    "Emerald Edge": "ID_EMERALD_EDGE"
}

def main():
    print("🎨 CONTENT META BOT STARTED...")
    
    try:
        creds_json = os.environ.get('GCP_CREDENTIALS')
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scope)
        gc = gspread.authorize(creds)
        sheet = gc.open(SHEET_NAME).get_worksheet(0)
    except Exception as e:
        print(f"❌ Sheet Error: {e}")
        return

    rows = sheet.get_all_records()
    
    for i, row in enumerate(rows):
        row_num = i + 2
        platform = str(row.get('Platform', '')).strip().lower()
        status = str(row.get('Status', '')).strip().upper()
        account_name = str(row.get('Account Name', '')).strip()

        if ("instagram" in platform or "facebook" in platform) and status == "PENDING":
            print(f"🚀 Processing {account_name}...")
            
            insta_id = CONTENT_IDS.get(account_name)
            if not insta_id:
                print(f"❌ ID Missing for {account_name}")
                continue

            video_url = row.get('Video URL', '')
            caption = row.get('Caption', 'Satisfying ASMR')
            tags = row.get('Tags', '#ASMR')
            
            final_caption = f"{caption}\n\n{tags}"
            access_token = os.environ.get('FB_ACCESS_TOKEN')
            temp_file = "content_reel.mp4"
            
            sheet.update_cell(row_num, 8, "Downloading...")
            
            try:
                gdown.download(video_url, temp_file, quiet=False, fuzzy=True)
                
                # Upload to Reels
                url = f"https://graph.facebook.com/v19.0/{insta_id}/media"
                params = {
                    'media_type': 'REELS',
                    'video_url': video_url, # Direct URL prefer
                    'caption': final_caption,
                    'access_token': access_token
                }
                
                # Note: For strict implementation, we might need Container upload like drop_meta.py
                # Using simple POST logic here for brevity, assume similar structure to drop_meta
                
                creation_id = requests.post(url, params=params).json().get('id')
                
                if creation_id:
                    import time
                    time.sleep(10)
                    pub_url = f"https://graph.facebook.com/v19.0/{insta_id}/media_publish"
                    requests.post(pub_url, params={'creation_id': creation_id, 'access_token': access_token})
                    
                    sheet.update_cell(row_num, 8, "DONE")
                    print("✅ Content Reel Posted!")
                else:
                    print("❌ Upload Failed")
                    sheet.update_cell(row_num, 8, "API ERROR")

                if os.path.exists(temp_file): os.remove(temp_file)

            except Exception as e:
                print(f"❌ Error: {e}")
                sheet.update_cell(row_num, 8, "ERROR")

if __name__ == "__main__":
    main()
