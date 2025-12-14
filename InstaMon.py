import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import json

st.set_page_config(page_title="InstaMon BPS", layout="wide")

LOOKER_EMBED_URL = "https://lookerstudio.google.com/embed/reporting/f8d6fc1b-b5bd-43eb-881c-e74a9d86ff75/page/Z52hF"

# ==================== SESSION ====================
if "data" not in st.session_state:
    st.session_state.data = []

# ==================== HEADERS (ANTI BOT) ====================
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ==================== CLEANING ====================
def first_sentence(text):
    match = re.search(r"(.+?[.!?])", text)
    return match.group(1) if match else text

def clean_caption(text):
    text = (text or "").replace("\n", " ").replace("\r", " ")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = first_sentence(text)
    text = re.sub(r"[^A-Za-z0-9 ,.!?]+", " ", text)
    return " ".join(text.split()).strip()

# ==================== HTML SCRAPER ====================
def scrape_instagram_html(url):
    r = requests.get(url, headers=HEADERS, timeout=15)

    if r.status_code != 200:
        raise Exception("HTTP blocked")

    soup = BeautifulSoup(r.text, "html.parser")
    script = soup.find("script", type="application/ld+json")

    if not script:
        raise Exception("Metadata tidak ditemukan")

    data = json.loads(script.string)

    caption = clean_caption(data.get("caption", ""))
    tanggal = data.get("uploadDate", "")[:10]

    return {
        "Caption": caption,
        "Tanggal": tanggal,
        "Link": url
    }

# ==================== UI ====================
tab1, tab2 = st.tabs(["🛠️ Tools Input Data", "📊 Dashboard Monitoring"])

with tab1:
    st.title("🛠️ InstaMon Instagram Scraper (HTML Mode)")

    st.info(
        "Mode TANPA LOGIN\n"
        "- Maks 5 link per proses\n"
        "- Delay 6 detik / link\n"
        "- Reel / post baru bisa gagal"
    )

    links_text = st.text_area(
        "Masukkan link Instagram (1 per baris)",
        height=150,
        placeholder="https://www.instagram.com/p/xxxx/"
    )

    if st.button("🚀 Proses Data"):
        links = [l.strip() for l in links_text.splitlines() if l.strip()]

        if len(links) > 5:
            st.error("❌ Maksimal 5 link per proses")
        else:
            sukses, gagal = 0, 0

            with st.spinner("Mengambil data (safe mode)..."):
                for i, link in enumerate(links, start=1):
                    try:
                        hasil = scrape_instagram_html(link)
                        st.session_state.data.append(hasil)
                        sukses += 1
                        st.success(f"✅ ({i}/{len(links)}) Berhasil")
                    except Exception:
                        gagal += 1
                        st.warning(f"⚠️ ({i}/{len(links)}) Gagal")

                    time.sleep(6)

            st.success(f"🎉 Selesai | Berhasil: {sukses} | Gagal: {gagal}")

    st.divider()

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

with tab2:
    st.title("📊 Dashboard Monitoring")
    st.components.v1.iframe(
        src=LOOKER_EMBED_URL,
        width=1200,
        height=650
    )
