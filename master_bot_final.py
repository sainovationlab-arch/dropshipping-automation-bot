import os
import json
import time
import requests
import tempfile
import re
import difflib
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials

# ------------- CONFIG -------------
IST = pytz.timezone("Asia/Kolkata")
TIME_BUFFER_MIN = 5  # minutes tolerance
GRAPH_URL = "https://graph.facebook.com/v19.0"

# Secrets / env
GCP_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
INSTAGRAM_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
RAW_IG_MAP = json.loads(os.environ.get("INSTAGRAM_USER_IDS", "{}"))
SHEET_ID = os.environ.get("SHEET_CONTENT_URL")  # spreadsheet id (or full url)

# transfer.sh fallback (no auth) — simple public temp hosting
TRANSFER_SH_BASE = "https://transfer.sh"

# Sheet columns (adjust indexes if your sheet differs)
DATE_COL = 0
DAY_COL = 1
TIME_COL = 2
BRAND_COL = 3
PLATFORM_COL = 4
VIDEO_NAME_COL = 5
VIDEO_URL_COL = 6
TITLE_COL = 7
HASHTAG_COL = 8
DESC_COL = 9
STATUS_COL = 10
LIVE_URL_COL = 11
LOG_COL = 15

# Behavior tuning
MAX_IG_PROCESS_WAIT_SEC = 180  # max time to wait for Instagram processing
IG_POLL_INTERVAL = 8  # seconds
HTTP_TIMEOUT = 30  # seconds for GET/HEAD


# ------------- Utils -------------
def normalize_text(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def fuzzy_find_ig(brand_name: str, threshold=0.35):
    target = normalize_text(brand_name)
    best = None
    best_score = 0.0
    for k, v in RAW_IG_MAP.items():
        score = difflib.SequenceMatcher(None, target, normalize_text(k)).ratio()
        if score > best_score:
            best_score = score
            best = v
    if best_score >= threshold:
        return best
    return None


def is_google_drive_link(url: str):
    return "drive.google.com" in url


def drive_direct_download(url: str):
    # convert possible google drive share link to direct download
    # https://drive.google.com/file/d/FILE_ID/view?usp=...
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if m:
        fid = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={fid}"
    # alternate sharing format ?id=...
    m2 = re.search(r"id=([a-zA-Z0-9_-]+)", url)
    if m2:
        return f"https://drive.google.com/uc?export=download&id={m2.group(1)}"
    return url


def head_ok(url: str):
    try:
        r = requests.head(url, allow_redirects=True, timeout=HTTP_TIMEOUT)
        if r.status_code == 200:
            ctype = r.headers.get("content-type", "")
            # accept video types
            if "video" in ctype or "application/octet-stream" in ctype:
                return True, r.headers
            # some hosts don't set content-type correctly but allow GET
            return True, r.headers
        return False, {"status_code": r.status_code, "headers": r.headers}
    except Exception as e:
        return False, {"error": str(e)}


def download_to_temp(url: str, max_mb=200):
    # download into a temp file and return path
    tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    total = 0
    with requests.get(url, stream=True, timeout=HTTP_TIMEOUT) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if not chunk:
                break
            tmpf.write(chunk)
            total += len(chunk)
            if total > max_mb * 1024 * 1024:
                tmpf.close()
                raise Exception("File too large")
    tmpf.close()
    return tmpf.name


def upload_transfer_sh(local_path):
    # simple fallback: transfer.sh (no auth, temporary)
    filename = os.path.basename(local_path)
    with open(local_path, "rb") as f:
        r = requests.put(f"{TRANSFER_SH_BASE}/{filename}", data=f, timeout=120)
        r.raise_for_status()
        return r.text.strip()  # transfer.sh returns URL in body


# ------------- Google Sheet connect -------------
def connect_sheet():
    creds = Credentials.from_service_account_info(json.loads(GCP_JSON),
                                                  scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)
    # if SHEET_ID is full url or id, open accordingly
    if SHEET_ID.startswith("http"):
        ss = gc.open_by_url(SHEET_ID)
    else:
        ss = gc.open_by_key(SHEET_ID)
    sheet = ss.get_worksheet(0)
    print("✅ Connected to sheet:", sheet.title)
    return sheet


# ------------- Instagram Helpers -------------
def ig_create_container(ig_user_id, video_url, caption):
    url = f"{GRAPH_URL}/{ig_user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": INSTAGRAM_TOKEN
    }
    r = requests.post(url, data=payload, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json().get("id")


def ig_check_status(container_id):
    url = f"{GRAPH_URL}/{container_id}"
    r = requests.get(url, params={"fields": "status_code", "access_token": INSTAGRAM_TOKEN}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json().get("status_code")


def ig_publish(ig_user_id, creation_id):
    url = f"{GRAPH_URL}/{ig_user_id}/media_publish"
    r = requests.post(url, data={"creation_id": creation_id, "access_token": INSTAGRAM_TOKEN}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json().get("id")


# ------------- Main posting flow -------------
def ensure_public_video(url):
    # returns a public-direct downloadable URL or raises
    # 1) if google drive, convert
    if is_google_drive_link(url):
        url = drive_direct_download(url)

    ok, info = head_ok(url)
    if ok:
        return url

    # try GET once to see error
    try:
        r = requests.get(url, stream=True, timeout=HTTP_TIMEOUT)
        if r.status_code == 200:
            # we have content but HEAD failed; we'll fallback to upload approach
            pass
        else:
            # try drive direct if possible
            if is_google_drive_link(url):
                url2 = drive_direct_download(url)
                ok2, _ = head_ok(url2)
                if ok2:
                    return url2
            raise Exception(f"Remote HEAD failed: {r.status_code}")
    except Exception as e:
        # fallback: download locally and upload to transfer.sh
        print("⚠ Fallback: will download & upload to transfer.sh because source not directly accessible:", e)

    # download local and upload to transfer.sh
    local = download_to_temp(url)
    try:
        public_url = upload_transfer_sh(local)
        print("⬆ uploaded to transfer.sh:", public_url)
        return public_url
    finally:
        try:
            os.remove(local)
        except:
            pass


def post_video_to_ig(brand_name, video_url, caption, sheet, row_index):
    # identify IG user id (smart fuzzy)
    ig_user_id = None
    # first try direct mapping by normalized brand keys
    ig_user_id = fuzzy_find_in_map(brand_name)
    if not ig_user_id:
        # fallback fuzzy with ratio
        ig_user_id = fuzzy_find_best(brand_name)
    if not ig_user_id:
        raise Exception("No IG mapping for brand: " + str(brand_name))

    # ensure public downloadable URL
    public_url = ensure_public_video(video_url)

    # create container
    creation_id = ig_create_container(ig_user_id, public_url, caption)
    print("📦 container id:", creation_id)

    # poll for status until FINISHED or timeout
    start = time.time()
    while time.time() - start < MAX_IG_PROCESS_WAIT_SEC:
        status = ig_check_status(creation_id)
        print("⏳ IG status:", status)
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise Exception("Instagram processing returned ERROR")
        time.sleep(IG_POLL_INTERVAL)

    else:
        raise Exception("Instagram processing timeout")

    # publish
    media_id = ig_publish(ig_user_id, creation_id)
    return f"https://www.instagram.com/reel/{media_id}/"


# Helper fuzzy functions (two-stage robust)
def fuzzy_find_in_map(brand_name):
    # exact normalized key match
    t = normalize_text(brand_name)
    for k, v in RAW_IG_MAP.items():
        if normalize_text(k) == t:
            return v
    return None


def fuzzy_find_best(brand_name):
    target = normalize_text(brand_name)
    best_score = 0
    best_id = None
    for k, v in RAW_IG_MAP.items():
        score = difflib.SequenceMatcher(None, target, normalize_text(k)).ratio()
        if score > best_score:
            best_score = score
            best_id = v
    if best_score >= 0.35:
        print("ℹ fuzzy matched", brand_name, "->", best_score)
        return best_id
    return None


def normalize_text(s):
    if not s:
        return ""
    return re.sub(r"[^a-z0-9]", "", s.lower())


# ------------- Runner -------------
def main():
    print("🤖 MASTER BOT FINAL RUN")
    sheet = connect_sheet()
    rows = sheet.get_all_values()
    now = datetime.now(IST)
    today = now.date()
    day_name = now.strftime("%A").lower()

    for i in range(1, len(rows)):
        row = rows[i]
        try:
            status = (row[STATUS_COL] or "").strip().upper()
            if status != "PENDING":
                continue

            # date/day/time checks (if present)
            try:
                row_date = datetime.strptime(row[DATE_COL], "%m-%d-%Y").date()
                if row_date != today:
                    continue
            except:
                pass

            try:
                if row[DAY_COL].strip().lower() != day_name:
                    continue
            except:
                pass

            # time tolerance
            try:
                t = datetime.strptime(row[TIME_COL].strip(), "%I:%M %p").time()
                scheduled_dt = IST.localize(datetime.combine(today, t))
                diff_min = abs((now - scheduled_dt).total_seconds()) / 60
                if diff_min > TIME_BUFFER_MIN:
                    continue
            except:
                pass

            platform = (row[PLATFORM_COL] or "").strip().lower()
            if "insta" not in platform:
                continue

            brand = row[BRAND_COL] or ""
            video_url = row[VIDEO_URL_COL] or ""
            title = row[TITLE_COL] or ""
            desc = row[DESC_COL] or ""
            tags = row[HASHTAG_COL] or ""
            caption = f"{title}\n\n{desc}\n\n{tags}"

            print(f"➡ Row {i+1} brand='{brand}' video='{video_url}'")

            public_live = post_video_to_ig(brand, video_url, caption, sheet, i+1)

            # update sheet
            sheet.update_cell(i+1, STATUS_COL+1, "DONE")
            sheet.update_cell(i+1, LIVE_URL_COL+1, public_live)
            sheet.update_cell(i+1, LOG_COL+1, "INSTAGRAM_POSTED")

            print("✅ Posted:", public_live)
            return

        except Exception as e:
            print("❌ ERROR row", i+1, str(e))
            try:
                sheet.update_cell(i+1, STATUS_COL+1, "FAILED")
                sheet.update_cell(i+1, LOG_COL+1, str(e))
            except Exception as _:
                pass
            return

    print("⏸ No matching task")


if __name__ == "__main__":
    main()
