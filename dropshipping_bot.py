import os
import io
import requests 
import time 
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from datetime import datetime

# Configuration File માંથી ડેટા લો
import get_ids

# --- GLOBAL CONFIGURATION SETUP ---
CREDENTIALS_FILE = get_ids.GOOGLE_CREDENTIALS_FILE 
SCOPES = ['https://www.googleapis.com/auth/drive'] 

# --- UTILITY FUNCTIONS ---

def authenticate_drive():
    """Service account key નો ઉપયોગ કરીને Google Drive સાથે Authentication કરે છે."""
    try:
        creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        print("✅ Google Drive Authentication Successful.")
        return service
    except Exception as e:
        print(f"❌ ERROR during Drive authentication: {e}")
        return None

def find_and_download_content(service):
    """Google Drive માંથી સૌથી જૂની ફાઈલ શોધીને ડાઉનલોડ કરે છે."""
    try:
        folder_id = get_ids.GOOGLE_DRIVE_FOLDER_ID
        query = (f"'{folder_id}' in parents and " 
                 "mimeType != 'application/vnd.google-apps.folder' and "
                 "trashed = false")
        
        results = service.files().list(
            q=query,
            orderBy='createdTime', pageSize=1, fields="files(id, name, mimeType)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            print("❌ ERROR: Google Drive માં પોસ્ટ કરવા માટે કોઈ નવી ફાઈલ નથી.")
            return None, None, None, None

        target_file = items[0]
        # [Content Download Logic remains the same]
        
        file_id = target_file['id']
        file_name = target_file['name']
        mime_type = target_file['mimeType']
        
        print(f"✅ Content Found: '{file_name}' (ID: {file_id})")

        if not os.path.exists("downloads"): os.makedirs("downloads")
        local_file_path = os.path.join("downloads", file_name)
        
        request = service.files().get_media(fileId=file_id)
        file_handle = io.FileIO(local_file_path, 'wb')
        
        downloader = MediaIoBaseDownload(file_handle, request)
        done = False
        while done is False: status, done = downloader.next_chunk()
        
        print(f"✅ Content Downloaded Successfully to: {local_file_path}")
        
        return file_id, local_file_path, file_name, mime_type
        
    except Exception as e:
        print(f"❌ ERROR during file finding/download: {e}")
        return None, None, None, None

def delete_file_from_drive(service, file_id):
    """પોસ્ટ થયા પછી Google Drive માંથી ફાઈલ ડીલીટ કરે છે."""
    try:
        service.files().delete(fileId=file_id).execute()
        print(f"✅ Cleanup: Original file (ID: {file_id}) deleted from Google Drive.")
        return True
    except Exception as e:
        print(f"❌ ERROR during Drive file deletion: {e}")
        return False

def get_page_access_token(page_id, access_token):
    """User Token નો ઉપયોગ કરીને Page Access Token મેળવે છે (સૌથી નિર્ણાયક પગલું)."""
    # આ API call જ Page Access Token મેળવવા માટેની ચાવી છે
    url_pat = f"https://graph.facebook.com/v19.0/{page_id}?fields=access_token&access_token={access_token}"
    response_pat = requests.get(url_pat).json()
    
    pat = response_pat.get('access_token')
    
    if not pat:
        print(f"❌ ERROR: Page Access Token retrieval failed. Response: {response_pat.get('error', {}).get('message', 'No message')[:100]}...")
        return None
    
    return pat

def post_to_instagram(page_id, insta_id, local_path, caption, access_token):
    """Image/Video ને Instagram પર પોસ્ટ કરવા માટેનું API લોજિક."""
    print(f"\n---> Attempting post on FB Page {page_id}...")
    
    # 1. Page Access Token મેળવો (User Token નો ઉપયોગ કરીને)
    page_access_token = get_page_access_token(page_id, access_token)

    if not page_access_token:
        print("❌ POST FAILED: Could not retrieve Page Access Token.")
        return False
    
    # 2. Image/Video Upload કરો (Creation API)
    file_extension = os.path.splitext(local_path)[1].lower()
    
    if file_extension in ['.jpg', '.jpeg', '.png']:
        upload_url = f"https://graph.facebook.com/v19.0/{insta_id}/media"
        params = {'caption': caption, 'access_token': page_access_token}
        files = {'image': open(local_path, 'rb')}
        
        try:
            response = requests.post(upload_url, data=params, files=files)
            response.raise_for_status()
            creation_id = response.json().get('id')
            print(f"✅ Image Uploaded. Creation ID: {creation_id}")
        except Exception as e:
            print(f"❌ ERROR during image upload (Step 2): {response.text if response else e}")
            return False
        finally:
            files['image'].close()
    else:
        print(f"❌ ERROR: Unsupported file type: {file_extension}. Only JPG/PNG supported.")
        return False

    # 3. કન્ટેન્ટ Publish કરો
    if creation_id:
        publish_url = f"https://graph.facebook.com/v19.0/{insta_id}/media_publish"
        params_publish = {'creation_id': creation_id, 'access_token': page_access_token}
        
        try:
            response_publish = requests.post(publish_url, params=params_publish)
            response_publish.raise_for_status()
            print("✅ Content Posted Successfully to Instagram!")
            return True
        except Exception as e:
            # Retrying publish in case of temporary Instagram processing delay
            print(f"⚠️ Publish failed initially. Retrying in 5s...")
            time.sleep(5)
            try:
                response_publish = requests.post(publish_url, params=params_publish)
                response_publish.raise_for_status()
                print("✅ Content Posted Successfully to Instagram (Retry Success)!")
                return True
            except Exception:
                print(f"❌ ERROR during publishing (Final Fail).")
                return False
        
    return False

# --- MAIN EXECUTION ---

def run_automation():
    """મુખ્ય ઓટોમેશન ફ્લો ચલાવે છે."""
    
    drive_service = authenticate_drive() 
    
    if drive_service:
        file_id, local_path, file_name, mime_type = find_and_download_content(drive_service)
        
        if local_path:
            print(f"\n--- Ready to Post: {local_path} ---")
            
            post_success_count = 0
            
            # Caption
            caption_base = file_name.split('.')[0]
            caption = (f"🔥 New Stock Alert! Check out the latest {caption_base} from our collection!\n"
                       f"#Dropshipping #Fashion #Luxury #{caption_base.replace(' ', '')}")
            
            # INSTAGRAM_IDS ડિક્શનરી પર loop ફેરવો
            for page_id, insta_id in get_ids.INSTAGRAM_IDS.items():
                
                is_success = post_to_instagram(
                    page_id=page_id,
                    insta_id=insta_id,
                    local_path=local_path,
                    caption=caption,
                    access_token=get_ids.ACCESS_TOKEN # User Token વાપરીએ છીએ
                )
                
                if is_success:
                    post_success_count += 1
            
            # --- CLEANUP ---
            if post_success_count > 0:
                delete_file_from_drive(drive_service, file_id)
            
            try:
                os.remove(local_path)
                print(f"✅ Cleanup: Local file deleted: {local_path}")
            except Exception as e:
                print(f"❌ ERROR: Could not delete local file: {e}")
                
            print(f"\n--- Dropshipping Automation Finished. Total Successes: {post_success_count} ---")
            
        else:
            print("\n--- Exiting: No content to post. ---")

if __name__ == '__main__':
    run_automation()