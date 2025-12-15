import streamlit as st
import pandas as pd
import csv
import re
import traceback
from datetime import datetime
from io import StringIO

import gspread
from google.oauth2.service_account import Credentials

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(
    page_title="InstaMon BPS",
    layout="wide",
    page_icon="📊"
)

LOOKER_EMBED_URL = "https://lookerstudio.google.com/embed/reporting/f8d6fc1b-b5bd-43eb-881c-e74a9d86ff75/page/Z52hF"

if "data" not in st.session_state:
    st.session_state.data = []

if "last_processed" not in st.session_state:
    st.session_state.last_processed = []

# ----------------------------
# HELPER
# ----------------------------
def first_sentence(text):
    if not text:
        return ""
    m = re.search(r"(.+?[.!?])", text)
    return m.group(1) if m else text

def clean_caption(text):
    text = (text or "").replace("\n", " ").replace("\r", " ")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = first_sentence(text)
    text = re.sub(r"[^A-Za-z0-9 ,.!?]+", " ", text)
    return " ".join(text.split()).strip()

def parse_csv_content(csv_text):
    reader = csv.reader(StringIO(csv_text))
    hasil = []

    for row in reader:
        if len(row) < 3:
            continue

        link, caption, ts = row[0], row[1], row[2]

        ts = (ts or "").strip()
        if ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")

        tanggal = datetime.fromisoformat(ts).strftime("%m-%d-%Y")

        hasil.append({
            "Caption": clean_caption(caption),
            "Tanggal": tanggal,
            "Link": (link or "").strip()
        })

    return hasil

# ----------------------------
# GOOGLE SHEETS
# ----------------------------
def send_to_gsheet(rows):
    sa_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)

    spreadsheet_id = st.secrets["gsheet"]["spreadsheet_id"]
    sheet_name = st.secrets["gsheet"]["sheet_name"]

    ws = client.open_by_key(spreadsheet_id).worksheet(sheet_name)

    # Header
    if (ws.acell("B1").value or "").strip() == "":
        ws.update("B1", [["Caption"]])
    if (ws.acell("C1").value or "").strip() == "":
        ws.update("C1", [["Tanggal"]])
    if (ws.acell("E1").value or "").strip() == "":
        ws.update("E1", [["Link"]])

    last_row = len(ws.get_all_values())
    start_row = max(2, last_row + 1)
    end_row = start_row + len(rows) - 1

    values = []
    for r in rows:
        values.append([
            r.get("Caption", ""),
            r.get("Tanggal", ""),
            "",
            r.get("Link", "")
        ])

    ws.update(f"B{start_row}:E{end_row}", values, value_input_option="RAW")

# ----------------------------
# UI
# ----------------------------
tab1, tab2 = st.tabs(["🛠️ Input Data", "📊 Dashboard Monitoring"])

# ============================
# TAB 1
# ============================
with tab1:
    st.markdown("## 🛠️ Input & Proses Data Instagram")
    st.caption("Paste data CSV Instagram dengan format: **link, caption, timestamp**")

    with st.container(border=True):
        pasted_text = st.text_area(
            "📋 Paste Data CSV",
            height=220,
            placeholder="https://instagram.com/post1, Caption postingan, 2024-01-01T10:00:00Z"
        )

    with st.expander("🔐 Informasi Service Account Google Sheets"):
        try:
            st.markdown("Share Google Sheet ke email berikut sebagai **Editor**:")
            st.code(st.secrets["gcp_service_account"]["client_email"])
        except Exception:
            st.warning("Secrets belum dikonfigurasi di Streamlit Cloud.")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🚀 Proses Data", use_container_width=True):
            if not pasted_text.strip():
                st.warning("Silakan paste data CSV terlebih dahulu.")
            else:
                try:
                    data_baru = parse_csv_content(pasted_text)
                    st.session_state.data.extend(data_baru)
                    st.session_state.last_processed = data_baru
                    st.success(f"✅ {len(data_baru)} data berhasil diproses")
                except Exception as e:
                    st.error("Gagal memproses data")
                    st.exception(e)

    with col2:
        if st.button("🗑️ Reset Data", use_container_width=True):
            st.session_state.data = []
            st.session_state.last_processed = []
            st.success("Data berhasil direset")

    with col3:
        if st.button("📤 Kirim ke Google Sheets", use_container_width=True):
            try:
                rows = st.session_state.get("last_processed", [])
                if not rows:
                    st.warning("Belum ada data baru yang diproses.")
                else:
                    send_to_gsheet(rows)
                    st.success(f"✅ {len(rows)} baris terkirim ke Google Sheets")
            except Exception as e:
                st.error("Gagal mengirim ke Google Sheets")
                st.exception(e)
                st.code(traceback.format_exc())

    st.divider()

    if st.session_state.data:
        st.markdown("### 📋 Data Hasil Proses")
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True)

        st.download_button(
            "⬇️ Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            "hasil_monitoring_instagram.csv",
            "text/csv"
        )
    else:
        st.info("Belum ada data yang diproses.")

# ============================
# TAB 2
# ============================
with tab2:
    st.markdown("## 📊 Dashboard Monitoring Instagram")
    st.components.v1.iframe(
        src=LOOKER_EMBED_URL,
        width=1400,
        height=720,
        scrolling=True
    )
