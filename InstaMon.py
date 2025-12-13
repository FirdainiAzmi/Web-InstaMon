import streamlit as st
import instaloader
import pandas as pd
import re

st.set_page_config(page_title="InstaMon BPS", layout="wide")

LOOKER_EMBED_URL = "https://lookerstudio.google.com/embed/reporting/f8d6fc1b-b5bd-43eb-881c-e74a9d86ff75/page/Z52hF"

if "data" not in st.session_state:
    st.session_state.data = []

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

def scrape_instagram(url):
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        save_metadata=False,
        compress_json=False
    )

    shortcode = url.split("/")[-2]
    post = instaloader.Post.from_shortcode(loader.context, shortcode)

    caption = clean_caption(post.caption or "")
    tanggal = post.date.strftime("%d/%m/%Y")

    return {
        "Caption": caption,
        "Tanggal": tanggal,
        "Link": url
    }

# ==================== STYLE CSS ====================
st.markdown("""
<style>
/* Header gradient */
.header-gradient {
    background: linear-gradient(90deg, #1E3C72, #2A5298);
    color: white;
    padding: 25px;
    border-radius: 15px;
    text-align: center;
    font-size: 38px;
    font-weight: bold;
    box-shadow: 0px 4px 20px rgba(0,0,0,0.2);
}

/* Subtitle */
.subtitle {
    color: #0B3D91;
    font-size: 20px;
    font-weight: 600;
    margin-bottom: 15px;
}

/* Card Container */
.card {
    background-color: #F0F8FF;
    padding: 25px;
    border-radius: 20px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    margin-bottom: 20px;
}

/* Buttons */
.stButton>button {
    background-color: #0B3D91;
    color: white;
    border-radius: 12px;
    padding: 0.7em 1.5em;
    font-weight: bold;
    border: none;
    font-size: 16px;
}
.stButton>button:hover {
    background-color: #1E5BB8;
    color: white;
}

/* Instagram mini card */
.insta-card {
    background-color: white;
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.1);
    margin-bottom: 15px;
    transition: transform 0.2s;
}
.insta-card:hover {
    transform: translateY(-5px);
}
.insta-caption {
    font-size: 16px;
    color: #0B3D91;
    margin-bottom: 8px;
}
.insta-date {
    font-size: 14px;
    color: #555555;
    margin-bottom: 10px;
}
.insta-link a {
    color: #1E3C72;
    text-decoration: none;
    font-weight: bold;
}
.insta-link a:hover {
    text-decoration: underline;
}
</style>
""", unsafe_allow_html=True)

# ==================== TABS ====================
tab1, tab2 = st.tabs(["🛠️ Tools Input Data", "📊 Dashboard Monitoring"])

# -------------------- TAB 1 --------------------
with tab1:
    st.markdown('<div class="header-gradient">🛠️ InstaMon Instagram Scraper</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Masukkan link Instagram (1 link per baris)</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)

        links_text = st.text_area(
            "Input link di sini:",
            height=150,
            placeholder="https://www.instagram.com/p/xxxx/\nhttps://www.instagram.com/reel/yyyy/"
        )

        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("🚀 Proses Data"):
                if not links_text.strip():
                    st.warning("⚠️ Link tidak boleh kosong!")
                else:
                    links = [x.strip() for x in links_text.splitlines() if x.strip()]
                    sukses = 0
                    with st.spinner("Mengambil data dari Instagram..."):
                        for link in links:
                            try:
                                hasil = scrape_instagram(link)
                                st.session_state.data.append(hasil)
                                sukses += 1
                            except:
                                st.error(f"Gagal mengambil: {link}")
                    st.success(f"✅ {sukses} data berhasil diproses!")

        with col2:
            if st.button("🗑️ Reset Data"):
                st.session_state.data = []
                st.success("✅ Semua data berhasil dihapus!")

        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("📋 Hasil Scraping (Preview Instagram Feed)")

    if st.session_state.data:
        for item in st.session_state.data[::-1]:  # tampilkan terbaru di atas
            st.markdown(f"""
            <div class="insta-card">
                <div class="insta-caption">{item['Caption']}</div>
                <div class="insta-date">{item['Tanggal']}</div>
                <div class="insta-link"><a href="{item['Link']}" target="_blank">Lihat di Instagram</a></div>
            </div>
            """, unsafe_allow_html=True)

        # Download CSV
        df = pd.DataFrame(st.session_state.data)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            csv,
            "hasil_scraping_instagram.csv",
            "text/csv",
            key="download-csv"
        )
    else:
        st.info("Belum ada data yang diproses.")

# -------------------- TAB 2 --------------------
with tab2:
    st.markdown('<div class="header-gradient">📊 Dashboard Monitoring</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Pantau hasil scraping melalui dashboard berikut:</div>', unsafe_allow_html=True)

    if LOOKER_EMBED_URL.strip() == "":
        st.warning("Dashboard belum ditautkan.")
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.components.v1.iframe(
            src=LOOKER_EMBED_URL,
            width=1200,
            height=650,
            scrolling=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
