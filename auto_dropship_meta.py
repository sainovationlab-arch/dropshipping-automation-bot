import os
import json
import gspread
from google.oauth2.service_account import Credentials # New Better Auth

# 👇 સાચું શીટનું નામ (આ ખાસ ચેક કરજો)
SHEET_NAME = "Dropshipping_Sheet"

def main():
    print("🛍️ AUTO DROPSHIPPING META BOT (V2) STARTED...")
    
    # 1. LOGIN (Google Sheet with Modern Auth)
    try:
        creds_json = os.environ.get('GCP_CREDENTIALS')
        if not creds_json: 
            print("❌ CRITICAL ERROR: 'GCP_CREDENTIALS' Secret is MISSING!")
            return
        
        # Define Scopes
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Load Credentials
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(creds)
        
        # Open Sheet
        sheet = gc.open(SHEET_NAME).get_worksheet(0)
        print(f"✅ Connected to {SHEET_NAME}")
        
    except Exception as e:
        print(f"❌ Connection Error (Check Sheet Name): {e}")
        return

    # 2. PROCESS ROW 2
    try:
        row_values = sheet.row_values(2)
        
        # ડેટા ઓછો હોય તો હેન્ડલ કરો
        if not row_values or len(row_values) < 10:
            print(f"❌ Row 2 data is empty or incomplete. Found: {row_values}")
            return

        # ડેટા ખેંચો
        platform = str(row_values[3]).strip().lower() # Column D (Index 3)
        status = str(row_values[8]).strip().upper()   # Column I (Index 8) - PENDING/DONE is usually Col I in your sheet?
        
        # આપણી શીટ મુજબ Status કોલમ 'I' (9th col -> Index 8) છે કે 'J' (10th col -> Index 9)?
        # Screenshot મુજબ: Status is Col I. So Index 8.
        
        print(f"🔍 Checking Row 2: Platform='{platform}', Status='{status}'")
        
        # Check for Facebook/Instagram
        if ("instagram" in platform or "facebook" in platform) and "PENDING" in status:
            print(f"🚀 Found Meta Task for: {platform}")
            
            fb_token = os.environ.get('FB_ACCESS_TOKEN')
            if not fb_token:
                print("❌ ERROR: 'FB_ACCESS_TOKEN' is MISSING!")
            else:
                print("✅ Meta Token Found.")
            
            # Simulation Logic
            try:
                # Update Logs (Column P? Let's assume Col L or just append)
                # Screenshot shows many columns. Let's just update Status for now.
                
                print(f"✨ Simulating upload to {platform}...")
                
                # Success - Update Status to DONE (Column I -> Cell 2,9)
                sheet.update_cell(2, 9, "DONE") 
                print("🎉 SUCCESS! Status updated to DONE in Google Sheet.")
                
            except Exception as e:
                print(f"❌ Meta Error: {e}")
        else:
            print(f"😴 Row 2 is not for Meta/Pending (Found: {platform}, {status})")

    except Exception as e:
        print(f"❌ Processing Error: {e}")

if __name__ == "__main__":
    main()
