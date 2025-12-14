import os
import time
import requests
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURATION ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Brand Mapping: Sheet Name vs Secret Name
# (Aa mapping thi bot ne khabar padse ke kai brand mate kyo token vaparvo)
BRAND_TOKENS = {
    "Diamond Dice": {"token": "PINTEREST_TOKEN_DIAMOND", "board": "PINTEREST_BOARD_DIAMOND"},
    "Pearl Verse": {"token": "PINTEREST_TOKEN_PEARL", "board": "PINTEREST_BOARD_PEARL"},
    "Luxivibe": {"token": "PINTEREST_TOKEN_LUXIVIBE", "board": "PINTEREST_BOARD_LUXIVIBE"},
    "Urban Glint": {"token": "PINTEREST_TOKEN_URBAN", "board": "PINTEREST_BOARD_URBAN"},
    "Grand Orbit": {"token": "PINTEREST_TOKEN_GRAND", "board": "PINTEREST_BOARD_GRAND"},
    "Royal Nexus": {"token": "PINTEREST_TOKEN_ROYAL", "board": "PINTEREST_BOARD_ROYAL"},
    "Opus Elite": {"token": "PINTEREST_TOKEN_OPUS", "board": "PINTEREST_BOARD_OPUS"},
}

def get_google_client():
    """Google Cloud Connection (Fixed Version)"""
    creds_json = os.environ.get('GCP_CREDENTIALS')
    if not creds_json:
        raise ValueError("GCP_CREDENTIALS not found!")
    
    import json
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def post_to_pinterest(brand_name, image_url, title, description):
    """Pinterest API Logic"""
    print(f"📌 Preparing pin for: {brand_name}")
    
    # 1. Credentials Melvo
    brand_data = BRAND_TOKENS.get(brand_name)
    if not brand_data:
        print(f"⚠️ Brand '{brand_name}' configuration not found.")
        return False
        
    access_token = os.environ.get(brand_data['token'])
    board_id = os.environ.get(brand_data['board'])
    
    if not access_token or not board_id:
        print(f"❌ Missing Secrets for {brand_name}")
        return False

    # 2. Pinterest API Call
    url = "https://api.pinterest.com/v5/pins"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "board_id": board_id,
        "media_source": {
            "source_type": "image_url",
            "url": image_url
        },
        "title": title,
        "description": description
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            print(f"✅ PIN SUCCESS: {brand_name} - {title}")
            return True
        else:
            print(f"❌ PIN FAILED: {response.text}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def run_pinterest_automation():
    print("🚀 Pinterest Automation Started...")
    client = get_google_client()
    
    # Content Sheet URL environment variable mathi lavo
    sheet_url = os.environ.get('SHEET_CONTENT_URL')
    if not sheet_url:
        print("❌ Sheet URL not found")
        return

    sheet = client.open_by_url(sheet_url).worksheet("Pending_Uploads")
    data = sheet.get_all_records()
    
    # Loop through rows
    for i, row in enumerate(data, start=2): # Header pachi start karo
        status = row.get("Status", "")
        platform = row.get("Platform", "")
        
        # Jo Status "Done" na hoy ANE Platform Pinterest hoy
        if status != "Done" and platform.lower() == "pinterest":
            brand = row.get("Brand Name")
            img = row.get("Image_URL")
            title = row.get("Title")
            desc = row.get("Description")
            
            if post_to_pinterest(brand, img, title, desc):
                # Update Status to Done
                sheet.update_cell(i, 6, "Done") # Column F (6) ma Done lakho
                time.sleep(2) # Thodu rest lo

if __name__ == "__main__":
    run_pinterest_automation()
