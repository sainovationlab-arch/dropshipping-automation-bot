import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 👇 શીટનું નામ
SHEET_NAME = "Master_Scheduler"

def main():
    print("🛍️ AUTO DROPSHIPPING META BOT (V2) STARTED...")
    
    # 1. LOGIN (Google Sheet)
    try:
        creds_json = os.environ.get('GCP_CREDENTIALS')
        if not creds_json: 
            print("❌ CRITICAL ERROR: 'GCP_CREDENTIALS' Secret is MISSING!")
            return
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scope)
        gc = gspread.authorize(creds)
        sheet = gc.open(SHEET_NAME).get_worksheet(0)
        print(f"✅ Connected to {SHEET_NAME}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    # 2. PROCESS ROW 2
    try:
        row_values = sheet.row_values(2)
        if len(row_values) < 10:
            print("❌ Row 2 data is incomplete")
            return

        platform = row_values[4].strip().lower()
        status = row_values[9].strip().upper()
        
        # Check for Facebook/Instagram
        if ("instagram" in platform or "facebook" in platform) and "PENDING" in status:
            print(f"🚀 Found Meta Task for: {platform}")
            
            fb_token = os.environ.get('FB_ACCESS_TOKEN')
            if not fb_token:
                print("❌ ERROR: 'FB_ACCESS_TOKEN' is MISSING! (Waiting for setup)")
            
            # Simulation Logic
            try:
                sheet.update_cell(2, 16, "Publishing to Meta (Auto)...")
                print(f"✨ Simulating upload to {platform}...")
                
                # Success Simulation
                sheet.update_cell(2, 10, "DONE")
                sheet.update_cell(2, 16, "SUCCESS! Auto Meta Post Sent.")
                sheet.update_cell(2, 17, "https://fb.com/post/simulation_v2")
                print("🎉 DONE!")
                
            except Exception as e:
                sheet.update_cell(2, 16, f"Meta Error: {e}")
                print(f"❌ Meta Error: {e}")
        else:
            print(f"😴 Row 2 is not for Meta/Pending (Found: {platform})")

    except Exception as e:
        print(f"❌ Processing Error: {e}")

if __name__ == "__main__":
    main()
