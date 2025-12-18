import os
import time
import datetime
import traceback

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ==============================
# CONFIG
# ==============================

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = os.environ.get("SHEET_ID")
SERVICE_ACCOUNT_INFO = os.environ.get("GCP_CREDENTIALS_JSON")

CHECK_INTERVAL_SECONDS = 300  # 5 minutes

# ==============================
# AUTH
# ==============================

creds = Credentials.from_service_account_info(
    eval(SERVICE_ACCOUNT_INFO),
    scopes=SCOPES
)
sheets_service = build("sheets", "v4", credentials=creds)

# ==============================
# HELPERS
# ==============================

def now_india():
    return datetime.datetime.now()

def get_sheet_data():
    sheet = sheets_service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range="Pending_Uploads"
    ).execute()
    return result.get("values", [])

def update_cell(row, col, value):
    sheets_service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"Pending_Uploads!{col}{row}",
        valueInputOption="RAW",
        body={"values": [[value]]}
    ).execute()

# ==============================
# PLATFORM UPLOAD STUBS
# ==============================

def upload_video(platform, video_url, title, description, hashtags):
    """
    REAL upload logic already exists in your project.
    This wrapper only measures duration.
    """
    start = time.time()

    # ---- EXISTING UPLOAD LOGIC RUNS HERE ----
    time.sleep(2)  # simulate upload time
    live_url = f"https://{platform}.com/live_post_example"
    # ----------------------------------------

    duration = int(time.time() - start)
    return live_url, duration

# ==============================
# ANALYTICS FETCHERS
# ==============================

def fetch_views_likes(platform, live_url):
    # Stub – replace with your real API logic
    return {
        "views": 100,
        "likes": 12
    }

def fetch_pinterest_analytics(live_url):
    impressions = 500
    clicks = 45
    ctr = round((clicks / impressions) * 100, 2) if impressions else 0
    return impressions, clicks, ctr

# ==============================
# MAIN LOGIC
# ==============================

def main():
    rows = get_sheet_data()
    headers = rows[0]
    data_rows = rows[1:]

    now = now_india()

    for index, row in enumerate(data_rows, start=2):
        try:
            status = row[headers.index("Status")].strip()
            if status != "PENDING":
                continue

            sheet_date = datetime.datetime.strptime(
                row[headers.index("Schedule_Date")], "%m-%d-%Y"
            ).date()
            sheet_time = datetime.datetime.strptime(
                row[headers.index("Schedule_Time")], "%I:%M %p"
            ).time()

            if now.date() != sheet_date or now.time() < sheet_time:
                continue

            platform = row[headers.index("Platform")]
            video_url = row[headers.index("Video_Drive_Link")]
            title = row[headers.index("Title_Hook")]
            description = row[headers.index("Description")]
            hashtags = row[headers.index("Caption_Hashtag")]

            live_url, duration = upload_video(
                platform, video_url, title, description, hashtags
            )

            update_cell(index, "L", live_url)
            update_cell(index, "M", duration)
            update_cell(index, "K", "DONE")

            # ===== ANALYTICS =====
            if platform.lower() == "pinterest":
                imp, clicks, ctr = fetch_pinterest_analytics(live_url)
                update_cell(index, "P", imp)
                update_cell(index, "Q", clicks)
                update_cell(index, "R", ctr)
            else:
                analytics = fetch_views_likes(platform, live_url)
                update_cell(index, "N", analytics["views"])
                update_cell(index, "O", analytics["likes"])

        except Exception as e:
            update_cell(index, "K", "FAILED")
            print(traceback.format_exc())

# ==============================
# ENTRY
# ==============================

if __name__ == "__main__":
    main()
