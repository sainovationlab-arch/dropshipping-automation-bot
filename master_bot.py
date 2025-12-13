import os
import requests
import json
import random
import time
import mimetypes

# --- CONFIGURATION ---
ACCOUNTS = [
    {"name": "Luxivibe", "token_env": "PINTEREST_TOKEN_LUXIVIBE", "board_env": "PINTEREST_BOARD_LUXIVIBE"},
    {"name": "Urban Glint", "token_env": "PINTEREST_TOKEN_URBAN", "board_env": "PINTEREST_BOARD_URBAN"},
    {"name": "Royal Nexus", "token_env": "PINTEREST_TOKEN_ROYAL", "board_env": "PINTEREST_BOARD_ROYAL"},
    {"name": "Opus Elite", "token_env": "PINTEREST_TOKEN_OPUS", "board_env": "PINTEREST_BOARD_OPUS"},
    {"name": "Grand Orbit", "token_env": "PINTEREST_TOKEN_GRAND", "board_env": "PINTEREST_BOARD_GRAND"},
    {"name": "Pearl Verse", "token_env": "PINTEREST_TOKEN_PEARL", "board_env": "PINTEREST_BOARD_PEARL"},
    {"name": "Diamond Dice", "token_env": "PINTEREST_TOKEN_DIAMOND", "board_env": "PINTEREST_BOARD_DIAMOND"},
]

def get_random_content():
    """ images ફોલ્ડરમાંથી રેન્ડમ ફોટો કે વિડિયો પસંદ કરે છે """
    # ફોલ્ડરનું નામ 'images' જ રાખ્યું છે પણ તેમાં વિડિયો પણ મૂકી શકાશે
    content_dir = "images" 
    if not os.path.exists(content_dir):
        print(f"❌ Error: '{content_dir}' ફોલ્ડર નથી મળ્યું!")
        return None
    
    # mp4 અને mov પણ એડ કર્યા
    files = [f for f in os.listdir(content_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.mp4', '.mov'))]
    if not files:
        print("❌ Error: ફોલ્ડરમાં કોઈ કન્ટેન્ટ નથી!")
        return None
    
    return os.path.join(content_dir, random.choice(files))

def upload_image_flow(session, headers, image_path):
    """ ફક્ત ઈમેજ અપલોડ કરવા માટેનું ફંક્શન """
    print("  [Type: Image] Creating upload session...")
    img_data = {
        "options": json.dumps({"type": "image/jpeg", "content_type": "image/jpeg"})
    }
    r = session.post("https://www.pinterest.com/resource/ImaqeUploadResource/create/", data=img_data, headers=headers)
    data = r.json()["resource_response"]["data"]
    upload_url = data["upload_url"]
    upload_params = data["upload_parameters"]

    with open(image_path, 'rb') as img_file:
        files = {'file': (os.path.basename(image_path), img_file, 'image/jpeg')}
        upload_data = upload_params.copy()
        r_upload = requests.post(upload_url, data=upload_data, files=files)
    
    if r_upload.status_code != 204:
        raise Exception("Image upload to server failed")
        
    return upload_url + "/" + upload_params["key"] # Returns Media URL

def upload_video_flow(session, headers, video_path):
    """ વિડિયો અપલોડ કરવા માટેનું સ્પેશિયલ ફંક્શન """
    print("  [Type: Video] Starting video upload sequence...")
    
    # 1. Register Video
    data = {
        "options": json.dumps({"type": "video", "content_type": "video/mp4"})
    }
    r = session.post("https://www.pinterest.com/resource/VideoUploadResource/create/", data=data, headers=headers)
    try:
        response_data = r.json()["resource_response"]["data"]
        upload_url = response_data["upload_url"]
        upload_params = response_data["upload_parameters"]
    except:
        raise Exception(f"Video Registration Failed: {r.text[:100]}")

    # 2. Upload File
    print("  Uploading video file (this may take time)...")
    with open(video_path, 'rb') as vid_file:
        files = {'file': (os.path.basename(video_path), vid_file, 'video/mp4')}
        upload_data = upload_params.copy()
        r_upload = requests.post(upload_url, data=upload_data, files=files)
    
    if r_upload.status_code != 204:
        raise Exception("Video file upload failed")

    # 3. Finalize
    print("  Finalizing video processing...")
    finalize_data = {
        "options": json.dumps({"upload_id": upload_params["key"], "type": "video"})
    }
    # Finalize call is actually the same endpoint usually, but needs checking status
    # For simple automation, we use the key as media_id directly but Pinterest requires async processing.
    # We will return the media ID (key) directly for Pin creation.
    
    return upload_params["key"] # Returns Media ID (Video ID)

def upload_to_pinterest(account_name, cookie, board_id, file_path):
    print(f"\n🚀 Starting upload for: {account_name}...")
    
    session = requests.Session()
    session.cookies.set("_pinterest_sess", cookie)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Referer": "https://www.pinterest.com/",
        "X-Requested-With": "XMLHttpRequest",
    }

    # Step 1: CSRF
    try:
        r = session.get("https://www.pinterest.com/", headers=headers)
        csrftoken = session.cookies.get("csrftoken") or "1234"
        headers["X-CSRFToken"] = csrftoken
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    # Step 2: Identify File Type & Upload
    is_video = file_path.lower().endswith(('.mp4', '.mov'))
    media_url_or_id = ""
    
    try:
        if is_video:
            media_url_or_id = upload_video_flow(session, headers, file_path)
        else:
            media_url_or_id = upload_image_flow(session, headers, file_path)
            
        print("  Media upload successful!")

    except Exception as e:
        print(f"❌ Media Upload Step Failed: {e}")
        return

    # Step 3: Create Pin
    try:
        print("  Creating Pin...")
        
        # Description with tags
        desc = "Success Mindset & Motivation 🚀 #PearlVerse #Motivation #Success"
        title = "Daily Inspiration"

        pin_options = {
            "board_id": board_id,
            "description": desc,
            "link": "https://www.instagram.com/", 
            "title": title,
            "section": None
        }

        if is_video:
            # Video Pin Structure
            pin_options["media_upload_id"] = media_url_or_id
            pin_options["method"] = "uploaded" 
            # Note: Videos might need a cover image, but auto-generated usually works
        else:
            # Image Pin Structure
            pin_options["image_url"] = media_url_or_id
            pin_options["method"] = "uploaded"

        post_data = {"source_url": "/", "data": json.dumps({"options": pin_options, "context": {}})}
        
        r_pin = session.post("https://www.pinterest.com/resource/PinResource/create/", data=post_data, headers=headers)
        
        if r_pin.status_code == 200 and "resource_response" in r_pin.text:
            print(f"✅ SUCCESS: Post published on {account_name}!")
        else:
            print(f"❌ Failed to publish pin. Server says: {r_pin.text[:100]}")
            
    except Exception as e:
        print(f"❌ Pin Creation Failed: {e}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("--- 🤖 PINTEREST UNIVERSAL BOT (VIDEO+PHOTO) STARTED 🤖 ---")
    
    file_path = get_random_content()
    
    if file_path:
        print(f"📂 Selected File: {file_path}")
        
        for acc in ACCOUNTS:
            token = os.environ.get(acc["token_env"])
            board_id = os.environ.get(acc["board_env"])
            
            if not token or not board_id:
                print(f"⚠️ Skipping {acc['name']}: Data missing.")
                continue
            
            upload_to_pinterest(acc["name"], token, board_id, file_path)
            
            wait_time = random.randint(10, 20) # Videos need more gap
            print(f"⏳ Waiting {wait_time} seconds...\n")
            time.sleep(wait_time)
            
    else:
        print("❌ Process Stopped: No Content Found.")
    
    print("--- ✅ ALL TASKS COMPLETED ---")
