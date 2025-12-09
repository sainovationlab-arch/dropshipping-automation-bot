import os
import json
import gspread
from google.oauth2.service_account import Credentials

# 👇 શીટનું નામ
SHEET_NAME = "Dropshipping_Sheet"

def main():
    print("🛍️ AUTO DROPSHIPPING META BOT (V2) STARTED...")
    
    # 1. LOGIN
    try:
        creds_json = os.environ.get('GCP_CREDENTIALS')
        if not creds_json: 
            print("❌ CRITICAL ERROR: 'GCP_CREDENTIALS' Secret is MISSING!")
            return
        
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open(SHEET_NAME).get_worksheet(0)
        print(f"✅ Connected to {SHEET_NAME}")
        
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    # 2. PROCESS ROW 2
    try:
        row_values = sheet.row_values(2)
        
        # 👇 સુધારો: અહીં મેં 10 ની જગ્યાએ 9 કરી દીધું છે
        if not row_values or len(row_values) < 9:
            print(f"❌ Row 2 data is empty or incomplete. Found: {row_values}")
            return

        # ડેટા ખેંચો
        platform = str(row_values[3]).strip().lower() # Col D
        # જો Col I (Index 8) માં Status હોય
        if len(row_values) > 8:
            status = str(row_values[8]).strip().upper()
        else:
            status = "UNKNOWN"
            
        print(f"🔍 Checking Row 2: Platform='{platform}', Status='{status}'")
        
        # Check for Facebook/Instagram
        if ("instagram" in platform or "facebook" in platform) and "PENDING" in status:
            print(f"🚀 Found Meta Task for: {platform}")
            
            fb_token = os.environ.get('FB_ACCESS_TOKEN')
            if not fb_token:
                print("❌ ERROR: 'FB_ACCESS_TOKEN' is MISSING!")
            else:
                print("✅ Meta Token Found.")
            
            # Update Sheet
            try:
                print(f"✨ Simulating upload to {platform}...")
                
                # Update Status to DONE (Row 2, Column 9 -> Cell I2)
                sheet.update_cell(2, 9, "DONE") 
                print("🎉 SUCCESS! Status updated to DONE in Google Sheet.")
                
            except Exception as e:
                print(f"❌ Sheet Update Error: {e}")
        else:
            print(f"😴 Row 2 is not for Meta/Pending (Found: {platform}, {status})")

    except Exception as e:
        print(f"❌ Processing Error: {e}")

if __name__ == "__main__":
    main()
