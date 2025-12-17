import streamlit as st
import pandas as pd
import csv
import re
from datetime import datetime
from io import StringIO
import gspread
from google.oauth2.service_account import Credentials

# =========================================================
# CONFIG & PREMIUM STYLING
# =========================================================
st.set_page_config(
    page_title="InstaMon BPS - Premium Dashboard",
    layout="wide",
    page_icon="✨"
)

# Custom CSS untuk tampilan Modern & Clean
st.markdown("""
    <style>
    /* Mengubah font dan background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Container Styling */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* Card Styling */
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.8);
        padding: 15px 20px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid rgba(255,255,255,0.3);
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: white;
        border-radius: 10px 10px 0px 0px;
        padding: 0px 30px;
        border: none;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }

    .stTabs [aria-selected="true"] {
        background-color: #4F46E5 !important;
        color: white !important;
    }

    /* Main Action Button */
    .stButton>button[kind="primary"] {
        background: linear-gradient(45deg, #4F46E5, #7C3AED);
        border: none;
        color: white;
        padding: 12px 24px;
        font-weight: 700;
        border-radius: 12px;
        width: 100%;
    }

    /* Dataframe Styling */
    .stDataFrame {
        border-radius: 15px;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# HELPER FUNCTIONS
# =========================================================
def send_to_gsheet(rows):
    # (Logika tetap sama dengan kode Anda sebelumnya)
    try:
        sa_info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(sa_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        client = gspread.authorize(creds)
        ws = client.open_by_key(st.secrets["gsheet"]["spreadsheet_id"]).worksheet(st.secrets["gsheet"]["sheet_name"])
        values = [[r["Caption"], r["Tanggal"], "", r["Link"]] for r in rows]
        last_row = len(ws.get_all_values())
        start_row = max(2, last_row + 1)
        ws.update(f"B{start_row}:E{start_row + len(rows) - 1}", values, value_input_option="RAW")
        return True
    except:
        return False

# =========================================================
# LOGIN LOGIC
# =========================================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "data" not in st.session_state: st.session_state.data = []

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("#")
        with st.container(border=True):
            st.image("https://img.icons8.com/fluency/96/instagram-new.png", width=60)
            st.title("InstaMon")
            st.caption("Monitoring Content BPS Made Easy")
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            if st.button("Login Sekarang", type="primary", use_container_width=True):
                if user == st.secrets["auth"]["username"] and pw == st.secrets["auth"]["password"]:
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("Kredensial salah")
    st.stop()

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/data-configuration.png", width=50)
    st.title("Settings")
    st.info(f"Connected to GSheet: \n`{st.secrets['gsheet']['sheet_name']}`")
    if st.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()

# =========================================================
# HEADER & METRICS
# =========================================================
st.title("🚀 InstaMon BPS")
st.markdown("Automasi rekap konten Instagram ke Google Sheets.")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Status", "Operational 🟢")
m2.metric("Data Tersimpan", len(st.session_state.data))
m3.metric("Uploader", st.secrets["auth"]["username"])
m4.metric("Version", "2.0.1")

st.write("---")

# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3 = st.tabs(["⚡ Input Data", "📊 Dashboard Looker", "📖 Panduan"])
with tab1:
    st.markdown("## 🛠️ Input & Proses Data Instagram")
    st.caption("Format hasil bookmark: **link, caption, timestamp**")

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
with tab2:
    st.markdown("""
        <div style="background-color: white; padding: 10px; border-radius: 15px;">
            <iframe src="https://lookerstudio.google.com/embed/reporting/f8d6fc1b-b5bd-43eb-881c-e74a9d86ff75/page/Z52hF" 
            width="100%" height="800" frameborder="0" style="border:0" allowfullscreen></iframe>
        </div>
    """, unsafe_allow_html=True)

with tab3:
    st.markdown("# 📘 Informasi Penggunaan InstaMon")
    st.caption("Panduan penggunaan web monitoring Instagram")

    st.divider()

    # ======================
    # SECTION: APA ITU INSTAMON
    # ======================
    st.markdown("""
    ### 🧠 Apa itu InstaMon?
    
    **InstaMon** adalah web internal untuk **merekap konten Instagram**
    dan **memonitoring konten kegiatan**.
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
    with c3:
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
    3. Klik bookmark **IG to CSV** yang sudah dibuat (lihat halaman bawah untuk cara pembuatan bookmarklet)
    4. Data otomatis tersalin
    5. Paste ke kolom CSV di InstaMon
    6. Klik **Proses Data**
    """)

    st.divider()
    # ======================
    # SECTION: BOOKMARKLET
    # ======================
    st.markdown("## 🔖 Cara Membuat Bookmarklet")

    left, right = st.columns([1, 2])

    with left:
        st.markdown("""
        1. Tampilkan **Bookmark Bar** dengan Ctrl+Shift+B
        2. Klik kanan pada **Bookmark Bar** dan klik **Bookmark Manager**
        3. KLik **Add New Bookmark**  
        4. Nama: `IG to CSV`
        4. URL: paste kode JS di samping
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



