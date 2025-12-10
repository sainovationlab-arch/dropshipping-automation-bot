import os
import requests

# ---------------- CONFIGURATION ---------------- #
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")
SHEET_ID = "1aBcD..." # (તમારો જૂનો શીટ ID જ રહેશે)

# 🔥 WORLD'S BEST FIX: DIRECT ID MAPPING (NO SEARCHING)
INSTAGRAM_ACCOUNTS = {
    "Pearl Verse": "17841479516066757"  # <-- મેં ID ફિક્સ કરી દીધું!
}

def post_to_instagram():
    print("🚀 STARTING FINAL ATTEMPT WITH HARDCODED ID...")

    # 1. Google Sheet માંથી ડેટા વાંચો (અહીં તમારો જૂનો કોડ જ આવશે)
    # ... (તમારો ડેટા વાંચવાનો કોડ અહી સમજી લેવો)
    
    # ધારો કે શીટમાંથી મળ્યું:
    account_name = "Pearl Verse"
    image_url = "https://images.unsplash.com/..." # (તમે શીટમાં જે મૂક્યું હોય)
    caption = "Final Victory Post! #Success"

    # 2. ID શોધો (ડાયરેક્ટ)
    ig_user_id = INSTAGRAM_ACCOUNTS.get(account_name)
    
    if not ig_user_id:
        print(f"❌ Error: ID for {account_name} not found in script.")
        return

    print(f"✅ FOUND ID DIRECTLY: {ig_user_id}")
    
    # 3. પોસ્ટ કરો (The Final Shot)
    post_url = f"https://graph.facebook.com/v17.0/{ig_user_id}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": FB_ACCESS_TOKEN
    }
    
    print("📤 Uploading Image...")
    response = requests.post(post_url, data=payload)
    
    if response.status_code == 200:
        creation_id = response.json().get("id")
        print(f"✅ Image Uploaded! ID: {creation_id}")
        
        # Publish Container
        publish_url = f"https://graph.facebook.com/v17.0/{ig_user_id}/media_publish"
        pub_payload = {
            "creation_id": creation_id,
            "access_token": FB_ACCESS_TOKEN
        }
        pub_response = requests.post(publish_url, data=pub_payload)
        
        if pub_response.status_code == 200:
            print("🏆 VICTORY! POST PUBLISHED SUCCESSFULLY ON INSTAGRAM!")
        else:
            print(f"❌ Publish Failed: {pub_response.text}")
    else:
        print(f"❌ Upload Failed: {response.text}")
        print("⚠️ HINT: If error says 'Permissions', you MUST add instagram_content_publish in Explorer!")

if __name__ == "__main__":
    post_to_instagram()
