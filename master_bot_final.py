import os
import json
import gspread
from datetime import datetime, timedelta
import pytz

# ================= CONFIG =================

IST = pytz.timezone("Asia/Kolkata")

LIVE_MODE = False   # 🔴 Sheet ready થાય ત્યારે TRUE કરશું

SHEET_ID = os.environ.get("SHEET_CONTENT_URL")
GCP_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

DATE_COL = 0
DAY_COL = 1
TIME_COL = 2
STATUS_COL = 9
LOG_COL = 15

TIME_BUFFER_MIN = 3

# ================= AUTH =================

def connect_sheet():
    creds = json.loads(GCP_JSON)
    gc = gspread.service_account_from_dict(creds)
    return gc.open_by_key(SHEET_ID).sheet1

# ================= TIME =================

def parse_time(t):
    try:
        return datetime.strptime(t.strip(), "%I:%M %p").time()
    except:
        return None

# ================= POSTING PLACEHOLDER =================

def execute_posting(row_data):
    """
    Future:
    - YouTube
    - Instagram
    - Pinterest
    """
    print("🚀 LIVE MODE POSTING EXECUTED")
    return "POSTED_SUCCESSFULLY"

# ================= MAIN =================

def main():
    print("🤖 BOT STARTED")

    now = datetime.now(IST)
    today_date = now.date()
    today_day = now.strftime("%A")

    sheet = connect_sheet()
    rows = sheet.get_all_values()

    target_row = None

    for i in range(1, len(rows)):
        row = rows[i]

        if len(row) <= STATUS_COL:
            continue

        if row[STATUS_COL].strip().upper() != "PENDING":
            continue

        try:
            row_date = datetime.strptime(row[DATE_COL], "%m-%d-%Y").date()
        except:
            continue

        if row_date != today_date:
            continue

        if row[DAY_COL].lower() != today_day.lower():
            continue

        row_time = parse_time(row[TIME_COL])
        if not row_time:
            continue

        row_dt = datetime.combine(today_date, row_time, tzinfo=IST)
        diff = abs((now - row_dt).total_seconds()) / 60

        if diff <= TIME_BUFFER_MIN:
            target_row = i + 1
            break

    if not target_row:
        print("⏸️ No task matched")
        return

    print(f"🎯 TASK FOUND AT ROW {target_row}")

    if LIVE_MODE:
        result = execute_posting(rows[target_row - 1])
        sheet.update_cell(target_row, STATUS_COL + 1, "DONE")
        sheet.update_cell(target_row, LOG_COL + 1, result)
    else:
        sheet.update_cell(target_row, STATUS_COL + 1, "DRY_RUN_DONE")
        sheet.update_cell(target_row, LOG_COL + 1, "READY_FOR_LIVE")

    print("✅ BOT CYCLE COMPLETE")

if __name__ == "__main__":
    main()
