import os
import json
import time
import requests
import re
import gspread
from google.oauth2.service_account import Credentials

# ==============================================================================
# 1. CONFIGURATION & MAPPING
# ==============================================================================

# Pinterest Brand Mapping (Brand Name -> Secret Key Name)
BRAND_CONFIG = {
    "Diamond Dice": {"token": "PINTEREST_TOKEN_DIAMOND", "board": "PINTEREST_BOARD_DIAMOND"},
    "Pearl Verse": {"token": "PINTEREST_TOKEN_PEARL", "board": "PINTEREST_BOARD_PEARL"},
    "Luxivibe": {"token": "PINTEREST_TOKEN_LUXIVIBE", "board": "PINTEREST_BOARD_LUXIVIBE"},
    "Urban Glint": {"token": "PINTEREST_TOKEN_URBAN", "board": "PINTEREST_BOARD_URBAN"},
    "Grand Orbit": {"token": "PINTEREST_TOKEN_GRAND", "board": "PINTEREST_BOARD_GRAND"},
    "Royal Nexus": {"token": "PINTEREST_TOKEN_ROYAL", "board": "PINTEREST_BOARD_ROYAL"},
    "Opus Elite": {"token": "PINTEREST_TOKEN_OPUS", "board": "PINTEREST_BOARD_OPUS"},
    "Emerald Edge": {"token": "PINTEREST_TOKEN_EMERALD", "board": "PINTEREST_BOARD_EMERALD"}
}

# ==============================================================================
# 2. HELPER FUNCTIONS
# ==============================================================================

def get_env_var(keys):
    """Find secret from environment variables"""
    for key in keys:
        val = os.environ.get(key)
        if val: return val
    return None

def get_val(row, keys):
    """Smart Column Reader"""
    normalized_row = {k.lower().replace(" ", "").replace("_", ""): v for k, v in row.items()}
    for key in keys:
        if key in row: return str(row[key]).strip()
        norm_key = key.lower().replace(" ", "").replace("_", "")
        if norm_key in normalized_row: return str(normalized_row[norm_key]).strip()
    return ""

def get_sheet_service():
    """Connect to Google Sheet"""
    creds_json = get_env_var(["GCP_CREDENTIALS", "GOOGLE_CREDENTIALS"])
    if not creds_json:
        print("❌ FATAL: GCP_CREDENTIALS missing.")
        return None
    
    try:
        creds = Credentials.from_service_account_info(
            json.loads(creds_json), 
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        client = gspread.authorize(creds)
        
        # Try finding Sheet URL/ID from Secrets
        sheet_id = get_env_var(["SHEET_CONTENT_URL", "SPREADSHEET_ID", "SHEET_DROPSHIPPING_URL"])
        if not sheet_id:
            print("❌ Sheet ID missing in Secrets.")
            return None

        if "docs.google.com" in sheet_id:
            return client.open_by_url(sheet_id).sheet1
        return client.open_by_key(sheet_id).sheet1
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

def download_video(url, filename):
    print(f"⬇️ Downloading: {url}")
    # Drive Link Converter
    if "drive.google.com" in url:
        m = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
        id_val = m.group(1) if m else (re.search(r"id=([a-zA-Z0-9_-]+)", url).group(1) if re.search(r"id=([a-zA-Z0-9_-]+)", url) else None)
        if id_val: url = f"https://drive.google.com/uc?export=download&confirm=t&id={id_val}"
    
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        return True
    except Exception as e:
        print(f"❌ Download Failed: {e}")
        return False

# ==============================================================================
# 3. PINTEREST API FUNCTIONS (v5)
# ==============================================================================

def upload_video_v5(access_token, file_path):
    print("📤 Registering Upload with Pinterest...")
    auth_headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    
    # 1. Register
    try:
        reg = requests.post("https://api.pinterest.com/v5/media", headers=auth_headers, json={"media_type": "video"})
        if reg.status_code != 201:
            print(f"❌ Register Failed: {reg.text}")
            return None
        
        data = reg.json()
        media_id = data['media_id']
        upload_url = data['upload_url']
        params = data['upload_parameters']
        
        # 2. Upload File
        print("📤 Uploading bytes...")
        with open(file_path, 'rb') as f:
            up = requests.post(upload_url, data=params, files={'file': f})
            if up.status_code != 204:
                print(f"❌ Upload Failed: {up.status_code}")
                return None
        
        # 3. Check Status
        print("⏳ Processing Video (Waiting 10s)...")
        for _ in range(6):
            time.sleep(5)
            chk = requests.get(f"https://api.pinterest.com/v5/media/{media_id}", headers=auth_headers).json()
            status = chk.get('status')
            print(f"   Status: {status}")
            if status == 'succeeded': return media_id
            if status == 'failed': return None
            
        return media_id # Try anyway if stuck in processing
        
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None

def create_pin_v5(access_token, board_id, media_id, title, desc, link):
    print(f"📌 Creating Pin on Board: {board_id}")
    url = "https://api.pinterest.com/v5/pins"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    
    payload = {
        "board_id": board_id,
        "media_source": {"source_type": "video_id", "media_id": media_id},
        "title": title[:100],
        "description": desc[:500],
    }
    if link and "http" in link: payload["link"] = link
    
    r = requests.post(url, headers=headers, json=payload)
    if r.status_code == 201:
        print(f"✅ PIN SUCCESS! ID: {r.json()['id']}")
        return True
    else:
        print(f"❌ Pin Failed: {r.text}")
        return False

# ==============================================================================
# 4. MAIN RUNNER
# ==============================================================================

def run_pinterest_bot():
    print("🚀 Pinterest Bot Started...")
    sheet = get_sheet_service()
    if not sheet: return

    try:
        all_values = sheet.get_all_values()
        headers = [str(h).strip() for h in all_values[0]]
        print(f"📊 Headers: {headers}")
        
        # Find Columns
        def find_col(names):
            for i, h in enumerate(headers):
                if h.lower().replace(" ","").replace("_","") in [n.lower().replace(" ","").replace("_","") for n in names]: return i + 1
            return None

        status_col = find_col(['Status'])
        platform_col = find_col(['Platform'])
        
        if not status_col or not platform_col:
            print("❌ Need 'Status' and 'Platform' columns.")
            return

        # Process Rows
        for i, raw_row in enumerate(all_values[1:]):
            row_num = i + 2
            row = {headers[k]: v for k, v in enumerate(raw_row) if k < len(headers)}
            
            status = get_val(row, ['Status']).upper()
            platform = get_val(row, ['Platform']).lower()
            
            if status == 'PENDING' and 'pinterest' in platform:
                brand = get_val(row, ['Brand_Name', 'Account_Name', 'Brand'])
                print(f"\n--- Processing Row {row_num}: {brand} ---")
                
                # Get Secrets for Brand
                config = BRAND_CONFIG.get(brand)
                if not config:
                    print(f"⚠️ No config found for brand: {brand}")
                    continue
                
                token = os.environ.get(config['token'])
                board = os.environ.get(config['board'])
                
                if not token or not board:
                    print(f"❌ Missing Secrets for {brand}. Check GitHub Settings.")
                    continue
                
                # Prepare Data
                video_url = get_val(row, ['Video_URL'])
                title = get_val(row, ['Title_Hook', 'Title'])
                desc = get_val(row, ['Description', 'Caption'])
                tags = get_val(row, ['Caption_Hashtags', 'Tags'])
                link = get_val(row, ['Link', 'Product_Link']) # Link to product or YouTube
                
                full_desc = f"{desc}\n\n{tags}"
                
                # Execute
                sheet.update_cell(row_num, status_col, 'PROCESSING')
                
                temp_file = "temp_pin.mp4"
                if download_video(video_url, temp_file):
                    media_id = upload_video_v5(token, temp_file)
                    if media_id:
                        if create_pin_v5(token, board, media_id, title, full_desc, link):
                            sheet.update_cell(row_num, status_col, 'DONE')
                        else:
                            sheet.update_cell(row_num, status_col, 'FAIL_PIN')
                    else:
                        sheet.update_cell(row_num, status_col, 'FAIL_UPLOAD')
                    
                    if os.path.exists(temp_file): os.remove(temp_file)
                else:
                    sheet.update_cell(row_num, status_col, 'FAIL_DL')

    except Exception as e:
        print(f"❌ System Error: {e}")

if __name__ == "__main__":
    run_pinterest_bot()
