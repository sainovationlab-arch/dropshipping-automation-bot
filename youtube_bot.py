import os
import json
import gspread
import requests
import gdown
import time
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIGURATION ---
SHEET_NAME = "Master_Scheduler"

def main():
    print("📺 YOUTUBE BOT STARTED...")
    
    # 1. CONNECT TO SHEET
    try:
        # GitHub Secrets માંથી ચાવી લઈએ છીએ
        creds_json = os.environ.get('GCP_CREDENTIALS')
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scope)
        gc = gspread.authorize(creds)
        sheet = gc.open(SHEET_NAME).get_worksheet(0)
        print("✅ Sheet Connected")
    except Exception as e:
        print(f"❌ Sheet Error: {e}")
        return

    # 2. READ DATA
    rows = sheet.get_all_records()
    print(f"🔍 Checking {len(rows)} rows...")

    for i, row in enumerate(rows):
        row_num = i + 2
        platform = str(row.get('Platform', '')).strip().lower()
        status = str(row.get('Status', '')).strip().upper()

        # ફક્ત YouTube અને PENDING હોય તેને જ પકડો
        if "youtube" in platform and status == "PENDING":
            print(f"🚀 Processing Row {row_num}...")
            
            video_url = row.get('Video URL', '')
            title = row.get('Title', 'Amazing Shorts')
            tags = row.get('Tags', '#Shorts')

            # Download Video
            temp_file = "video.mp4"
            sheet.update_cell(row_num, 8, "Downloading...") # Status update
            
            try:
                if "drive.google.com" in video_url:
                    gdown.download(video_url, temp_file, quiet=False, fuzzy=True)
                else:
                    with open(temp_file, 'wb') as f:
                        f.write(requests.get(video_url).content)
                
                # Upload to YouTube
                sheet.update_cell(row_num, 8, "Uploading...")
                
                token_json = os.environ.get('YOUTUBE_TOKEN_JSON')
                creds_yt = Credentials.from_authorized_user_info(json.loads(token_json))
                youtube = build('youtube', 'v3', credentials=creds_yt)
                
                body = {
                    'snippet': {
                        'title': title,
                        'description': f"{title}\n\n{tags}",
                        'tags': tags.split(','),
                        'categoryId': '22'
                    },
                    'status': {'privacyStatus': 'public'}
                }
                
                media = MediaFileUpload(temp_file, chunksize=-1, resumable=True)
                req = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
                
                resp = None
                while resp is None:
                    stat, resp = req.next_chunk()
                    if stat: print(f"Uploading {int(stat.progress()*100)}%")

                # Success
                sheet.update_cell(row_num, 8, "DONE")
                sheet.update_cell(row_num, 9, f"https://youtu.be/{resp['id']}")
                print(f"✅ Upload Success: https://youtu.be/{resp['id']}")
                
                if os.path.exists(temp_file): os.remove(temp_file)

            except Exception as e:
                print(f"❌ Error on Row {row_num}: {e}")
                sheet.update_cell(row_num, 8, f"ERROR: {e}")

if __name__ == "__main__":
    main()
