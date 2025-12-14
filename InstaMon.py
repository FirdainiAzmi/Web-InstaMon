import streamlit as st
import pandas as pd
import csv
import re
from datetime import datetime
from io import StringIO

import gspread
from google.oauth2.service_account import Credentials

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="InstaMon BPS", layout="wide")

LOOKER_EMBED_URL = "https://lookerstudio.google.com/embed/reporting/f8d6fc1b-b5bd-43eb-881c-e74a9d86ff75/page/Z52hF"

if "data" not in st.session_state:
    st.session_state.data = []

if "last_processed" not in st.session_state:
    st.session_state.last_processed = []

# ----------------------------
# HELPERS (CAPTION & CSV PARSER)
# ----------------------------
def first_sentence(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"(.+?[.!?])", text)
    return m.group(1) if m else text

def clean_caption(text: str) -> str:
    text = (text or "").replace("\n", " ").replace("\r", " ")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = first_sentence(text)
    text = re.sub(r"[^A-Za-z0-9 ,.!?]+", " ", text)
    return " ".join(text.split()).strip()

def parse_csv_content(csv_text: str):
    reader = csv.reader(StringIO(csv_text))
    hasil = []

    for row in reader:
        if len(row) < 3:
            continue

        link, caption, ts = row[0].strip(), row[1], row[2].strip()

        # format tanggal (ISO string)
        if ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")

        tanggal = datetime.fromisoformat(ts).strftime("%m-%d-%Y")

        hasil.append({
            "Caption": clean_caption(caption),
            "Tanggal": tanggal,
            "Link": link
        })

    return hasil

# ----------------------------
# GOOGLE SHEETS SENDER (STREAMLIT CLOUD)
# ----------------------------
def send_to_gsheet(rows):
    """
    rows: list of dicts with keys: Caption, Tanggal, Link
    Secrets needed:
      st.secrets["gcp_service_account"] : dict from service account JSON
      st.secrets["gsheet"]["spreadsheet_id"]
      st.secrets["gsheet"]["sheet_name"]
    """
    sa_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)

    spreadsheet_id = st.secrets["gsheet"]["spreadsheet_id"]
    sheet_name = st.secrets["gsheet"]["sheet_name"]

    ws = client.open_by_key(spreadsheet_id).worksheet(sheet_name)

    # header kalau sheet masih kosong
    if not ws.get_all_values():
        ws.append_row(["Caption", "Tanggal", "Link"])

    values = [[r["Caption"], r["Tanggal"], r["Link"]] for r in rows]
    ws.append_rows(values, value_input_option="RAW")

# ----------------------------
# UI
# ----------------------------
tab1, tab2 = st.tabs(["🛠️ Input Data", "📊 Dashboard Monitoring"])

# ============================
# TAB 1
# ============================
with tab1:
    st.title("🛠️ Input & Proses Data Instagram")

    st.subheader("📂 Upload File CSV")
    uploaded = st.file_uploader("Upload CSV (link, caption, timestamp)", type=["csv"])

    st.subheader("✍️ Atau Paste Data CSV")
    pasted_text = st.text_area("Paste di sini (1 baris = 1 postingan)", height=150)

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("🚀 PROSES DATA"):
            if uploaded:
                csv_text = uploaded.getvalue().decode("utf-8")
            elif pasted_text.strip():
                csv_text = pasted_text
            else:
                st.warning("Upload file atau paste data terlebih dahulu.")
                csv_text = None

            if csv_text:
                try:
                    data_baru = parse_csv_content(csv_text)
                    st.session_state.data.extend(data_baru)
                    st.session_state.last_processed = data_baru  # biar tombol kirim ga dobel
                    st.success(f"✅ {len(data_baru)} data berhasil diproses")
                except Exception as e:
                    st.error(f"Gagal memproses data: {e}")

    with col2:
        if st.button("🗑️ RESET DATA"):
            st.session_state.data = []
            st.session_state.last_processed = []
            st.success("Data berhasil direset")

    with col3:
        if st.button("📤 KIRIM DATA TERAKHIR KE GOOGLE SHEETS"):
            try:
                rows = st.session_state.get("last_processed", [])
                if not rows:
                    st.warning("Belum ada data baru yang diproses. Klik PROSES DATA dulu.")
                else:
                    send_to_gsheet(rows)
                    st.success(f"✅ {len(rows)} baris terkirim ke Google Sheets")
            except Exception as e:
                st.error(f"❌ Gagal kirim ke Sheets: {e}")

    st.divider()

    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)

        st.subheader("📋 Tabel Data")
        st.dataframe(df, use_container_width=True)

        csv_out = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            csv_out,
            "hasil_monitoring_instagram.csv",
            "text/csv"
        )
    else:
        st.info("Belum ada data.")

# ============================
# TAB 2
# ============================
with tab2:
    st.title("📊 Dashboard Monitoring")
    st.components.v1.iframe(
        src=LOOKER_EMBED_URL,
        width=1400,
        height=700,
        scrolling=True
    )
