import streamlit as st
import pandas as pd
import requests
import re

st.set_page_config(page_title="InstaMon BPS", layout="wide")

LOOKER_EMBED_URL = "https://lookerstudio.google.com/embed/reporting/f8d6fc1b-b5bd-43eb-881c-e74a9d86ff75/page/Z52hF"

# ==================== SESSION ====================
if "data" not in st.session_state:
    st.session_state.data = []

# ==================== CLEAN ====================
def clean_caption(text):
    text = text or ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ==================== OEMBED ====================
def scrape_instagram_oembed(url):
    api = "https://graph.facebook.com/v17.0/instagram_oembed"
    params = {
        "url": url,
        "omitscript": True
    }

    r = requests.get(api, params=params, timeout=15)

    if r.status_code != 200:
        raise Exception("oEmbed gagal")

    data = r.json()

    caption = data.get("title", "")
    return clean_caption(caption)

# ==================== UI ====================
tab1, tab2 = st.tabs(["🛠️ Tools Input Data", "📊 Dashboard Monitoring"])

with tab1:
    st.title("🛠️ InstaMon Instagram Monitoring (Safe Mode)")
    st.caption("Mode resmi • Tanpa login • Untuk monitoring kegiatan")

    st.info(
        "ℹ️ Mode Aman (oEmbed Resmi)\n"
        "- Hampir tidak diblok\n"
        "- Caption bisa terpotong\n"
        "- Tanggal bisa diisi manual"
    )

    links_text = st.text_area(
        "Masukkan link Instagram (1 per baris)",
        height=150,
        placeholder="https://www.instagram.com/p/xxxxx/"
    )

    tanggal_default = st.text_input(
        "Tanggal kegiatan (opsional, format YYYY-MM-DD)",
        placeholder="2025-01-15"
    )

    if st.button("🚀 Proses Data"):
        links = [l.strip() for l in links_text.splitlines() if l.strip()]
        sukses, gagal = 0, 0

        with st.spinner("Mengambil data dari Instagram (safe mode)..."):
            for i, link in enumerate(links, start=1):
                try:
                    caption = scrape_instagram_oembed(link)
                    st.session_state.data.append({
                        "Caption": caption,
                        "Tanggal": tanggal_default,
                        "Link": link
                    })
                    sukses += 1
                    st.success(f"✅ ({i}/{len(links)}) Berhasil")
                except:
                    gagal += 1
                    st.warning(f"⚠️ ({i}/{len(links)}) Gagal")

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
