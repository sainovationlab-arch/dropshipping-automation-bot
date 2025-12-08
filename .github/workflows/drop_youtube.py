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
# આ નામ સુરક્ષિત છે, કોઈ વાંધો નથી
SHEET_NAME = "Dropshipping_Sheet"

def main():
    print("💎 DROPSHIPPING YOUTUBE BOT STARTED (PUBLIC SAFE MODE)...")
    
    # --- 1. SECURE CONNECTION ---
    try:
        # અહીં આપણે ડાયરેક્ટ કી નથી લખતા, પણ Secret માંથી લઈએ છીએ
        creds_json = os.environ.get('GCP_CREDENTIALS')
        
        if not creds_json:
            print("❌ Error: GCP_CREDENTIALS secret is missing.")
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
        
        # Check: Platform YouTube હોવું જોઈએ અને Status PENDING હોવું જોઈએ
        if "youtube" in platform and status == "PENDING":
            account_name = str(row.get('Account Name', '')).strip()
            print(f"🚀 Found Task: Row {row_num} for {account_name}")
            
            video_url = row.get('Video URL', '')
            title = row.get('Caption', 'New Product')
            tags = row.get('Tags', '#Dropshipping')
            product_link = row.get('Link', '')

            # Download Video
            temp_file = "drop_video.mp4"
            sheet.update_cell(row_num, 8, "Downloading...") # Col H
            
            try:
                # ડાઉનલોડ લોજિક
                if "drive" in video_url:
                    gdown.download(video_url, temp_file, quiet=False, fuzzy=True)
                else:
                    with open(temp_file, 'wb') as f:
                        f.write(requests.get(video_url).content)
                
                # YouTube Login (Safe Mode)
                token_env = os.environ.get('YOUTUBE_TOKEN_JSON')
                if not token_env:
                    print("❌ Error: YOUTUBE_TOKEN_JSON secret is missing.")
                    sheet.update_cell(row_num, 8, "TOKEN ERROR")
                    return

                creds_yt = Credentials.from_authorized_user_info(json.loads(token_env))
                youtube = build('youtube', 'v3', credentials=creds_yt)
                
                # Upload Logic
                sheet.update_cell(row_num, 8, "Uploading...")
                description = f"{title}\n\n🛍️ SHOP HERE: {product_link}\n\n{tags}"

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
                    if stat: print(f"Uploading... {int(stat.progress()*100)}%")
                
                # Success
                sheet.update_cell(row_num, 8, "DONE")
                sheet.update_cell(row_num, 9, f"https://youtu.be/{resp['id']}") # Col I
                print(f"✅ Success! Video ID: {resp['id']}")
                
                # Cleanup
                if os.path.exists(temp_file): os.remove(temp_file)
                
                post_processed = True
                break # <--- સૌથી મહત્વનું: એક પોસ્ટ કરીને અટકી જશે (Unlimited Free Trick)

            except Exception as e:
                print(f"❌ Upload Error: {e}")
                sheet.update_cell(row_num, 8, f"ERROR: {e}")
                # એરર આવે તો પણ બ્રેક મારીએ જેથી લૂપ ના ફરે
                break

    if not post_processed:
        print("😴 No pending posts found for YouTube.")

if __name__ == "__main__":
    main()
