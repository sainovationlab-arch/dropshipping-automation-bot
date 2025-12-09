import os
import json
import gspread
import gdown
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import requests
import pandas as pd # Ensure pandas is imported if used later

# 👇 શીટનું નામ બદલવામાં આવ્યું છે!
SHEET_NAME = "Content_Sheet" 

def main():
    print("💎 CONTENT YOUTUBE BOT STARTED...")
    post_processed = False
    
    # 1. LOGIN (Google Sheet)
    try:
        creds_json = os.environ.get('GCP_CREDENTIALS')
        if not creds_json: 
            print("❌ CRITICAL ERROR: 'GCP_CREDENTIALS' Secret is MISSING!")
            return
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scope)
        gc = gspread.authorize(creds)
        sheet = gc.open(SHEET_NAME).get_worksheet(0)
        print(f"✅ Connected to {SHEET_NAME}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    # 2. PROCESS ROWS
    try:
        rows = sheet.get_all_records()
        print(f"🔍 Checking {len(rows)} rows for PENDING tasks...")
        
        for i, row in enumerate(rows):
            row_num = i + 2 # Row 1 is header
            
            platform = str(row.get('Platform', '')).strip().lower()
            status = str(row.get('Status', '')).strip().upper()
            
            if "youtube" in platform and status == "PENDING":
                print(f"🚀 Found Content Task at Row {row_num}")
                
                # DATA EXTRACTION (Based on Content_Sheet columns)
                video_url = row.get('Video URL', '') 
                title = row.get('Caption', 'Content Post') 
                tags = row.get('Tags', '#shorts #content')
                
                # YouTube Token Check
                token_env = os.environ.get('YOUTUBE_TOKEN_JSON')
                if not token_env:
                    print("❌ ERROR: 'YOUTUBE_TOKEN_JSON' Secret is MISSING!")
                    continue 

                print("✅ YouTube Token Found. Downloading video...")
                temp_file = "content_video.mp4"
                
                # DOWNLOAD LOGIC (identical to dropshipping bot)
                try:
                    # Simplified download using requests for generic URLs or gdown for Drive
                    r = requests.get(video_url, stream=True)
                    if r.status_code == 200:
                        with open(temp_file, 'wb') as f:
                            for chunk in r.iter_content(1024): f.write(chunk)
                        downloaded = True
                    else:
                        downloaded = False
                    
                    if not downloaded and "drive" in video_url:
                        gdown.download(video_url, temp_file, quiet=False, fuzzy=True)
                        downloaded = True
                
                except Exception as e:
                    downloaded = False
                    print(f"❌ Download Failed: {e}")
                
                if downloaded:
                    # UPLOAD LOGIC
                    sheet.update_cell(row_num, 9, "Uploading...") # Update Status column
                    
                    creds_yt = Credentials.from_authorized_user_info(json.loads(token_env))
                    youtube = build('youtube', 'v3', credentials=creds_yt)
                    
                    body = {
                        'snippet': {'title': title, 'description': f"{title}\n{tags}", 'categoryId': '22'},
                        'status': {'privacyStatus': 'public'} 
                    }
                    
                    media = MediaFileUpload(temp_file, chunksize=-1, resumable=True)
                    req = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
                    
                    resp = None
                    while resp is None:
                        stat, resp = req.next_chunk()
                        if stat: print(f"Uploading... {int(stat.progress()*100)}%")
                    
                    # SUCCESS
                    sheet.update_cell(row_num, 9, "DONE") # Status column
                    # Assumes YouTube Link is Col 10 (J in Content_Sheet)
                    sheet.update_cell(row_num, 10, f"https://youtu.be/{resp['id']}") 
                    print(f"🎉 SUCCESS! Video Uploaded: {resp['id']}")
                    
                    post_processed = True
                    if os.path.exists(temp_file): os.remove(temp_file)
                    break
                
                else:
                    sheet.update_cell(row_num, 9, "Download Error")
                    if os.path.exists(temp_file): os.remove(temp_file)
                    print("❌ Upload Skipped: Download Error.")
                    break

        if not post_processed:
            print("😴 No PENDING Content YouTube posts found.")

    except Exception as e:
        print(f"❌ Processing Error: {e}")
        
if __name__ == "__main__":
    main()
