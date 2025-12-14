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
    """Google Drive Link mathi Video Download kare che"""
    print(f"⬇️ Downloading video...")
    
    # Convert View Link to Download Link
    if "drive.google.com" in url and "/view" in url:
        file_id = url.split("/d/")[1].split("/")[0]
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return True
    return False

def upload_video_to_pinterest(access_token, file_path):
    """Pinterest Media API thi Video Upload kare che"""
    print("📤 Uploading video to Pinterest Server...")
    
    # Step 1: Register Upload
    register_url = "https://api.pinterest.com/v5/media"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {"media_type": "video"}
    
    reg_resp = requests.post(register_url, headers=headers, json=payload)
    if reg_resp.status_code != 201:
        print(f"❌ Media Register Failed: {reg_resp.text}")
        return None
    
    data = reg_resp.json()
    media_id = data['media_id']
    upload_url = data['upload_url']
    upload_params = data['upload_parameters']
    
    # Step 2: Actual File Upload
    with open(file_path, 'rb') as file:
        upload_data = upload_params.copy()
        upload_data['file'] = file
        # Note: requests.post handles multipart automatically if 'files' is passed
        # But we need to pass params as fields and file as files
        # Careful cleanup of params
        files = {'file': file}
        up_resp = requests.post(upload_url, data=upload_params, files=files)
        
    if up_resp.status_code != 204:
        print("❌ Video File Upload Failed")
        return None

    # Step 3: Wait for Processing
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

def create_pin(access_token, board_id, media_id, title, description, cover_url=None):
