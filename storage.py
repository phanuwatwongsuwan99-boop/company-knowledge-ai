"""Chat-log storage.

Uses Google Sheets when credentials are configured in st.secrets (free and
permanent). Falls back to a local CSV file, which Streamlit Community Cloud
wipes whenever the app restarts or goes to sleep.
"""
import csv
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

TZ_TH = timezone(timedelta(hours=7))
CSV_PATH = "chat_logs.csv"
COLUMNS = [
    "Chat ID",
    "วัน-เวลา",
    "ชื่อพนักงาน",
    "คำถาม",
    "คำตอบจาก AI",
    "สถานะการตอบ",
    "แหล่งข้อมูล",
]


def now_th() -> str:
    return datetime.now(TZ_TH).strftime("%Y-%m-%d %H:%M:%S")


def _secret(key, default=None):
    try:
        return st.secrets.get(key, default)
    except Exception:  # no secrets file at all
        return default


def using_sheets() -> bool:
    return bool(_secret("gcp_service_account")) and bool(_secret("GSHEET_URL"))


def backend_name() -> str:
    return "Google Sheets" if using_sheets() else "ไฟล์ CSV ชั่วคราว"


@st.cache_resource(show_spinner=False)
def _worksheet():
    import gspread

    gc = gspread.service_account_from_dict(dict(_secret("gcp_service_account")))
    ws = gc.open_by_url(_secret("GSHEET_URL")).sheet1
    if not ws.row_values(1):
        ws.append_row(COLUMNS, value_input_option="RAW")
    return ws


def _rows_to_df(rows):
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    body = rows[1:] if rows[0] and rows[0][0] == COLUMNS[0] else rows
    # Pad / trim every row so old 6-column logs still load.
    fixed = [(list(r) + [""] * len(COLUMNS))[: len(COLUMNS)] for r in body if any(r)]
    return pd.DataFrame(fixed, columns=COLUMNS)


def append_log(chat_id, username, question, answer, status, sources=""):
    row = [chat_id, now_th(), username, question, answer, status, sources]
    if using_sheets():
        _worksheet().append_row(row, value_input_option="RAW")
    else:
        new_file = not os.path.isfile(CSV_PATH)
        with open(CSV_PATH, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(COLUMNS)
            writer.writerow(row)
    load_logs.clear()


@st.cache_data(ttl=60, show_spinner=False)
def load_logs() -> pd.DataFrame:
    try:
        if using_sheets():
            return _rows_to_df(_worksheet().get_all_values())
        if os.path.isfile(CSV_PATH):
            with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
                return _rows_to_df(list(csv.reader(f)))
    except Exception as e:
        st.warning(f"โหลดประวัติการแชทไม่สำเร็จ: {e}")
    return pd.DataFrame(columns=COLUMNS)


def logs_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")
