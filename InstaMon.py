import streamlit as st
import pandas as pd
import csv
import re
import traceback
from datetime import datetime
from io import StringIO

import gspread
from google.oauth2.service_account import Credentials

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="InstaMon BPS",
    layout="wide",
    page_icon="📊"
)

LOOKER_EMBED_URL = "https://lookerstudio.google.com/embed/reporting/f8d6fc1b-b5bd-43eb-881c-e74a9d86ff75/page/Z52hF"

# =========================================================
# SESSION STATE
# =========================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "data" not in st.session_state:
    st.session_state.data = []

if "last_processed" not in st.session_state:
    st.session_state.last_processed = []

# =========================================================
# LOGIN PAGE
# =========================================================
def login_page():
    st.markdown("## 🔐 Login InstaMon BPS")

    with st.container(border=True):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", use_container_width=True):
            if (
                username == st.secrets["auth"]["username"]
                and password == st.secrets["auth"]["password"]
            ):
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("❌ Username atau password salah")

if not st.session_state.logged_in:
    login_page()
    st.stop()

# =========================================================
# HELPER FUNCTIONS
# =========================================================
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

def parse_csv_content(csv_text, existing_links):
    reader = csv.reader(StringIO(csv_text))
    hasil = []
    skipped = 0

    for row in reader:
        if len(row) < 3:
            continue

        link, caption, ts = row[0].strip(), row[1], row[2]

        if not link or link in existing_links:
            skipped += 1
            continue

        existing_links.add(link)

        ts = ts.strip()
        if ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")

        tanggal = datetime.fromisoformat(ts).strftime("%m-%d-%Y")

        hasil.append({
            "Caption": clean_caption(caption),
            "Tanggal": tanggal,
            "Link": link
        })

    return hasil, skipped

# =========================================================
# GOOGLE SHEETS
# =========================================================
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

    if (ws.acell("B1").value or "") == "":
        ws.update("B1", [["Caption"]])
    if (ws.acell("C1").value or "") == "":
        ws.update("C1", [["Tanggal"]])
    if (ws.acell("E1").value or "") == "":
        ws.update("E1", [["Link"]])

    last_row = len(ws.get_all_values())
    start_row = max(2, last_row + 1)
    end_row = start_row + len(rows) - 1

    values = []
    for r in rows:
        values.append([
            r["Caption"],   # B
            r["Tanggal"],   # C
            "",             # D
            r["Link"]       # E
        ])

    ws.update(f"B{start_row}:E{end_row}", values, value_input_option="RAW")

# =========================================================
# UI TABS
# =========================================================
tab1, tab2, tab3 = st.tabs([
    "🛠️ Input Data",
    "📊 Dashboard Monitoring",
    "📘 Informasi Penggunaan"
])

# =======================
# TAB 1 - INPUT DATA
# =======================
with tab1:
    st.markdown("## 🛠️ Input & Proses Data Instagram")
    st.caption("Format CSV: **link, caption, timestamp**")

    with st.container(border=True):
        pasted_text = st.text_area(
            "📋 Paste Data CSV",
            height=220
        )

    with st.expander("🔐 Informasi Service Account"):
        st.markdown("Share Google Sheet ke email ini sebagai **Editor**:")
        st.code(st.secrets["gcp_service_account"]["client_email"])

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🚀 Proses Data", use_container_width=True):
            if not pasted_text.strip():
                st.warning("Paste data terlebih dahulu.")
            else:
                existing_links = {d["Link"] for d in st.session_state.data}
                data_baru, skipped = parse_csv_content(
                    pasted_text,
                    existing_links
                )

                st.session_state.data.extend(data_baru)
                st.session_state.last_processed = data_baru

                st.success(f"✅ {len(data_baru)} data diproses")
                if skipped > 0:
                    st.warning(f"⚠️ {skipped} data dilewati (duplikat link)")

    with col2:
        if st.button("🗑️ Reset Data", use_container_width=True):
            st.session_state.data = []
            st.session_state.last_processed = []
            st.success("Data berhasil direset")

    with col3:
        if st.button("📤 Kirim ke Google Sheets", use_container_width=True):
            rows = st.session_state.last_processed
            if not rows:
                st.warning("Belum ada data baru.")
            else:
                send_to_gsheet(rows)
                st.success(f"✅ {len(rows)} baris terkirim ke Google Sheets")

    st.divider()

    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True)

        st.download_button(
            "⬇️ Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            "hasil_monitoring_instagram.csv",
            "text/csv"
        )
    else:
        st.info("Belum ada data.")

# =======================
# TAB 2 - DASHBOARD
# =======================
with tab2:
    st.markdown("## 📊 Dashboard Monitoring Instagram")
    st.components.v1.iframe(
        src=LOOKER_EMBED_URL,
        width=1400,
        height=720,
        scrolling=True
    )

# =======================
# TAB 3 - INFORMASI PENGGUNAAN
# =======================
with tab3:
    st.markdown("# 📘 Informasi Penggunaan InstaMon")
    st.caption("Panduan resmi penggunaan aplikasi monitoring Instagram")

    st.divider()

    # ======================
    # SECTION: APA ITU INSTAMON
    # ======================
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        ### 🧠 Apa itu InstaMon?

        **InstaMon** adalah aplikasi internal untuk **monitoring konten Instagram**
        yang digunakan secara **manual, aman, dan non-otomatis**.

        Aplikasi ini **TIDAK melakukan scraping otomatis**
        dan **TIDAK mengambil data langsung dari Instagram**.
        """)

    with col2:
        st.success("""
        ✅ Manual  
        ✅ Aman  
        ✅ Audit-friendly  
        """)

    st.divider()

    # ======================
    # SECTION: ALUR KERJA
    # ======================
    st.markdown("## 🔄 Alur Kerja InstaMon")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.info("""
        **1️⃣Bookmarklet**
        - Klik IG to CSV
        - Data disalin
        """)
    with c2:
        st.info("""
        **2️⃣ Rekap Data**
        - Paste hasil bookmarklet
        - Proses data
        - Kirim data ke Google Sheets
        """)
    with c:
        st.info("""
        **3️⃣ Dashboard Monitoring**
        - Hasil rekap data yang dilakukan akan ditampilkan pada dashbaord tersebut
        """)
    st.divider()
    # ======================
    # SECTION: CARA PAKAI
    # ======================
    st.markdown("## ▶️ Cara Penggunaan InstaMon")

    st.markdown("""
    1. Login Instagram melalui browser  
    2. Buka **1 postingan Instagram**
    3. Klik bookmark **IG to CSV**
    4. Data otomatis tersalin
    5. Paste ke kolom CSV di InstaMon
    6. Klik **Proses Data**
    """)

    st.divider()
    # ======================
    # SECTION: BOOKMARKLET
    # ======================
    st.markdown("## 🔖 Bookmarklet IG to CSV")

    left, right = st.columns([1, 2])

    with left:
        st.markdown("""
        ### 🔧 Cara Membuat Bookmarklet
        1. Tampilkan **Bookmark Bar** dengan Ctrl+Shift+B
        2. Klik kanan pada **Bookmark Bar** dan klik **Bookmark Manager**
        3. KLik **Add New Bookmark**  
        4. Nama: `IG to CSV`
        4. URL: paste kode JS
        5. Simpan
        """)

    with right:
        st.code("""
javascript:(()=>{const permalink=location.href.split("?")[0];
let captionFull=document.querySelector("h1")?.innerText?.trim()||"";
if(!captionFull){
 const og=document.querySelector('meta[property="og:description"]')?.content||"";
 captionFull=og.includes(":")?og.split(":").slice(1).join(":").trim():og.trim()
}
const timeEl=document.querySelector("article time[datetime]")||document.querySelector("time[datetime]");
const timestamp=timeEl?timeEl.getAttribute("datetime"):"";

const firstSentence=(t)=>{const m=(t||"").match(/^(.+?[.!?])(\s|$)/s);
return m?m[1].trim():(t||"").split("\\n")[0].trim()};

const clean=(t)=>firstSentence(t)
.replace(/\\s+/g," ")
.replace(/[^\x00-\x7F]/g,"")
.replace(/[^A-Za-z0-9 ,\\.?!]+/g," ")
.trim();

const cap=clean(captionFull).replaceAll('"','""');
const line=`"${permalink}","${cap}","${timestamp}"`;

navigator.clipboard.writeText(line)
.then(()=>alert("CSV disalin:\\n"+line))
.catch(()=>prompt("Copy CSV:",line));
})();
        """, language="javascript")

    st.divider()






