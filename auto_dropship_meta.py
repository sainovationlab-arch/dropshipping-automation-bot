import os
import json
import time
import gspread
import requests
from google.oauth2.service_account import Credentials

# 👇 શીટનું નામ
SHEET_NAME = "Dropshipping_Sheet"

def get_instagram_id(page_id, access_token):
    """ Facebook Page ID પરથી Instagram ID શોધે છે """
    url = f"https://graph.facebook.com/v18.0/{page_id}?fields=instagram_business_account&access_token={access_token}"
    resp = requests.get(url)
    data = resp.json()
    if 'instagram_business_account' in data:
        return data['instagram_business_account']['id']
    return None

def post_to_instagram(ig_user_id, media_url, caption, access_token):
    """ Instagram પર પોસ્ટ કરે છે (2 Steps: Container -> Publish) """
    # Step 1: Create Container
    url_container = f"https://graph.facebook.com/v18.0/{ig_user_id}/media"
    payload = {
        'image_url': media_url,
        'caption': caption,
        'access_token': access_token
    }
    # Video handling
    if ".mp4" in media_url or "video" in media_url:
        payload = {
            'video_url': media_url,
            'media_type': 'VIDEO',
            'caption': caption,
            'access_token': access_token
        }

    resp = requests.post(url_container, data=payload)
    if resp.status_code != 200:
        return None, f"Container Error: {resp.text}"
    
    creation_id = resp.json().get('id')
    
    # Wait needed for video processing
    time.sleep(5) 

    # Step 2: Publish Container
    url_publish = f"https://graph.facebook.com/v18.0/{ig_user_id}/media_publish"
    payload_pub = {
        'creation_id': creation_id,
        'access_token': access_token
    }
    resp_pub = requests.post(url_publish, data=payload_pub)
    
    if resp_pub.status_code == 200:
        return resp_pub.json().get('id'), "SUCCESS"
    else:
        return None, f"Publish Error: {resp_pub.text}"

def main():
    print("🚀 ALL-IN-ONE META BOT STARTED...")
    
    # 1. SETUP SHEETS
    try:
        creds_json = os.environ.get('GCP_CREDENTIALS')
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open(SHEET_NAME).get_worksheet(0)
    except Exception as e:
        print(f"❌ Sheet Error: {e}")
        return

    # 2. PROCESS ROW 2 (Testing)
    try:
        row_values = sheet.row_values(2)
        if not row_values or len(row_values) < 9:
            print("❌ Row 2 incomplete.")
            return

        account_name = str(row_values[2]).strip()   # Col C
        platform = str(row_values[3]).strip().lower() # Col D
        media_url = str(row_values[4]).strip()      # Col E
        caption = str(row_values[5]).strip()        # Col F
        status = str(row_values[8]).strip().upper() # Col I

        if "PENDING" not in status:
            print(f"😴 Status is '{status}', skipping.")
            return

        print(f"🎯 Target: {account_name} on {platform}")

        # 3. FACEBOOK API LOGIN
        user_access_token = os.environ.get('FB_ACCESS_TOKEN')
        
        # Get Page Token & ID
        resp = requests.get(f"https://graph.facebook.com/v18.0/me/accounts?access_token={user_access_token}")
        pages_data = resp.json().get('data', [])
        
        page_token = None
        page_id = None
        
        for page in pages_data:
            if page.get('name').strip().lower() == account_name.lower():
                page_token = page.get('access_token')
                page_id = page.get('id')
                break
        
        if not page_token:
            print(f"❌ Page '{account_name}' not found.")
            return

        # 4. POSTING LOGIC
        post_id = None
        error_msg = ""

        # 👉 FACEBOOK POSTING
        if "facebook" in platform:
            print("📤 Posting to Facebook...")
            if ".mp4" in media_url:
                post_url = f"https://graph.facebook.com/v18.0/{page_id}/videos"
                payload = {'file_url': media_url, 'description': caption, 'access_token': page_token}
            else:
                post_url = f"https://graph.facebook.com/v18.0/{page_id}/photos"
                payload = {'url': media_url, 'caption': caption, 'access_token': page_token}
            
            resp_fb = requests.post(post_url, data=payload)
            if resp_fb.status_code == 200:
                post_id = resp_fb.json().get('id')
            else:
                error_msg = resp_fb.text

        # 👉 INSTAGRAM POSTING
        elif "instagram" in platform:
            print("📸 Posting to Instagram...")
            ig_id = get_instagram_id(page_id, user_access_token) # Note: Using User Token to find IG ID
            
            if not ig_id:
                # Try getting IG ID using Page Token if User Token fails specific permission
                ig_id = get_instagram_id(page_id, page_token)
            
            if ig_id:
                print(f"✅ Found IG ID: {ig_id}")
                post_id, error_msg = post_to_instagram(ig_id, media_url, caption, page_token)
            else:
                error_msg = "Could not find Instagram Business ID linked to this Page."

        # 5. RESULT
        if post_id:
            print(f"🎉 SUCCESS! ID: {post_id}")
            sheet.update_cell(2, 9, "DONE")
            sheet.update_cell(2, 10, f"Posted: {post_id}")
        else:
            print(f"❌ Failed: {error_msg}")
            sheet.update_cell(2, 9, "ERROR")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
