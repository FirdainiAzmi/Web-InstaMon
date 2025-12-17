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

LOOKER_EMBED_URL = "https://lookerstudio.google.com/embed/reporting/f8d6fc1b-b5bd-43eb-881c-e74a9d86ff75/page/Z52hF"
# # Custom CSS untuk tampilan Modern & Clean
st.markdown("""
    <style>
    /* Mengubah font dan background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Menghilangkan header asli Streamlit */
    header[data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
    }

    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* --- CUSTOM HEADER STYLE --- */
    .custom-header {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        margin-bottom: 2rem;
        display: flex;
        align-items: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
    }
    .header-text h1 {
        margin: 0;
        font-weight: 800;
        background: linear-gradient(45deg, #4F46E5, #7C3AED);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
    }
    .header-text p {
        margin: 0;
        color: #64748b;
        font-size: 1.1rem;
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
    try:
        sa_info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(sa_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        client = gspread.authorize(creds)
        ws = client.open_by_key(st.secrets["gsheet"]["spreadsheet_id"]).worksheet(st.secrets["gsheet"]["sheet_name"])
        
        # Data yang disusun: B=Caption, C=Tanggal, D="", E=Link, F=Penginput
        values = [[r["Caption"], r["Tanggal"], "", r["Link"], r["Penginput"]] for r in rows]
        
        last_row = len(ws.get_all_values())
        start_row = max(2, last_row + 1)
        
        # PERBAIKAN: Range harus sampai kolom F (Kolom ke-6)
        # B = Kolom 2, F = Kolom 6. 
        ws.update(f"B{start_row}:F{start_row + len(rows) - 1}", values, value_input_option="RAW")
        return True
    except Exception as e:
        st.error(f"Gagal mengirim ke GSheet: {e}") # Agar Anda tahu jika ada error teknis
        return False

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

# Tambahkan parameter nama_penginput
def parse_csv_content(csv_text, existing_links, nama_penginput): 
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
            "Link": link,
            "Penginput": nama_penginput # Masukkan variabel ke sini
        })

    return hasil, skipped

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
                else: st.error("Username/password salah")
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
    # --- TAMBAHAN: DEVELOPED BY ---
    st.write("---")
    st.markdown("""
        <div style="padding: 10px; border-radius: 10px; background-color: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.2);">
            <p style="margin:0; font-size:0.8rem; color:#475569;">Developed By:</p>
            <p style="margin:0; font-weight:bold; color:#4F46E5;">Firdaini Azmi & Muhammad Ariq Hibatullah</p>
        </div>
    """, unsafe_allow_html=True)

# =========================================================
# HEADER & METRICS
# =========================================================
st.title("🚀 InstaMon BPS")
st.markdown("Automasi rekap konten Instagram ke Google Sheets.")

st.write("---")

# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3 = st.tabs(["⚡ Input Data", "📊 Dashboard Looker", "📖 Panduan"])
with tab1:
    # --- BAGIAN ATAS: INPUT & AKSI ---
    col_in, col_opt = st.columns([2, 1])

    with col_in:
        st.markdown("#### 📥 Paste Data")
        with st.container(border=True):
            # Tambahkan input nama penginput di sini
            nama_penginput = st.text_input("👤 Nama Penginput:", placeholder="Masukkan nama Anda...")
            
            input_csv = st.text_area(
                "Masukkan kode dari bookmarklet:", 
                height=150, # Sedikit dikurangi tingginya agar muat dengan input nama
                placeholder="Link, Caption, Timestamp..."
            )
    
    with col_opt:
        st.markdown("#### ⚙️ Aksi Cepat")
        with st.container(border=True):
            # Penataan tombol dengan icon dan warna yang menarik
            btn_proses = st.button("⚡ Proses & Bersihkan", type="primary", use_container_width=True)
            st.write("") # Memberi sedikit jarak antar tombol
            btn_gsheet = st.button("📤 Push ke GSheet", use_container_width=True)
            st.write("")
            btn_clear = st.button("🗑️ Kosongkan Antrean", use_container_width=True)
            
            # Tambahan informasi kecil di bawah tombol agar tidak kosong
            st.divider()
            st.caption("ℹ️ Pastikan format CSV sesuai dengan output dari bookmarklet Instagram.")

    # --- LOGIKA PROSES (LOGIKA ASLI ANDA) ---
    if btn_proses:
       if input_csv.strip() and nama_penginput.strip():
            existing_links = {d["Link"] for d in st.session_state.data}
            # PERBAIKAN: Tambahkan nama_penginput sebagai argumen ketiga
            data_baru, skipped = parse_csv_content(input_csv, existing_links, nama_penginput)
            
            st.session_state.data.extend(data_baru)
            st.session_state.last_processed = data_baru
            
            st.toast("Data sedang diproses...", icon="⏳")
            st.success(f"✅ {len(data_baru)} data diproses!!")
            if skipped > 0:
                st.warning(f"⚠️ {skipped} data duplikat dilewati.")
    
    # --- LOGIKA GSHEET (LOGIKA ASLI ANDA) ---
    if btn_gsheet:
        if not st.session_state.last_processed:
            st.warning("Belum ada data baru untuk dikirim.")
        else:
            with st.spinner("Sedang mengirim ke Google Sheets..."):
                send_to_gsheet(st.session_state.last_processed)
                st.balloons() # Efek visual sukses
                st.success(f"✅ {len(st.session_state.last_processed)} baris berhasil dikirim!")
    
    # --- LOGIKA CLEAR (LOGIKA ASLI ANDA) ---
    if btn_clear:
        st.session_state.data = []
        st.session_state.last_processed = []
        st.success("Antrean berhasil dikosongkan.")
        st.rerun()

    # --- BAGIAN BAWAH: PREVIEW ---
    st.divider()
    st.markdown("#### 🔍 Preview Hasil")
    
    if st.session_state.data:
        # Menampilkan data dalam dataframe yang rapi
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(
            df, 
            use_container_width=True, 
            hide_index=True, # Menghilangkan kolom indeks agar lebih profesional
            column_config={
                "Link": st.column_config.LinkColumn("Link Postingan"),
                "Tanggal": st.column_config.TextColumn("Tanggal Post"),
                "Caption": st.column_config.TextColumn("Caption (Clean)")
            }
        )
        
        # Tombol download di bawah tabel
        st.download_button(
            label="⬇️ Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"rekap_ig_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    else:
        # Tampilan saat data kosong menggunakan st.info
        st.info("Belum ada data di antrean. Silahkan paste data di atas untuk memulai proses rekap.")
with tab2:
    st.markdown("## 📊 Dashboard Monitoring Instagram")
    st.components.v1.iframe(
        src=LOOKER_EMBED_URL,
        width=1400,
        height=480,
        scrolling=True
    )


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

























