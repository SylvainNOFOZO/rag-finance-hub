# ══════════════════════════════════════════════════════════════════════════════
# NUAGE DE MOTS — Ce qui se dit sur un thème donné
# ══════════════════════════════════════════════════════════════════════════════
import streamlit as st
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from wordcloud import WordCloud

from modules.scraper import load_documents
from modules.rag import STOPWORDS_FR_EN, retrieve


def build_wordcloud(theme: str, domains=None, max_words: int = 80):
    """Génère un nuage de mots à partir des documents liés au thème."""
    # 1. Documents pertinents via RAG (TF-IDF), fallback = filtre texte simple
    ctx = retrieve(theme, domains=domains, k=40)
    if not ctx:
        docs = load_documents(domains=domains, limit=500)
        theme_low = theme.lower()
        ctx = [d for d in docs
               if theme_low in f"{d.get('title','')} {d.get('content','')}".lower()]
    if not ctx:
        return None, 0

    text = " ".join(f"{d.get('title','')} {d.get('content','')}" for d in ctx)
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    tokens = re.findall(r"[A-Za-zÀ-ÿ]{4,}", text.lower())
    tokens = [t for t in tokens if t not in STOPWORDS_FR_EN
              and t != theme.lower()]
    if not tokens:
        return None, len(ctx)

    wc = WordCloud(
        width=1100, height=500,
        background_color="#0a0c12",
        colormap="viridis",
        max_words=max_words,
        prefer_horizontal=0.9,
        min_font_size=10,
    ).generate(" ".join(tokens))

    fig, ax = plt.subplots(figsize=(11, 5), facecolor="#0a0c12")
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    fig.tight_layout(pad=0)
    return fig, len(ctx)


def wordcloud_page():
    st.markdown("## Nuage de mots")
    st.caption("Visualisez ce qui se dit autour d'un thème dans les documents "
               "collectés. Le dernier sujet abordé dans le chatbot est proposé "
               "par défaut.")

    default_theme = st.session_state.get("last_theme", "")
    tc1, tc2 = st.columns([3, 2])
    with tc1:
        theme = st.text_input("Thème", value=default_theme,
                              placeholder="Ex : inflation, bitcoin, or, taux Fed…")
    with tc2:
        domains = st.multiselect(
            "Domaines", ["Finance", "Trading", "Économie", "Économétrie"],
            default=["Finance", "Trading", "Économie", "Économétrie"],
            key="wc_domains")

    max_words = st.slider("Nombre de mots", 30, 150, 80, step=10)

    if st.button("Générer le nuage", icon=":material/cloud:", type="primary"):
        if not theme.strip():
            st.warning("Saisissez un thème.")
            return
        with st.spinner("Analyse des documents…"):
            fig, n_docs = build_wordcloud(theme.strip(), domains or None, max_words)
        if fig is None:
            st.warning(f"Aucun document trouvé sur « {theme} ». "
                       "Lancez une collecte ou essayez un autre thème.")
        else:
            st.markdown(
                f"<div style='color:#6b7894;font-size:13px;margin-bottom:8px'>"
                f"Basé sur <b style='color:#00d4aa'>{n_docs}</b> documents "
                f"pertinents</div>", unsafe_allow_html=True)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
