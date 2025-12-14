import streamlit as st
import pandas as pd
import time
import re
from playwright.sync_api import sync_playwright

# ==================== CONFIG ====================
st.set_page_config(page_title="InstaMon BPS", layout="wide")

LOOKER_EMBED_URL = "https://lookerstudio.google.com/embed/reporting/f8d6fc1b-b5bd-43eb-881c-e74a9d86ff75/page/Z52hF"

# ==================== SESSION ====================
if "data" not in st.session_state:
    st.session_state.data = []

# ==================== CLEANING ====================
def clean_caption(text):
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ==================== PLAYWRIGHT SCRAPER ====================
def scrape_instagram_playwright(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        page.goto(url, timeout=60000)
        page.wait_for_timeout(4000)

        # ===== CAPTION =====
        caption = ""
        try:
            caption = page.locator("article span").first.inner_text()
        except:
            caption = ""

        # ===== TANGGAL =====
        tanggal = ""
        try:
            dt = page.locator("time").get_attribute("datetime")
            tanggal = dt[:10]
        except:
            tanggal = ""

        browser.close()

        return {
            "Caption": clean_caption(caption),
            "Tanggal": tanggal,
            "Link": url
        }

# ==================== UI ====================
tab1, tab2 = st.tabs(["🛠️ Tools Input Data", "📊 Dashboard Monitoring"])

with tab1:
    st.title("🛠️ InstaMon Instagram Monitoring")
    st.caption("Mode cepat • Tanpa login • Untuk monitoring kegiatan")

    st.warning(
        "⚠️ Ketentuan Aman:\n"
        "- Maksimal 5 link per proses\n"
        "- Delay 5 detik / link\n"
        "- Jalankan secara lokal"
    )

    links_text = st.text_area(
        "Masukkan link Instagram (1 per baris)",
        height=150,
        placeholder="https://www.instagram.com/p/xxxxx/"
    )

    if st.button("🚀 Proses Data"):
        links = [l.strip() for l in links_text.splitlines() if l.strip()]

        if len(links) > 5:
            st.error("❌ Maksimal 5 link per proses")
        else:
            sukses, gagal = 0, 0

            with st.spinner("Mengambil data dari Instagram..."):
                for i, link in enumerate(links, start=1):
                    try:
                        data = scrape_instagram_playwright(link)
                        st.session_state.data.append(data)
                        sukses += 1
                        st.success(f"✅ ({i}/{len(links)}) Berhasil")
                    except Exception as e:
                        gagal += 1
                        st.warning(f"⚠️ ({i}/{len(links)}) Gagal")

                    time.sleep(5)

            st.success(f"🎉 Selesai | Berhasil: {sukses} | Gagal: {gagal}")

    st.divider()

    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            csv,
            "hasil_monitoring_instagram.csv",
            "text/csv"
        )
    else:
        st.info("Belum ada data.")

with tab2:
    st.title("📊 Dashboard Monitoring")
    st.components.v1.iframe(
        src=LOOKER_EMBED_URL,
        width=1200,
        height=650
    )
