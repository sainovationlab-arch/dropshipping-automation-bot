import os
import json
import gspread
from datetime import datetime, timedelta
import pytz
import time

# ================= CONFIG =================

IST = pytz.timezone("Asia/Kolkata")

SHEET_ID = os.environ.get("SHEET_CONTENT_URL")
GCP_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

DATE_COL = 0   # Column A
DAY_COL = 1    # Column B
TIME_COL = 2   # Column C
STATUS_COL = 9 # Column J
LOG_COL = 15   # Column P

TIME_BUFFER_MIN = 3  # +/- minutes window

# ================= AUTH =================

def connect_sheet():
    creds_dict = json.loads(GCP_JSON)
    gc = gspread.service_account_from_dict(creds_dict)
    return gc.open_by_key(SHEET_ID).sheet1

# ================= TIME HELPERS =================

def parse_sheet_time(time_str):
    try:
        return datetime.strptime(time_str.strip(), "%I:%M %p").time()
    except:
        return None

# ================= MAIN LOGIC =================

def main():
    print("🤖 BOT WOKE UP")

    now = datetime.now(IST)
    today_date = now.date()
    today_day = now.strftime("%A")
    now_time = now.time()

    print(f"🕒 Current IST Time: {now.strftime('%Y-%m-%d %I:%M %p')} ({today_day})")

    sheet = connect_sheet()
    rows = sheet.get_all_values()

    matched_row = None

    for i in range(1, len(rows)):
        row = rows[i]

        if len(row) <= STATUS_COL:
            continue

        status = row[STATUS_COL].strip().upper()
        if status != "PENDING":
            continue

        try:
            sheet_date = datetime.strptime(row[DATE_COL].strip(), "%m-%d-%Y").date()
        except:
            continue

        sheet_day = row[DAY_COL].strip()
        sheet_time = parse_sheet_time(row[TIME_COL])

        if not sheet_time:
            continue

        if sheet_date != today_date:
            continue

        if sheet_day.lower() != today_day.lower():
            continue

        sheet_dt = datetime.combine(today_date, sheet_time, tzinfo=IST)
        diff = abs((now - sheet_dt).total_seconds()) / 60

        if diff <= TIME_BUFFER_MIN:
            matched_row = i + 1
            break

    if not matched_row:
        print("⏸️ No matching task. Sleeping.")
        return

    print(f"🎯 MATCH FOUND AT ROW {matched_row}")

    # DRY RUN ACTION
    sheet.update_cell(matched_row, STATUS_COL + 1, "DONE")
    sheet.update_cell(matched_row, LOG_COL + 1, f"EXECUTED @ {now.strftime('%I:%M %p')}")

    print("✅ DRY RUN COMPLETE – STATUS UPDATED")

if __name__ == "__main__":
    main()
