import os
import requests

# ---------------- CONFIGURATION ---------------- #
# ટોકન ગિટહબના ખજાનામાંથી આવશે
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")

# 🔥 FIX NO. 1: DIRECT INSTAGRAM ID (NO SEARCHING)
# આ ID આપણે તમારા લોગમાંથી શોધ્યું છે, જે 100% સાચું છે.
TARGET_IG_ID = "17841479516066757" 

def post_to_instagram():
    print("🚀 STARTING DIRECT POST INJECTION...")

    # 🔥 FIX NO. 2: DIRECT IMAGE LINK (BYPASSING GOOGLE SHEET)
    # આપણે શીટમાંથી વાંચવું જ નથી, સીધી સાચી લિંક અહીં આપી દઈએ.
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/Image_created_with_a_mobile_phone.png/640px-Image_created_with_a_mobile_phone.png"
    caption = "System Success! This is a direct automated post. #PearlVerse #Victory"

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
            print("👉 Check your Instagram now!")
        else:
            print(f"❌ Publish Failed: {pub_response.text}")
    else:
        print(f"❌ Upload Failed: {response.text}")
        print("⚠️ NOTE: If this fails, check your Token permissions again.")

if __name__ == "__main__":
    post_to_instagram()
