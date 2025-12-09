import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 👇 શીટનું નામ (Content માટે)
SHEET_NAME = "Content_Sheet"

def main():
    print("💎 CONTENT PINTEREST BOT STARTED...")
    
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

    # 2. PROCESS ROWS
    try:
        rows = sheet.get_all_records()
        print(f"🔍 Checking {len(rows)} rows for PENDING tasks...")
        
        post_processed = False
        for i, row in enumerate(rows):
            row_num = i + 2
            
            platform = str(row.get('Platform', '')).strip().lower()
            status = str(row.get('Status', '')).strip().upper()
            
            # Pinterest Check
            if "pinterest" in platform and status == "PENDING":
                print(f"🚀 Found Content Pinterest Task at Row {row_num}")
                
                # DATA EXTRACTION
                video_url = row.get('Video URL', '')
                title = row.get('Caption', 'New Pin')
                link = row.get('Link', '') # Product/Redirect Link
                
                # Board & Account Name logic (Assuming columns exist or using defaults)
                board = str(row.get('Tags', 'My Board')).split('#')[0].strip() # Tags માંથી કામચલાઉ Board
                account = row.get('Account Name', 'Main Account')

                # Pinterest Token Check (Future Proofing)
                pin_token = os.environ.get('PINTEREST_ACCESS_TOKEN')
                if not pin_token:
                    print("❌ ERROR: 'PINTEREST_ACCESS_TOKEN' is MISSING! (Waiting for App Review)")
                    # We continue to simulate logic
                
                # UPLOAD LOGIC (Simulation)
                try:
                    sheet.update_cell(row_num, 9, "Pinning...") # Status Update
                    print(f"✨ Simulating Pin to Board: {board} on Account: {account}")
                    
                    # Success Simulation
                    sheet.update_cell(row_num, 9, "DONE")
                    sheet.update_cell(row_num, 10, "https://pinterest.com/pin/simulation")
                    print("🎉 DONE!")
                    post_processed = True
                    break
                
                except Exception as e:
                    sheet.update_cell(row_num, 9, "Pin Error")
                    print(f"❌ Pin Error: {e}")
                    break
        
        if not post_processed:
            print("😴 No PENDING Content Pinterest posts found.")

    except Exception as e:
        print(f"❌ Processing Error: {e}")

if __name__ == "__main__":
    main()
