import os
import json
import gspread
import requests
import gdown
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIGURATION ---
SHEET_NAME = "Content_Sheet"  # <--- આ અલગ શીટ છે

def main():
    print("🎨 CONTENT YOUTUBE BOT STARTED (PUBLIC SAFE MODE)...")
    
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
        print(f"❌ Sheet Connection Error: {e}")
        return

    # --- 2. FIND ONE PENDING POST ---
    rows = sheet.get_all_records()
    post_processed = False

    for i, row in enumerate(rows):
        row_num = i + 2
        platform = str(row.get('Platform', '')).strip().lower()
        status = str(row.get('Status', '')).strip().upper()
        
        # Check: YouTube & PENDING
        if "youtube" in platform and status == "PENDING":
            account_name = str(row.get('Account Name', '')).strip()
            print(f"🚀 Processing: {account_name} (Row {row_num})")
            
            video_url = row.get('Video URL', '')
            title = row.get('Caption', 'Relaxing ASMR')
            tags = row.get('Tags', '#ASMR #Shorts')

            temp_file = "content_video.mp4"
            sheet.update_cell(row_num, 8, "Downloading...")
            
            try:
                # Download
                if "drive" in video_url:
                    gdown.download(video_url, temp_file, quiet=False, fuzzy=True)
                else:
                    with open(temp_file, 'wb') as f:
                        f.write(requests.get(video_url).content)
                
                # YouTube Login (From Secret)
                token_env = os.environ.get('YOUTUBE_TOKEN_JSON')
                if not token_env:
                    print("❌ Secret Missing: YOUTUBE_TOKEN_JSON")
                    return

                creds_yt = Credentials.from_authorized_user_info(json.loads(token_env))
                youtube = build('youtube', 'v3', credentials=creds_yt)
                
                # Upload Logic
                sheet.update_cell(row_num, 8, "Uploading...")
                description = f"{title}\n\nSubscribe for more satisfying videos!\n\n{tags}"

                body = {
                    'snippet': {
                        'title': title,
                        'description': description,
                        'tags': tags.split(','),
                        'categoryId': '24' # Entertainment
                    },
                    'status': {'privacyStatus': 'public'}
                }
                
                media = MediaFileUpload(temp_file, chunksize=-1, resumable=True)
                req = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
                
                resp = None
                while resp is None:
                    stat, resp = req.next_chunk()
                    if stat: print(f"Uploading... {int(stat.progress()*100)}%")
                
                # Success
                sheet.update_cell(row_num, 8, "DONE")
                sheet.update_cell(row_num, 9, f"https://youtu.be/{resp['id']}")
                print(f"✅ Success! Video ID: {resp['id']}")
                
                if os.path.exists(temp_file): os.remove(temp_file)
                
                post_processed = True
                break # <--- મહત્વનું: એક પોસ્ટ કરીને અટકી જશે

            except Exception as e:
                print(f"❌ Error: {e}")
                sheet.update_cell(row_num, 8, f"ERROR: {e}")
                break

    if not post_processed:
        print("😴 No pending posts for Content YouTube.")

if __name__ == "__main__":
    main()
