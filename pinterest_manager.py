import os
import time
import requests
import gspread
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
    
    import json
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def post_to_pinterest(brand_name, image_url, title, description):
    print(f"📌 Preparing pin for: {brand_name}")
    
    brand_data = BRAND_TOKENS.get(brand_name)
    if not brand_data:
        print(f"⚠️ Brand '{brand_name}' configuration not found.")
        return False
        
    access_token = os.environ.get(brand_data['token'])
    board_id = os.environ.get(brand_data['board'])
    
    if not access_token or not board_id:
        print(f"❌ Missing Secrets for {brand_name}")
        return False

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
            print(f"✅ PIN SUCCESS: {brand_name}")
            return True
        else:
            print(f"❌ PIN FAILED: {response.text}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def run_pinterest_automation():
    print("🚀 Pinterest Automation Started (Sheet Fixed)...")
    client = get_google_client()
    
    sheet_url = os.environ.get('SHEET_CONTENT_URL')
    if not sheet_url:
        print("❌ Sheet URL not found")
        return

    # Have aapne 'Pending_Uploads' tab j kholishu
    try:
        sheet = client.open_by_url(sheet_url).worksheet("Pending_Uploads")
    except:
        print("❌ Error: Tab name 'Pending_Uploads' not found. Please rename 'Sheet1' to 'Pending_Uploads'")
        return

    data = sheet.get_all_records()
    
    for i, row in enumerate(data, start=2):
        # Tamari sheet mujab column names
        status = row.get("Status", "")
        platform = row.get("Platform", "")
        
        if status != "Done" and platform.lower() == "pinterest":
            # Mapping columns from YOUR sheet
            brand = row.get("Account_Name")  # 'Brand Name' badle 'Account_Name'
            img = row.get("Video_URL")       # 'Image_URL' badle 'Video_URL'
            title = row.get("Caption")       # 'Title' badle 'Caption'
            
            # Description ma Caption + Tags banne mix kariye
            desc = f"{row.get('Caption')} \n\n {row.get('Tags')}"
            
            if post_to_pinterest(brand, img, title, desc):
                sheet.update_cell(i, 8, "Done") # Column H (8) ma Done lakho
                time.sleep(2)

if __name__ == "__main__":
    run_pinterest_automation()
