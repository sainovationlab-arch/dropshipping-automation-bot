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
# આ રોબોટ માત્ર આ શીટ જ વાંચશે
SHEET_NAME = "Dropshipping_Sheet"

# અલગ અલગ ચેનલ માટે અલગ ટોકન્સ (ભવિષ્યમાં આપણે અહીં અલગ ફાઈલો જોડીશું)
# અત્યારે ઉદાહરણ તરીકે એક જ Main Token વાપરીએ છીએ
TOKEN_MAPPING = {
    "Luxivibes": "TOKEN_LUXIVIBES",
    "Urban Glint": "TOKEN_URBANGLINT",
    "Grand Orbit": "TOKEN_GRANDORBIT",
    "Royal Nexus": "TOKEN_ROYALNEXUS",
    "Opus Elite": "TOKEN_OPUS"
}

def main():
    print("💎 DROPSHIPPING YOUTUBE BOT STARTED...")
    
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

        # માત્ર YouTube અને Dropshipping accounts
        if "youtube" in platform and status == "PENDING":
            print(f"🚀 Processing {account_name} (Row {row_num})...")
            
            # વિડીયો વિગતો
            video_url = row.get('Video URL', '')
            title = row.get('Caption', 'New Product') # YouTube Title = Caption column
            tags = row.get('Tags', '#Dropshipping')
            product_link = row.get('Link', '') # Product Link

            # Download
            temp_file = "drop_video.mp4"
            sheet.update_cell(row_num, 8, "Downloading...")
            
            try:
                if "drive" in video_url:
                    gdown.download(video_url, temp_file, quiet=False, fuzzy=True)
                
                # Channel Login Selection (Advanced Logic)
                # અત્યારે આપણે ડિફોલ્ટ એક જ સિક્રેટ વાપરીએ છીએ, પછી અપગ્રેડ કરીશું
                token_env = os.environ.get('YOUTUBE_TOKEN_JSON') 
                
                creds_yt = Credentials.from_authorized_user_info(json.loads(token_env))
                youtube = build('youtube', 'v3', credentials=creds_yt)
                
                # Description with Product Link
                description = f"{title}\n\n🛍️ BUY HERE: {product_link}\n\n{tags}"

                body = {
                    'snippet': {
                        'title': title,
                        'description': description,
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
                
                # Pinned Comment Logic (New Feature)
                video_id = resp['id']
                if product_link:
                    comment_text = f"🔥 Get yours here: {product_link}"
                    youtube.commentThreads().insert(
                        part="snippet",
                        body={
                            "snippet": {
                                "videoId": video_id,
                                "topLevelComment": {"snippet": {"textOriginal": comment_text}}
                            }
                        }
                    ).execute()
                    print("✅ Pinned Comment Added!")

                sheet.update_cell(row_num, 8, "DONE")
                sheet.update_cell(row_num, 9, f"https://youtu.be/{video_id}")
                
                if os.path.exists(temp_file): os.remove(temp_file)

            except Exception as e:
                print(f"❌ Error: {e}")
                sheet.update_cell(row_num, 8, f"ERROR: {e}")

if __name__ == "__main__":
    main()
