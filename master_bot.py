import os
import json
import gspread
from google.oauth2.service_account import Credentials

# =======================================================
# 🕵️ SHEET FINDER TOOL (DIAGNOSTIC)
# =======================================================

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def find_my_sheets():
    print("\n" + "="*60)
    print("🕵️ SEARCHING FOR SHEETS...")
    
    # 1. Credentials Check
    creds_json = os.environ.get("GCP_CREDENTIALS")
    if not creds_json:
        print("❌ ERROR: Credentials missing.")
        return

    try:
        creds_dict = json.loads(creds_json)
        bot_email = creds_dict.get("client_email", "Unknown")
        print(f"🔑 BOT EMAIL:  {bot_email}")
        print("(Make sure THIS email is added to your Sheet as Editor)")
        print("-" * 60)

        # 2. Connect
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        
        # 3. List All Sheets
        # Aa function bot ne je sheet dekhay te badhu list lavse
        sheets = client.list_spreadsheet_files()
        
        if not sheets:
            print("❌ RESULT: ZERO SHEETS FOUND!")
            print("👉 Aa Bot ne koi pan sheet dekhati nathi.")
            print(f"👉 Solution: '{bot_email}' ne copy karo ane sheet ma Share karo.")
        else:
            print(f"✅ RESULT: FOUND {len(sheets)} SHEETS!")
            print("👇 Tamaru Sheet ID ahiya niche che (Match karo):")
            print("-" * 60)
            found_dropshipping = False
            for sheet in sheets:
                print(f"📄 Name: {sheet['name']}")
                print(f"🔗 ID:   {sheet['id']}")
                print("-" * 60)
                if "Dropshiping" in sheet['name']:
                    found_dropshipping = True
                    print("🚀 ^^^ AAHIYA CHE TAMARI SHEET ID! AA COPY KARO! ^^^")
            
            if not found_dropshipping:
                print("⚠️ Mane Sheets mali pan 'Dropshiping' naam ni sheet nathi mali.")

    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    find_my_sheets()
