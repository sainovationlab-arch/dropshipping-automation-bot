import os
import time
import requests
import gspread
import json
from google.oauth2.service_account import Credentials

# --- CONFIGURATION ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Brand Mapping
BRAND_TOKENS = {
    "Diamond Dice": {"token": "PINTEREST_TOKEN_DIAMOND", "board": "PINTEREST_BOARD_DIAMOND"},
    "Pearl Verse": {"token": "PINTEREST_TOKEN_PEARL", "board": "PINTEREST_BOARD_PEARL"},
    "Luxivibe": {"token": "PINTEREST_TOKEN_LUXIVIBE", "board": "PINTEREST_BOARD_LUXIVIBE"},
    "Urban Glint": {"token": "PINTEREST_TOKEN_URBAN", "board": "PINTEREST_BOARD_URBAN"},
    "Grand Orbit": {"token": "PINTEREST_TOKEN_GRAND", "board": "PINTEREST_BOARD_GRAND"},
    "Royal Nexus": {"token": "PINTEREST_TOKEN_ROYAL", "board": "PINTEREST_BOARD_ROYAL"},
    "Opus Elite": {"token": "PINTEREST_TOKEN_OPUS", "board": "PINTEREST_BOARD_OPUS"},
    "Emerald Edge": {"token": "PINTEREST_TOKEN_EMERALD", "board": "PINTEREST_BOARD_EMERALD"}
}

def get_google_client():
    creds_json = os.environ.get('GCP_CREDENTIALS')
    if not creds_json:
        raise ValueError("GCP_CREDENTIALS not found!")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def download_file(url, filename):
    print(f"⬇️ Downloading video from: {url}")
    if "drive.google.com" in url and "/view" in url:
        try:
            file_id = url.split("/d/")[1].split("/")[0]
            url = f"https://drive.google.com/uc?export=download&id={file_id}"
        except:
            print("❌ Error parsing Drive URL")
            return False
    
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
        else:
            print(f"❌ Download Failed. Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Download Error: {e}")
        return False

def upload_video_to_pinterest(access_token, file_path):
    print("📤 Uploading video to Pinterest Server...")
    # Clean token (Remove spaces/newlines)
    access_token = access_token.strip()
    
    register_url = "https://api.pinterest.com/v5/media"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {"media_type": "video"}
    
    try:
        reg_resp = requests.post(register_url, headers=headers, json=payload)
        if reg_resp.status_code != 201:
            print(f"❌ Media Register Failed: {reg_resp.text}")
            return None
        
        data = reg_resp.json()
        media_id = data['media_id']
        upload_url = data['upload_url']
        upload_params = data['upload_parameters']
        
        with open(file_path, 'rb') as file:
            files = {'file': file}
            up_resp = requests.post(upload_url, data=upload_params, files=files)
            
        if up_resp.status_code != 204:
            print("❌ Video File Upload Failed")
            return None

        print("⏳ Processing Video (Waiting 10s)...")
        for _ in range(5):
            time.sleep(5)
            check_resp = requests.get(f"{register_url}/{media_id}", headers=headers)
            status = check_resp.json().get('status')
            if status == 'succeeded':
                print("✅ Video Processed!")
                return media_id
            elif status == 'failed':
                print("❌ Video Processing Failed on Pinterest")
                return None
        return media_id
    except Exception as e:
        print(f"❌ Upload Error: {e}")
        return None

def create_pin(access_token, board_id, media_id, title, description):
    # Clean token (Remove spaces/newlines)
    access_token = access_token.strip()
    
    url = "https://api.pinterest.com/v5/pins"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {
        "board_id": board_id,
        "media_source": {"source_type": "video_id", "media_id": media_id},
        "title": title,
        "description": description
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code == 201:
        print(f"✅ PIN CREATED: {title}")
        return True
    else:
        print(f"❌ Pin Failed: {resp.text}")
        return False

def run_pinterest_automation():
    print("🚀 Pinterest Video Automation Started...")
    client = get_google_client()
    sheet_url = os.environ.get('SHEET_CONTENT_URL')
    
    if not sheet_url:
        print("❌ Sheet URL missing")
        return

    try:
        sheet = client.open_by_url(sheet_url).worksheet("Pending_Uploads")
    except Exception as e:
        print(f"❌ Error opening sheet: {e}")
        return

    data = sheet.get_all_records()
    print(f"📊 Rows found: {len(data)}")

    for i, row in enumerate(data, start=2):
        status = str(row.get("Status", "")).strip().lower()
        platform = str(row.get("Platform", "")).strip().lower()
        brand = row.get("Account_Name")

        print(f"🔎 Row {i}: Brand='{brand}' | Platform='{platform}' | Status='{status}'")

        if status != "done" and "pinterest" in platform:
            print(f"🎯 MATCH FOUND: Processing Row {i}")
            video_url = row.get("Video_URL")
            caption = row.get("Caption")
            tags = row.get("Tags")
            desc = f"{caption}\n\n{tags}"
            
            brand_config = BRAND_TOKENS.get(brand)
            if not brand_config:
                print(f"⚠️ Brand '{brand}' not configured. Skipping.")
                continue

            video_filename = "temp_video.mp4"
            if download_file(video_url, video_filename):
                # Retrieve tokens safely with stripping
                token = os.environ.get(brand_config['token'], "").strip()
                board = os.environ.get(brand_config['board'], "").strip()
                
                if token and board:
                    media_id = upload_video_to_pinterest(token, video_filename)
                    if media_id:
                        if create_pin(token, board, media_id, caption, desc):
                            sheet.update_cell(i, 8, "Done") # Update status
                            print(f"✅ Row {i} Done!")
                else:
                    print(f"❌ Missing Secrets for {brand}")
            
            if os.path.exists(video_filename):
                os.remove(video_filename)
            print("--------------------------------")

if __name__ == "__main__":
    run_pinterest_automation()
