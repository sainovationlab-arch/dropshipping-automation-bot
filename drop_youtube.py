import os
import json
import gspread
import requests
import gdown
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SHEET_NAME = "Dropshipping_Sheet"

def main():
    print("💎 DEBUG MODE STARTED...") # <--- ફેરફાર
    
    # 1. CHECK SECRET
    creds_json = os.environ.get('GCP_CREDENTIALS')
    if not creds_json:
        print("❌ CRITICAL ERROR: 'GCP_CREDENTIALS' Secret is MISSING!")
        print("👉 Please go to Settings > Secrets and add it.")
        return
    else:
        print("✅ Secret Found! Connecting...")

    # 2. CONNECT
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scope)
        gc = gspread.authorize(creds)
        sheet = gc.open(SHEET_NAME).get_worksheet(0)
        print("✅ Sheet Connected Successfully!")
    except Exception as e:
        print(f"❌ Sheet Connection Failed: {e}")
        return

    # 3. PROCESS ROWS
    rows = sheet.get_all_records()
    print(f"🔍 Checking {len(rows)} rows for PENDING tasks...")
    
    post_processed = False
    for i, row in enumerate(rows):
        row_num = i + 2
        platform = str(row.get('Platform', '')).strip().lower()
        status = str(row.get('Status', '')).strip().upper()
        
        if "youtube" in platform and status == "PENDING":
            print(f"🚀 Found Task at Row {row_num}")
            
            # ... (બાકીનો કોડ સેમ છે) ...
            video_url = row.get('Video URL', '')
            title = row.get('Caption', 'Test')
            
            # YouTube Token Check
            token_env = os.environ.get('YOUTUBE_TOKEN_JSON')
            if not token_env:
                print("❌ ERROR: 'YOUTUBE_TOKEN_JSON' Secret is MISSING!")
                return

            print("✅ YouTube Token Found. Downloading video...")
            temp_file = "video.mp4"
            
            try:
                if "drive" in video_url:
                    gdown.download(video_url, temp_file, quiet=False, fuzzy=True)
                else:
                    with open(temp_file, 'wb') as f:
                        f.write(requests.get(video_url).content)
                
                print("✅ Downloaded. Uploading to YouTube...")
                
                creds_yt = Credentials.from_authorized_user_info(json.loads(token_env))
                youtube = build('youtube', 'v3', credentials=creds_yt)
                
                body = {
                    'snippet': {'title': title, 'description': "Test Upload", 'categoryId': '22'},
                    'status': {'privacyStatus': 'public'} # અથવા 'private' ટેસ્ટ માટે
                }
                
                media = MediaFileUpload(temp_file, chunksize=-1, resumable=True)
                req = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
                
                resp = None
                while resp is None:
                    stat, resp = req.next_chunk()
                    if stat: print(f"Uploading... {int(stat.progress()*100)}%")
                
                sheet.update_cell(row_num, 9, "DONE")
                print(f"🎉 SUCCESS! Video Uploaded: {resp['id']}")
                post_processed = True
                break
                
            except Exception as e:
                print(f"❌ Upload Error: {e}")
                break

    if not post_processed:
        print("😴 No PENDING posts found in sheet.")

if __name__ == "__main__":
    main()
