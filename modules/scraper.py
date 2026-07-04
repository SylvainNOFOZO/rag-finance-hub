# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER — Collecte d'informations sur le net (RSS + extraction d'articles)
# Domaines : Finance · Trading · Économie · Économétrie
# Stockage : table Supabase rag_documents
# ══════════════════════════════════════════════════════════════════════════════
import streamlit as st
import requests
import feedparser

from modules.config import get_secret
import re
import os
from datetime import datetime
from bs4 import BeautifulSoup

# ── Sources RSS par domaine ─────────────────────────────────────────────────────
FEEDS = {
    "Finance": [
        ("Yahoo Finance",   "https://finance.yahoo.com/news/rssindex"),
        ("Les Échos Marchés", "https://services.lesechos.fr/rss/les-echos-finance-marches.xml"),
        ("Investing FR",    "https://fr.investing.com/rss/news.rss"),
        ("CNBC Finance",    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"),
    ],
    "Trading": [
        ("FXStreet",   "https://www.fxstreet.com/rss/news"),
        ("ForexLive",  "https://www.forexlive.com/feed/news"),
        ("DailyForex", "https://www.dailyforex.com/rss/forexnews.xml"),
        ("Investing Commodities", "https://fr.investing.com/rss/news_11.rss"),
    ],
    "Économie": [
        ("Le Monde Économie", "https://www.lemonde.fr/economie/rss_full.xml"),
        ("Les Échos Économie", "https://services.lesechos.fr/rss/les-echos-economie.xml"),
        ("VoxEU / CEPR",  "https://cepr.org/rss/voxeu"),
        ("La Tribune",    "https://www.latribune.fr/feed.xml"),
    ],
    "Économétrie": [
        ("arXiv Econometrics",  "https://arxiv.org/rss/econ.EM"),
        ("arXiv Stat Finance",  "https://arxiv.org/rss/q-fin.ST"),
        ("arXiv Applied Stats", "https://arxiv.org/rss/stat.AP"),
    ],
}

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 RAGFinanceHub/1.0"}


def _sb():
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_KEY")
    hdr = {"apikey": key, "Authorization": f"Bearer {key}",
           "Content-Type": "application/json"}
    return f"{url}/rest/v1/rag_documents", hdr


def clean_html(raw: str) -> str:
    """Supprime les balises HTML et normalise les espaces."""
    if not raw:
        return ""
    try:
        text = BeautifulSoup(raw, "html.parser").get_text(" ")
    except Exception:
        text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", text).strip()


def fetch_feed(source_name: str, feed_url: str, domain: str, max_items: int = 15):
    """Parse un flux RSS → liste de documents."""
    docs = []
    try:
        resp = requests.get(feed_url, headers=UA, timeout=12)
        parsed = feedparser.parse(resp.content)
        for entry in parsed.entries[:max_items]:
            title = clean_html(entry.get("title", ""))
            summary = clean_html(entry.get("summary", entry.get("description", "")))
            link = entry.get("link", "")
            pub = entry.get("published", entry.get("updated", ""))
            try:
                pub_dt = datetime(*entry.published_parsed[:6]).isoformat()
            except Exception:
                pub_dt = datetime.now().isoformat()
            if title and link:
                docs.append({
                    "domain": domain,
                    "title": title,
                    "url": link,
                    "content": f"{title}. {summary}"[:4000],
                    "source": source_name,
                    "published": pub_dt,
                })
    except Exception:
        pass
    return docs


def scrape_domains(domains: list, progress_cb=None):
    """Scrape tous les flux des domaines sélectionnés."""
    all_docs = []
    tasks = [(d, s, u) for d in domains for (s, u) in FEEDS.get(d, [])]
    for i, (domain, sname, surl) in enumerate(tasks):
        if progress_cb:
            progress_cb((i + 1) / len(tasks), f"{domain} · {sname}")
        all_docs.extend(fetch_feed(sname, surl, domain))
    return all_docs


def save_documents(docs: list):
    """Upsert dans Supabase (dédupliqué par URL). Retourne le nb inséré."""
    if not docs:
        return 0
    ep, hdr = _sb()
    inserted = 0
    # Insertion par lots de 50
    for i in range(0, len(docs), 50):
        batch = docs[i:i + 50]
        try:
            r = requests.post(
                ep,
                headers={**hdr, "Prefer": "resolution=ignore-duplicates"},
                json=batch, timeout=20)
            if r.status_code in (200, 201):
                inserted += len(batch)
        except Exception:
            pass
    return inserted


def load_documents(domains: list = None, limit: int = 800):
    """Charge les documents depuis Supabase."""
    ep, hdr = _sb()
    q = f"{ep}?select=*&order=published.desc&limit={limit}"
    if domains:
        dom_list = ",".join(f'"{d}"' for d in domains)
        q += f"&domain=in.({dom_list})"
    try:
        r = requests.get(q, headers=hdr, timeout=15)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def count_documents():
    ep, hdr = _sb()
    try:
        r = requests.get(f"{ep}?select=id", headers={**hdr, "Prefer": "count=exact"},
                         timeout=10)
        cr = r.headers.get("content-range", "/0")
        return int(cr.split("/")[-1])
    except Exception:
        return 0


def delete_all_documents():
    ep, hdr = _sb()
    try:
        r = requests.delete(f"{ep}?id=gt.0", headers=hdr, timeout=20)
        return r.status_code in (200, 204)
    except Exception:
        return False


def scraper_page():
    """Page Streamlit : lancement du scraping."""
    st.markdown("## Collecte d'informations")
    st.caption("Scraping des flux RSS spécialisés — les documents alimentent le "
               "chatbot RAG, les dashboards et les nuages de mots.")

    n_docs = count_documents()
    st.markdown(
        f"<div style='background:#111520;border:1px solid #1e2535;border-radius:12px;"
        f"padding:14px 20px;margin-bottom:16px'>"
        f"<span style='color:#8892a4'>Documents en base :</span> "
        f"<b style='color:#00d4aa;font-size:20px;font-family:monospace'>{n_docs}</b></div>",
        unsafe_allow_html=True)

    domains = st.multiselect(
        "Domaines à scraper",
        list(FEEDS.keys()),
        default=list(FEEDS.keys()),
    )

    with st.expander("Sources par domaine"):
        for d in domains:
            st.markdown(f"**{d}**")
            for sname, surl in FEEDS[d]:
                st.markdown(f"- {sname} — `{surl}`")

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Lancer la collecte", icon=":material/travel_explore:",
                     use_container_width=True, type="primary"):
            if not domains:
                st.warning("Sélectionnez au moins un domaine.")
            else:
                pbar = st.progress(0.0, text="Initialisation…")
                docs = scrape_domains(
                    domains,
                    progress_cb=lambda p, txt: pbar.progress(p, text=f"Scraping : {txt}"))
                pbar.progress(1.0, text="Sauvegarde en base…")
                n = save_documents(docs)
                pbar.empty()
                st.success(f"{len(docs)} articles collectés · {n} traités en base "
                           f"(doublons ignorés automatiquement).")
                st.session_state.pop("_rag_index", None)  # invalider l'index RAG
                st.rerun()
    with c2:
        if st.button("Vider la base documentaire", icon=":material/delete_sweep:",
                     use_container_width=True):
            st.session_state["confirm_wipe_docs"] = True

    if st.session_state.get("confirm_wipe_docs"):
        st.error("Supprimer TOUS les documents collectés ?")
        wc1, wc2, _ = st.columns([1, 1, 4])
        with wc1:
            if st.button("Oui, tout supprimer", key="wipe_yes"):
                delete_all_documents()
                st.session_state.pop("confirm_wipe_docs", None)
                st.session_state.pop("_rag_index", None)
                st.rerun()
        with wc2:
            if st.button("Annuler", key="wipe_no"):
                st.session_state.pop("confirm_wipe_docs", None)
                st.rerun()

    # Aperçu des derniers documents
    st.markdown("---")
    st.markdown("#### Derniers documents collectés")
    recent = load_documents(limit=15)
    if not recent:
        st.info("Aucun document. Lancez une collecte.")
    else:
        for doc in recent:
            dom_colors = {"Finance": "#00d4aa", "Trading": "#7c6aff",
                          "Économie": "#ff9f43", "Économétrie": "#54a0ff"}
            dc = dom_colors.get(doc.get("domain", ""), "#8892a4")
            pub = str(doc.get("published", ""))[:16].replace("T", " ")
            st.markdown(
                f"<div style='background:#111520;border:1px solid #1e2535;"
                f"border-radius:10px;padding:10px 16px;margin-bottom:8px'>"
                f"<span style='color:{dc};font-size:11px;font-weight:700;"
                f"text-transform:uppercase'>{doc.get('domain','')}</span> "
                f"<span style='color:#6b7894;font-size:11px'> · {doc.get('source','')} · {pub}</span><br>"
                f"<a href='{doc.get('url','')}' target='_blank' "
                f"style='color:#e8ecf4;text-decoration:none;font-weight:600'>"
                f"{doc.get('title','')}</a></div>",
                unsafe_allow_html=True)
