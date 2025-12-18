import os
import requests
import time
from dotenv import load_dotenv

# 1. Load Secrets form .env file
load_dotenv()

# ==========================================
# 👇 AUTOMATIC SETTINGS (Do Not Change)
# ==========================================

# Hu automatic Diamond Dice na ID/Token shodhvano try karu chu
IG_USER_ID = os.getenv("INSTAGRAM_ACCOUNT_ID_DIAMOND")
ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN_DIAMOND")

# Ek "Test Video" nakhu chu (Aa confirm karse ke system chale che ke nahi)
# Aa video 100% Instagram compatible che.
VIDEO_URL = "https://www.w3schools.com/html/mov_bbb.mp4"
CAPTION = "Debug Test - Please Delete Later"

# ==========================================

def debug_instagram_upload():
    print("\n🔍 DIAGNOSIS STARTED...")

    # 1. Check Credentials
    if not IG_USER_ID or not ACCESS_TOKEN:
        print("❌ ERROR: Mane .env file mathi ID ke Token nathi malya!")
        print(f"   IG_USER_ID Found? {'✅' if IG_USER_ID else '❌'}")
        print(f"   ACCESS_TOKEN Found? {'✅' if ACCESS_TOKEN else '❌'}")
        print("👉 Solution: Tamari .env file check karo ke spelling sacha che?")
        return

    print(f"✅ Credentials Found! Testing for Account ID: {IG_USER_ID}")
    
    # 2. Create Media Container
    print("⏳ Step 1: Sending Video to Instagram...")
    url_create = f"https://graph.facebook.com/v18.0/{IG_USER_ID}/media"
    payload = {
        "video_url": VIDEO_URL,
        "media_type": "REELS",
        "caption": CAPTION,
        "access_token": ACCESS_TOKEN
    }
    
    r = requests.post(url_create, data=payload)
    
    # --- ERROR CATCHING ---
    if r.status_code != 200:
        print("\n❌ STEP 1 FAILED (Instagram na padi):")
        error_data = r.json()
        print(f"   Error Message: {error_data.get('error', {}).get('message')}")
        print(f"   Error Type: {error_data.get('error', {}).get('type')}")
        print("-" * 30)
        return
    # ----------------------

    creation_id = r.json().get('id')
    print(f"✅ Success! Container ID: {creation_id}")
    
    # 3. Wait for Processing
    print("⏳ Waiting 30 seconds for processing...")
    for i in range(30, 0, -1):
        print(f"{i}...", end="\r")
        time.sleep(1)
    print("\n")
    
    # 4. Check Status
    status_url = f"https://graph.facebook.com/v18.0/{creation_id}?fields=status_code,status&access_token={ACCESS_TOKEN}"
    stat = requests.get(status_url).json()
    print(f"📊 Processing Status: {stat.get('status_code')} ({stat.get('status')})")
    
    if stat.get('status_code') == 'ERROR':
        print("❌ Video Processing Failed. Instagram doesn't like this video format.")
        return

    # 5. Publish
    print("🚀 Step 2: Publishing Reel...")
    url_publish = f"https://graph.facebook.com/v18.0/{IG_USER_ID}/media_publish"
    pub_payload = {
        "creation_id": creation_id,
        "access_token": ACCESS_TOKEN
    }
    
    pub = requests.post(url_publish, data=pub_payload)
    
    if pub.status_code == 200:
        print("\n✅✅ SUCCESS! TEST PASSED.")
        print("Instagram par jaine juo, ek 'Bunny' walo video post thayo hase.")
        print("👉 Aano matlab: Tamaro Token barabar che, pan Sheet walo Video kharab hato.")
    else:
        print("\n❌ Publishing Failed:")
        print(pub.text)

if __name__ == "__main__":
    debug_instagram_upload()
