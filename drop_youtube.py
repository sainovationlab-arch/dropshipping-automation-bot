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
    print("💎 DROPSHIPPING YOUTUBE BOT STARTED...")
    try:
        creds_json = os.environ.get('GCP_CREDENTIALS')
        if not creds_json: return
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scope)
        gc = gspread.authorize(creds)
        sheet = gc.open(SHEET_NAME).get_worksheet(0)
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    rows = sheet.get_all_records()
    for i, row in enumerate(rows):
        row_num = i + 2
        platform = str(row.get('Platform', '')).strip().lower()
        status = str(row.get('Status', '')).strip().upper()
        
        if "youtube" in platform and status == "PENDING":
            print(f"🚀 Processing Row {row_num}")
            video_url = row.get('Video URL', '')
            title = row.get('Caption', 'New Product')
            tags = row.get('Tags', '#Dropshipping')
            link = row.get('Link', '')
            
            temp_file = "drop_video.mp4"
            sheet.update_cell(row_num, 8, "Downloading...")
            
            try:
                if "drive" in video_url:
                    gdown.download(video_url, temp_file, quiet=False, fuzzy=True)
                else:
                    with open(temp_file, 'wb') as f:
                        f.write(requests.get(video_url).content)

                token_env = os.environ.get('YOUTUBE_TOKEN_JSON')
                creds_yt = Credentials.from_authorized_user_info(json.loads(token_env))
                youtube = build('youtube', 'v3', credentials=creds_yt)
                
                body = {
                    'snippet': {'title': title, 'description': f"{title}\n\n🛍️ {link}\n\n{tags}", 'tags': tags.split(','), 'categoryId': '22'},
                    'status': {'privacyStatus': 'public'}
                }
                
                media = MediaFileUpload(temp_file, chunksize=-1, resumable=True)
                req = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
                
                resp = None
                while resp is None:
                    stat, resp = req.next_chunk()
                
                sheet.update_cell(row_num, 8, "DONE")
                sheet.update_cell(row_num, 9, f"https://youtu.be/{resp['id']}")
                print("✅ Done!")
                
                if os.path.exists(temp_file): os.remove(temp_file)
                break 

            except Exception as e:
                print(f"❌ Error: {e}")
                sheet.update_cell(row_num, 8, f"ERROR: {e}")
                break

if __name__ == "__main__":
    main()
