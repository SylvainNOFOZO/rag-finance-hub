# ══════════════════════════════════════════════════════════════════════════════
# RAG FINANCE HUB
# Scraping · Chatbot RAG (Claude) · Dashboards · Nuages de mots ·
# Calendrier économique · Authentification admin
# ══════════════════════════════════════════════════════════════════════════════
import streamlit as st

st.set_page_config(
    page_title="RAG Finance Hub",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS global ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
.stApp { background-color: #0a0c12; }
section[data-testid="stSidebar"] > div { background-color:#0c0f1a; border-right:1px solid #1e2535; }
h1,h2,h3,h4,h5,h6,p,label,.stMarkdown { color:#e8ecf4 !important; }
.stSelectbox label,.stTextInput label,.stMultiSelect label,.stSlider label {
    color:#8892a4 !important; font-size:11px !important;
    text-transform:uppercase; letter-spacing:1px; }
.stButton > button[kind="primary"] { background-color:#00d4aa; color:#000;
    font-weight:800; border:none; border-radius:10px; }
.stButton > button { border-radius:10px; font-weight:700; }
hr { border-color:#1e2535 !important; }
div[data-testid="stChatMessage"] { background:#111520; border:1px solid #1e2535;
    border-radius:12px; }
</style>
""", unsafe_allow_html=True)

from modules.auth import login_gate, logout, admin_panel
from modules.scraper import scraper_page, count_documents
from modules.rag import chatbot_page
from modules.dashboard import dashboard_page
from modules.wordcloud_gen import wordcloud_page
from modules.calendar_eco import calendar_page

# ── Porte d'authentification ──────────────────────────────────────────────────
if not login_gate():
    st.stop()

# ── Navigation ────────────────────────────────────────────────────────────────
if "nav" not in st.session_state:
    st.session_state.nav = "chat"

PAGES = [
    ("chat",      "Chatbot",     ":material/forum:"),
    ("scrape",    "Collecte",    ":material/travel_explore:"),
    ("dash",      "Dashboard",   ":material/monitoring:"),
    ("cloud",     "Nuage de mots", ":material/cloud:"),
    ("calendar",  "Annonces éco", ":material/event:"),
]

with st.sidebar:
    st.markdown("## RAG Finance Hub")
    st.caption(f"Connecté : **{st.session_state.auth_user}** "
               f"({st.session_state.auth_role})")
    st.divider()

    for key, label, icon in PAGES:
        if st.button(f"  {label}", icon=icon, use_container_width=True,
                     type="primary" if st.session_state.nav == key else "secondary",
                     key=f"nav_{key}"):
            st.session_state.nav = key
            st.rerun()

    if st.session_state.auth_role == "admin":
        if st.button("  Utilisateurs", icon=":material/manage_accounts:",
                     use_container_width=True,
                     type="primary" if st.session_state.nav == "admin" else "secondary",
                     key="nav_admin"):
            st.session_state.nav = "admin"
            st.rerun()

    st.divider()
    n = count_documents()
    st.markdown(
        f"<div style='background:#00d4aa14;border:1px solid #00d4aa44;"
        f"border-radius:8px;padding:7px 12px;font-size:12px;color:#00d4aa'>"
        f"📚 {n} documents en base</div>", unsafe_allow_html=True)
    st.markdown(" ")
    if st.button("  Déconnexion", icon=":material/logout:",
                 use_container_width=True):
        logout()

# ── Routage ───────────────────────────────────────────────────────────────────
nav = st.session_state.nav
if nav == "chat":
    chatbot_page()
elif nav == "scrape":
    scraper_page()
elif nav == "dash":
    dashboard_page()
elif nav == "cloud":
    wordcloud_page()
elif nav == "calendar":
    calendar_page()
elif nav == "admin":
    admin_panel()
