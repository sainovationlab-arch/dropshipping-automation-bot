import os
import json
import gspread
import requests
import gdown
from oauth2client.service_account import ServiceAccountCredentials

SHEET_NAME = "Content_Sheet"
CONTENT_IDS = { "Pearl Verse": "PAGE_ID_HERE", "Diamond Dice": "PAGE_ID_HERE" }

def main():
    print("🎨 CONTENT META BOT STARTED...")
    try:
        creds_json = os.environ.get('GCP_CREDENTIALS')
        if not creds_json: return
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scope)
        gc = gspread.authorize(creds)
        sheet = gc.open(SHEET_NAME).get_worksheet(0)
    except: return

    rows = sheet.get_all_records()
    for i, row in enumerate(rows):
        row_num = i + 2
        platform = str(row.get('Platform', '')).strip().lower()
        status = str(row.get('Status', '')).strip().upper()

        if ("instagram" in platform or "facebook" in platform) and status == "PENDING":
            print(f"🚀 Processing Row {row_num}")
            video_url = row.get('Video URL', '')
            caption = row.get('Caption', '')
            
            acc_name = str(row.get('Account Name', '')).strip()
            page_id = CONTENT_IDS.get(acc_name, "PAGE_ID_HERE") 

            access_token = os.environ.get('FB_ACCESS_TOKEN')
            temp_file = "content_reel.mp4"
            sheet.update_cell(row_num, 8, "Downloading...")
            
            try:
                gdown.download(video_url, temp_file, quiet=False, fuzzy=True)
                url = f"https://graph.facebook.com/v19.0/{page_id}/media"
                params = {'access_token': access_token, 'caption': caption, 'media_type': 'REELS'}
                files = {'video_file': open(temp_file, 'rb')}
                
                resp = requests.post(url, params=params, files=files).json()
                if resp.get('id'):
                    pub_url = f"https://graph.facebook.com/v19.0/{page_id}/media_publish"
                    requests.post(pub_url, params={'creation_id': resp['id'], 'access_token': access_token})
                    sheet.update_cell(row_num, 8, "DONE")
                    print("✅ Done!")
                else:
                    sheet.update_cell(row_num, 8, "API ERROR")
                
                if os.path.exists(temp_file): os.remove(temp_file)
                break
            except Exception as e:
                sheet.update_cell(row_num, 8, "ERROR")
                break

if __name__ == "__main__":
    main()
