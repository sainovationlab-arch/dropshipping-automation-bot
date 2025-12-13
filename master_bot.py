import os
import requests
import json
import random
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- SHEET URLs from Secrets ---
DROPSHIPPING_SHEET_ID = os.environ.get('SHEET_DROPSHIPPING_URL')
CONTENT_SHEET_ID = os.environ.get('SHEET_CONTENT_URL')

# --- CONFIGURATION (Linking Accounts to Sheets) ---
ACCOUNTS = [
    # Dropshipping Accounts (Sheet 1)
    {"name": "Luxivibe", "token_env": "PINTEREST_TOKEN_LUXIVIBE", "board_env": "PINTEREST_BOARD_LUXIVIBE", "sheet_id": DROPSHIPPING_SHEET_ID},
    {"name": "Urban Glint", "token_env": "PINTEREST_TOKEN_URBAN", "board_env": "PINTEREST_BOARD_URBAN", "sheet_id": DROPSHIPPING_SHEET_ID},
    {"name": "Royal Nexus", "token_env": "PINTEREST_TOKEN_ROYAL", "board_env": "PINTEREST_BOARD_ROYAL", "sheet_id": DROPSHIPPING_SHEET_ID},
    {"name": "Opus Elite", "token_env": "PINTEREST_TOKEN_OPUS", "board_env": "PINTEREST_BOARD_OPUS", "sheet_id": DROPSHIPPING_SHEET_ID},
    {"name": "Grand Orbit", "token_env": "PINTEREST_TOKEN_GRAND", "board_env": "PINTEREST_BOARD_GRAND", "sheet_id": DROPSHIPPING_SHEET_ID},
    
    # Content Creation Accounts (Sheet 2)
    {"name": "Pearl Verse", "token_env": "PINTEREST_TOKEN_PEARL", "board_env": "PINTEREST_BOARD_PEARL", "sheet_id": CONTENT_SHEET_ID},
    {"name": "Diamond Dice", "token_env": "PINTEREST_TOKEN_DIAMOND", "board_env": "PINTEREST_BOARD_DIAMOND", "sheet_id": CONTENT_SHEET_ID},
    # Emerald Edge (Pending)
]

# --- Google Sheets Functions ---
def connect_to_sheet(sheet_id):
    """ Google Sheet ID દ્વારા કનેક્ટ કરે છે """
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    
    if not creds_json:
        print("❌ Error: GOOGLE_SHEETS_CREDENTIALS Secret Missing!")
        return None, None

    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    try:
        # Sheet ID દ્વારા ઓપન કરો
        sheet = client.open_by_key(sheet_id).sheet1 
        return sheet, client
    except Exception as e:
        print(f"❌ Error opening sheet {sheet_id}: {e}")
        return None, None

def get_pending_post(sheet):
    """ શીટમાંથી પહેલી પેન્ડિંગ પોસ્ટ શોધે છે """
    records = sheet.get_all_records()
    row_index = 2 # 2nd row after header

    for row in records:
        # માત્ર Media URL હોય અને Status 'Done' ન હોય તો જ લેવાનું
        if str(row.get('Status', '')).lower() != 'done' and row.get('Media URL'):
            return row, row_index
        row_index += 1
    return None, None

def update_sheet_status(sheet, row_index, status="Done"):
    """ શીટમાં સ્ટેટસ અપડેટ કરે છે """
    try:
        sheet.update_cell(row_index, 5, status) # E Column (5th) is Status
        print(f"✅ Sheet Status Updated to: {status}")
    except Exception as e:
        print(f"❌ Error updating sheet: {e}")

# --- Media Download & Upload Functions (Same as previous, omitted for brevity) ---
def download_media(url):
    """ URL પરથી ફોટો/વિડિયો ડાઉનલોડ કરે છે """
    print(f"📥 Downloading media from: {url}")
    # ... (Same download code as previous response) ...
    try:
        if "drive.google.com" in url and "/file/d/" in url:
            file_id = url.split('/d/')[1].split('/')[0]
            url = f"https://drive.google.com/uc?export=download&id={file_id}"

        r = requests.get(url, allow_redirects=True)
        if r.status_code == 200:
            filename = "temp_media.mp4" if "mp4" in r.headers.get("Content-Type", "") else "temp_media.jpg"
            with open(filename, 'wb') as f:
                f.write(r.content)
            return filename
        else:
            print(f"❌ Download Failed. Status: {r.status_code}")
            return None
    except Exception as e:
        print(f"❌ Download Error: {e}")
        return None

def upload_to_pinterest(account_name, cookie, board_id, file_path, title, desc, link):
    # ... (Same Pinterest upload logic as previous response) ...
    # This logic is long and complex, but remains the same for image/video upload and pin creation.
    # Placeholder for the actual upload function
    
    session = requests.Session()
    session.cookies.set("_pinterest_sess", cookie)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Referer": "https://www.pinterest.com/",
        "X-CSRFToken": "1234"
    }

    # 1. CSRF Setup
    try:
        session.get("https://www.pinterest.com/", headers=headers)
        headers["X-CSRFToken"] = session.cookies.get("csrftoken") or "1234"
    except: pass

    # 2. Upload
    is_video = file_path.endswith('.mp4')
    media_url_or_id = ""
    try:
        # Video Upload Flow (omitted detailed code)
        if is_video:
            data = {"options": json.dumps({"type": "video", "content_type": "video/mp4"})}
            r = session.post("https://www.pinterest.com/resource/VideoUploadResource/create/", data=data, headers=headers)
            up_data = r.json()["resource_response"]["data"]
            with open(file_path, 'rb') as f:
                requests.post(up_data["upload_url"], data=up_data["upload_parameters"], files={'file': f})
            media_url_or_id = up_data["upload_parameters"]["key"]
        # Image Upload Flow (omitted detailed code)
        else:
            data = {"options": json.dumps({"type": "image/jpeg", "content_type": "image/jpeg"})}
            r = session.post("https://www.pinterest.com/resource/ImaqeUploadResource/create/", data=data, headers=headers)
            up_data = r.json()["resource_response"]["data"]
            with open(file_path, 'rb') as f:
                requests.post(up_data["upload_url"], data=up_data["upload_parameters"], files={'file': f})
            media_url_or_id = up_data["upload_url"] + "/" + up_data["upload_parameters"]["key"]
            
    except Exception as e:
        print(f"  ❌ Upload Failed: {e}")
        return False

    # 3. Create Pin
    try:
        options = {
            "board_id": board_id,
            "description": desc,
            "link": link,
            "title": title,
            "section": None,
            "method": "uploaded"
        }
        if is_video:
            options["media_upload_id"] = media_url_or_id
        else:
            options["image_url"] = media_url_or_id

        post_data = {"source_url": "/", "data": json.dumps({"options": options, "context": {}})}
        r_pin = session.post("https://www.pinterest.com/resource/PinResource/create/", data=post_data, headers=headers)
        
        if r_pin.status_code == 200:
            return True
        else:
            print(f"  ❌ Failed on {account_name}. Server said: {r_pin.status_code}")
            return False
    except: return False


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("--- 🤖 PINTEREST MULTI-SHEET BOT STARTED 🤖 ---")
    
    # 1. એકાઉન્ટ્સને શીટ ID પ્રમાણે ગ્રુપ કરો
    sheet_data = {
        DROPSHIPPING_SHEET_ID: {"sheet": None, "pending_post": None, "row_index": None, "accounts": []},
        CONTENT_SHEET_ID: {"sheet": None, "pending_post": None, "row_index": None, "accounts": []},
    }

    # 2. શીટ્સ સાથે કનેક્ટ કરો અને ડેટા પ્રી-ફેચ કરો
    for sheet_id in sheet_data.keys():
        if sheet_id:
            sheet, client = connect_to_sheet(sheet_id)
            if sheet:
                post, row_index = get_pending_post(sheet)
                sheet_data[sheet_id].update({"sheet": sheet, "pending_post": post, "row_index": row_index})

    # 3. દરેક એકાઉન્ટ માટે પ્રોસેસ કરો
    for acc in ACCOUNTS:
        token = os.environ.get(acc["token_env"])
        board_id = os.environ.get(acc["board_env"])
        sheet_id = acc["sheet_id"]
        
        if not token or not board_id or not sheet_id:
            print(f"⚠️ Skipping {acc['name']}: Data (Token/Board/Sheet) missing.")
            continue
            
        sheet_info = sheet_data.get(sheet_id)
        if sheet_info and sheet_info['pending_post']:
            post_data = sheet_info['pending_post']
            row_index = sheet_info['row_index']
            
            # 4. મીડિયા ડાઉનલોડ કરો (કોમન ફાઇલ ડાઉનલોડ થાય)
            file_path = download_media(post_data['Media URL'])
            
            if file_path:
                print(f"\n📌 Posting {post_data['Title']} to {acc['name']}...")
                
                # 5. Pinterest પર અપલોડ કરો
                if upload_to_pinterest(acc['name'], token, board_id, file_path, 
                                        post_data['Title'], post_data['Description'], post_data['Link']):
                    
                    # 6. જો બધા એકાઉન્ટમાં પોસ્ટ થઈ જાય, તો શીટ અપડેટ કરો (આગળની પોસ્ટ પર જઈ શકે તે માટે)
                    sheet_info['accounts'].append(acc['name'])

                # 7. થોડું વેઇટ કરો (Safety)
                wait_time = random.randint(10, 20)
                print(f"⏳ Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                
                # Clean up the downloaded file
                os.remove(file_path)

        else:
            print(f"💤 Skipping {acc['name']}: No pending post found in its sheet.")
            
    # 8. છેલ્લે, જો બધા એકાઉન્ટ (જે તે શીટના) માં પોસ્ટ થઈ જાય તો Status 'Done' કરો
    for sheet_id, info in sheet_data.items():
        if info['sheet'] and info['pending_post']:
            all_posted = True
            # Check if all accounts linked to this sheet have successfully posted
            for acc in ACCOUNTS:
                if acc['sheet_id'] == sheet_id and acc['name'] not in info['accounts']:
                    all_posted = False
                    break
            
            if all_posted:
                 update_sheet_status(info['sheet'], info['row_index'], "Done")
            else:
                 # જો કોઈ એકાઉન્ટમાં ભૂલ આવી હોય તો 'Error' માર્ક કરો
                 # For simplicity, we just leave it pending to try again next time.
                 pass

    print("--- ✅ ALL TASKS COMPLETED ---")
