import os
import requests

# ---------------- CONFIGURATION ---------------- #
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")

# 🔥 DIRECT ID (This is 100% Correct)
TARGET_IG_ID = "17841479516066757" 

def post_to_instagram():
    print("🚀 STARTING DIRECT POST INJECTION...")  # <-- આ લાઈન આવવી જોઈએ!

    # 🔥 DIRECT IMAGE LINK (Wikipedia Link - 100% Working)
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/Image_created_with_a_mobile_phone.png/640px-Image_created_with_a_mobile_phone.png"
    
    caption = "Final Victory Post! System is working perfectly. #PearlVerse #Success"

    print(f"📸 Image to Upload: {image_url}")
    print(f"🎯 Target Account ID: {TARGET_IG_ID}")

    # ---------------- STEP 1: UPLOAD IMAGE CONTAINER ---------------- #
    post_url = f"https://graph.facebook.com/v19.0/{TARGET_IG_ID}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": FB_ACCESS_TOKEN
    }
    
    print("📤 Uploading Image Container...")
    response = requests.post(post_url, data=payload)
    
    if response.status_code == 200:
        creation_id = response.json().get("id")
        print(f"✅ Container Created! ID: {creation_id}")
        
        # ---------------- STEP 2: PUBLISH CONTAINER ---------------- #
        publish_url = f"https://graph.facebook.com/v19.0/{TARGET_IG_ID}/media_publish"
        pub_payload = {
            "creation_id": creation_id,
            "access_token": FB_ACCESS_TOKEN
        }
        
        print("🚀 Publishing to Instagram Feed...")
        pub_response = requests.post(publish_url, data=pub_payload)
        
        if pub_response.status_code == 200:
            print("🏆 VICTORY! POST PUBLISHED SUCCESSFULLY! 🥳")
        else:
            print(f"❌ Publish Failed: {pub_response.text}")
    else:
        print(f"❌ Upload Failed: {response.text}")

if __name__ == "__main__":
    post_to_instagram()
