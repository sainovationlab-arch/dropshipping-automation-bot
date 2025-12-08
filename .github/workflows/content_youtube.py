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
SHEET_NAME = "Content_Sheet"  # આ અલગ શીટ છે

def main():
    print("🎨 CONTENT CREATION YOUTUBE BOT STARTED...")
    
    # 1. Sheet Connection
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

        # માત્ર YouTube અને Content accounts (Pearl Verse, Diamond Dice, Emerald Edge)
        if "youtube" in platform and status == "PENDING":
            print(f"🚀 Processing {account_name} (Row {row_num})...")
            
            video_url = row.get('Video URL', '')
            title = row.get('Caption', 'Amazing ASMR')
            tags = row.get('Tags', '#ASMR #Shorts')

            # Download
            temp_file = "content_video.mp4"
            sheet.update_cell(row_num, 8, "Downloading...")
            
            try:
                gdown.download(video_url, temp_file, quiet=False, fuzzy=True)
                
                # Login Logic (અત્યારે Main Token થી, પછી મલ્ટી-ચેનલ)
                token_env = os.environ.get('YOUTUBE_TOKEN_JSON')
                creds_yt = Credentials.from_authorized_user_info(json.loads(token_env))
                youtube = build('youtube', 'v3', credentials=creds_yt)
                
                # Content Description (No product link needed here mostly)
                description = f"{title}\n\nSubscribe for more satisfying ASMR!\n\n{tags}"

                body = {
                    'snippet': {
                        'title': title,
                        'description': description,
                        'tags': tags.split(','),
                        'categoryId': '24' # Entertainment Category
                    },
                    'status': {'privacyStatus': 'public'}
                }
                
                media = MediaFileUpload(temp_file, chunksize=-1, resumable=True)
                req = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
                
                resp = None
                while resp is None:
                    stat, resp = req.next_chunk()
                    if stat: print(f"Uploading {int(stat.progress()*100)}%")
                
                sheet.update_cell(row_num, 8, "DONE")
                sheet.update_cell(row_num, 9, f"https://youtu.be/{resp['id']}")
                print(f"✅ Content Upload Success: {account_name}")
                
                if os.path.exists(temp_file): os.remove(temp_file)

            except Exception as e:
                print(f"❌ Error: {e}")
                sheet.update_cell(row_num, 8, f"ERROR: {e}")

if __name__ == "__main__":
    main()
