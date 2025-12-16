import os
import json
import gspread
from datetime import datetime
import pytz

# ================= CONFIG =================

IST = pytz.timezone("Asia/Kolkata")

LIVE_MODE = True   # 🔥 EVERYTHING ON

SHEET_ID = os.environ.get("SHEET_CONTENT_URL")
GCP_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

# Column Index (0-based)
DATE_COL = 0    # A
DAY_COL = 1     # B
TIME_COL = 2    # C
STATUS_COL = 9  # J
LOG_COL = 15    # P

TIME_BUFFER_MIN = 3

# ================= GOOGLE SHEET AUTH =================

def connect_sheet():
    creds = json.loads(GCP_JSON)
    gc = gspread.service_account_from_dict(creds)
    return gc.open_by_key(SHEET_ID).sheet1

# ================= TIME PARSER =================

def parse_time(time_str):
    try:
        return datetime.strptime(time_str.strip(), "%I:%M %p").time()
    except:
        return None

# ================= POSTING ENGINE =================

def execute_posting(row_data):
    """
    All platform posting logic will stay here.
    Currently SAFE because STATUS != PENDING
    """
    print("🚀 EXECUTING REAL POSTING LOGIC")
    return "POST_SUCCESS"

# ================= MAIN BOT =================

def main():
    print("🤖 MASTER BOT WOKE UP")

    now = datetime.now(IST)
    today_date = now.date()
    today_day = now.strftime("%A")

    print(f"🕒 IST TIME: {now.strftime('%Y-%m-%d %I:%M %p')} ({today_day})")

    sheet = connect_sheet()
    rows = sheet.get_all_values()

    matched_row = None

    for i in range(1, len(rows)):
        row = rows[i]

        if len(row) <= STATUS_COL:
            continue

        status = row[STATUS_COL].strip().upper()

        # 🔒 MAIN SAFETY LOCK
        if status != "PENDING":
            continue

        try:
            row_date = datetime.strptime(row[DATE_COL], "%m-%d-%Y").date()
        except:
            continue

        if row_date != today_date:
            continue

        if row[DAY_COL].strip().lower() != today_day.lower():
            continue

        row_time = parse_time(row[TIME_COL])
        if not row_time:
            continue

        row_dt = datetime.combine(today_date, row_time, tzinfo=IST)
        diff = abs((now - row_dt).total_seconds()) / 60

        if diff <= TIME_BUFFER_MIN:
            matched_row = i + 1
            break

    if not matched_row:
        print("⏸️ No matching PENDING task found")
        return

    print(f"🎯 MATCH FOUND AT ROW {matched_row}")

    if LIVE_MODE:
        result = execute_posting(rows[matched_row - 1])
        sheet.update_cell(matched_row, STATUS_COL + 1, "DONE")
        sheet.update_cell(matched_row, LOG_COL + 1, result)
    else:
        sheet.update_cell(matched_row, STATUS_COL + 1, "DRY_RUN")
        sheet.update_cell(matched_row, LOG_COL + 1, "TEST_MODE")

    print("✅ MASTER BOT CYCLE COMPLETE")

# ================= ENTRY =================

if __name__ == "__main__":
    main()
