import streamlit as st
import instaloader
import pandas as pd
import re
from datetime import datetime

st.set_page_config(page_title="InstaMon BPS", layout="wide")

LOOKER_EMBED_URL = "https://lookerstudio.google.com/embed/reporting/f8d6fc1b-b5bd-43eb-881c-e74a9d86ff75/page/Z52hF"

if "data" not in st.session_state:
    st.session_state.data = []

# =======================
#  CLEANING FUNCTIONS
# =======================

def first_sentence(text):
    text = text.strip()
    match = re.search(r"(.+?[.!?])", text)
    return match.group(1) if match else text

def clean_caption(text):
    text = (text or "").replace("\n", " ").replace("\r", " ")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = first_sentence(text)
    text = re.sub(r"[^A-Za-z0-9 ,.!?]+", " ", text)
    text = " ".join(text.split()).strip()
    return text

# =======================
#  SCRAPING BY USERNAME
# =======================

def scrape_by_username(username, start_date, end_date):
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        save_metadata=False,
        compress_json=False
    )

    profile = instaloader.Profile.from_username(loader.context, username)
    hasil = []

    for post in profile.get_posts():
        post_date = post.date

        # FILTER BERDASARKAN RENTANG TANGGAL
        if start_date <= post_date <= end_date:
            hasil.append({
                "Caption": clean_caption(post.caption or ""),
                "Tanggal": post_date.strftime("%m/%d/%Y"),
                "Link": f"https://www.instagram.com/p/{post.shortcode}/"
            })

    return hasil

# =======================
#  UI STREAMLIT
# =======================

tab1, tab2 = st.tabs(["🛠️ Tools Input Data", "📊 Dashboard Monitoring"])

with tab1:
    st.title("🛠️ Scraping Instagram Berdasarkan Username & Rentang Tanggal")

    username = st.text_input("Masukkan Username Instagram (tanpa @):", placeholder="bps_statistics")

    date_range = st.date_input(
        "Pilih rentang tanggal:",
        value=(datetime(2024, 1, 1), datetime.now()),
        help="Sistem hanya mengambil postingan dalam rentang tanggal ini."
    )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date = datetime.combine(date_range[0], datetime.min.time())
        end_date = datetime.combine(date_range[1], datetime.max.time())
    else:
        start_date = end_date = None

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 PROSES SCRAPING"):
            if not username.strip():
                st.warning("Username tidak boleh kosong!")
            else:
                with st.spinner("Sedang mengambil data..."):
                    try:
                        hasil = scrape_by_username(username, start_date, end_date)
                        st.session_state.data = hasil
                        st.success(f"✅ {len(hasil)} postingan berhasil ditemukan!")
                    except Exception as e:
                        st.error(f"Terjadi kesalahan: {e}")

    with col2:
        if st.button("🗑️ RESET DATA"):
            st.session_state.data = []
            st.success("Data berhasil dihapus!")

    st.divider()
    st.subheader("📋 TABEL HASIL SCRAPING")

    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            csv,
            "hasil_scraping_instagram.csv",
            "text/csv"
        )
    else:
        st.info("Belum ada data hasil scraping.")

with tab2:
    st.title("📊 Dashboard Monitoring")

    st.components.v1.iframe(
        src=LOOKER_EMBED_URL,
        width=1400,
        height=630,
        scrolling=True
    )
