import os
import json
import gspread
import requests
import gdown
from oauth2client.service_account import ServiceAccountCredentials

SHEET_NAME = "Dropshipping_Sheet"

# 10 Accounts Mapping (તમારા સાચા IDs અહીં નાખવા પડશે)
# અત્યારે મેં ઉદાહરણ ID રાખ્યા છે
META_IDS = {
    "Luxivibes": "123456789",
    "Urban Glint": "17841479492205083",
    "Grand Orbit": "987654321",
    "Royal Nexus": "1122334455",
    "Opus Elite": "5566778899"
}

def main():
    print("💎 DROPSHIPPING META BOT STARTED...")
    
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
            
            insta_id = META_IDS.get(account_name)
            if not insta_id:
                print(f"❌ ID Missing for {account_name}")
                continue

            video_url = row.get('Video URL', '')
            caption_text = row.get('Caption', 'Check this out!')
            product_link = row.get('Link', '')
            tags = row.get('Tags', '')
            
            # Combine Caption + Link + Tags
            final_caption = f"{caption_text}\n\n👉 Shop Link: {product_link}\n\n{tags}"
            
            access_token = os.environ.get('FB_ACCESS_TOKEN')
            temp_file = "drop_reel.mp4"
            sheet.update_cell(row_num, 8, "Downloading...")
            
            try:
                gdown.download(video_url, temp_file, quiet=False, fuzzy=True)
                
                # Upload Reels (Advanced)
                # 1. Init Upload
                url = f"https://graph.facebook.com/v19.0/{insta_id}/media"
                params = {
                    'media_type': 'REELS',
                    'video_url': video_url, # Reels API needs Hosted URL usually, but let's try direct upload logic if needed
                    'caption': final_caption,
                    'access_token': access_token
                }
                # (નોંધ: Reels API માટે ઘણીવાર વિડીયો URL પબ્લિક હોવું જોઈએ. 
                # આપણે ડ્રાઈવ લિંક વાપરી રહ્યા છીએ, જે ક્યારેક પ્રોબ્લેમ કરે.
                # આપણે Container પદ્ધતિ વાપરીશું).
                
                creation_id = requests.post(url, params=params).json().get('id')

                if creation_id:
                    # 2. Publish
                    print("⏳ Waiting for processing...")
                    import time
                    time.sleep(10) # Wait for Meta to process video
                    
                    pub_url = f"https://graph.facebook.com/v19.0/{insta_id}/media_publish"
                    pub_params = {'creation_id': creation_id, 'access_token': access_token}
                    res = requests.post(pub_url, params=pub_params).json()
                    
                    if 'id' in res:
                        sheet.update_cell(row_num, 8, "DONE")
                        print("✅ Dropshipping Reel Posted!")
                    else:
                        print(f"❌ Publish Error: {res}")
                else:
                    print("❌ Upload Init Failed")

            except Exception as e:
                print(f"❌ Error: {e}")
                sheet.update_cell(row_num, 8, "ERROR")

if __name__ == "__main__":
    main()
