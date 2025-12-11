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
    tanggal = post.date.strftime("%m/%d/%Y")

    return {
        "Caption": caption,
        "Tanggal": tanggal,
        "Link": url
    }

tab1, tab2 = st.tabs(["🛠️ Tools Input Data", "📊 Dashboard Monitoring"])
with tab1:
    st.title("🛠️ Tools Scraping Instagram")

    st.write("Masukkan **banyak link Instagram (1 link per baris)**")

    links_text = st.text_area(
        "Input link di sini:",
        height=150,
        placeholder="https://www.instagram.com/p/xxxx/\nhttps://www.instagram.com/reel/yyyy/"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 PROSES DATA"):
            if not links_text.strip():
                st.warning("Link tidak boleh kosong!")
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
        if st.button("🗑️ RESET DATA"):
            st.session_state.data = []
            st.success("✅ Semua data berhasil dihapus!")

    st.divider()
    st.subheader("📋 TABEL HASIL SCRAPING")

    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True)

        # DOWNLOAD CSV
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            csv,
            "hasil_scraping_instagram.csv",
            "text/csv"
        )
    else:
        st.info("Belum ada data yang diproses.")
with tab2:
    st.title("📊 Dashboard Monitoring")

    if LOOKER_EMBED_URL.strip() == "":
        st.warning("Dashboard belum ditautkan.")
    else:
        st.components.v1.iframe(
            src=LOOKER_EMBED_URL,
            width=1400,
            height=620,
            scrolling=True
        )









