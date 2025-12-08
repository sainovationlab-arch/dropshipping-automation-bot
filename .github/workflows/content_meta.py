import os
import json
import gspread
import requests
import gdown
from oauth2client.service_account import ServiceAccountCredentials

SHEET_NAME = "Content_Sheet" # <--- Content Sheet

# Placeholder IDs (આ આપણે પછી શીટમાં અથવા સિક્રેટમાં મેનેજ કરીશું)
CONTENT_IDS = {
    "Pearl Verse": "PAGE_ID_HERE",
    "Diamond Dice": "PAGE_ID_HERE",
    "Emerald Edge": "PAGE_ID_HERE"
}

def main():
    print("🎨 CONTENT META BOT STARTED (PUBLIC SAFE MODE)...")
    
    # --- 1. SECURE CONNECTION ---
    try:
        creds_json = os.environ.get('GCP_CREDENTIALS')
        if not creds_json:
            print("❌ Secret Missing: GCP_CREDENTIALS")
            return
            
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scope)
        gc = gspread.authorize(creds)
        sheet = gc.open(SHEET_NAME).get_worksheet(0)
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    # --- 2. FIND ONE PENDING POST ---
    rows = sheet.get_all_records()
    post_processed = False

    for i, row in enumerate(rows):
        row_num = i + 2
        platform = str(row.get('Platform', '')).strip().lower()
        status = str(row.get('Status', '')).strip().upper()
        
        # Check: Insta/FB & PENDING
        if ("instagram" in platform or "facebook" in platform) and status == "PENDING":
            account_name = str(row.get('Account Name', '')).strip()
            print(f"🚀 Processing: {account_name} (Row {row_num})")
            
            insta_id = CONTENT_IDS.get(account_name)
            if not insta_id or insta_id == "PAGE_ID_HERE":
                print(f"❌ ID Missing for {account_name}")
                sheet.update_cell(row_num, 8, "ID ERROR")
                continue

            video_url = row.get('Video URL', '')
            caption = row.get('Caption', 'Satisfying ASMR')
            tags = row.get('Tags', '#ASMR')
            
            final_caption = f"{caption}\n\n{tags}"
            
            # Token form Secret
            access_token = os.environ.get('FB_ACCESS_TOKEN')
            if not access_token:
                print("❌ Secret Missing: FB_ACCESS_TOKEN")
                return

            temp_file = "content_reel.mp4"
            sheet.update_cell(row_num, 8, "Downloading...")
            
            try:
                gdown.download(video_url, temp_file, quiet=False, fuzzy=True)
                
                # Upload Logic (Simple Reels)
                url = f"https://graph.facebook.com/v19.0/{insta_id}/media"
                params = {
                    'access_token': access_token,
                    'caption': final_caption,
                    'media_type': 'REELS'
                }
                files = {'video_file': open(temp_file, 'rb')}
                
                # Upload
                response = requests.post(url, params=params, files=files).json()
                creation_id = response.get('id')
                
                if creation_id:
                    # Publish
                    pub_url = f"https://graph.facebook.com/v19.0/{insta_id}/media_publish"
                    pub_params = {'creation_id': creation_id, 'access_token': access_token}
                    pub_res = requests.post(pub_url, params=pub_params).json()
                    
                    if pub_res.get('id'):
                        sheet.update_cell(row_num, 8, "DONE")
                        print("✅ Posted Successfully!")
                    else:
                        print(f"❌ Publish Error: {pub_res}")
                        sheet.update_cell(row_num, 8, "PUB ERROR")
                else:
                    print(f"❌ Upload Error: {response}")
                    sheet.update_cell(row_num, 8, "UPLOAD ERROR")

                if os.path.exists(temp_file): os.remove(temp_file)
                
                post_processed = True
                break # <--- એક પોસ્ટ કરીને અટકી જશે

            except Exception as e:
                print(f"❌ Error: {e}")
                sheet.update_cell(row_num, 8, "ERROR")
                break

    if not post_processed:
        print("😴 No pending posts for Content Meta.")

if __name__ == "__main__":
    main()
