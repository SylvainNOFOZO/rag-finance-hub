# ══════════════════════════════════════════════════════════════════════════════
# RAG FINANCE HUB — Application monofichier
# Scraping · Chatbot RAG (Claude) · Dashboards · Nuages de mots ·
# Calendrier économique · Authentification admin
# Déploiement : Hugging Face Spaces (Docker) ou Streamlit local
# ══════════════════════════════════════════════════════════════════════════════
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import feedparser
import hashlib
import os
import re
import secrets as pysecrets
from datetime import datetime
from collections import Counter
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from wordcloud import WordCloud

st.set_page_config(
    page_title="RAG Finance Hub",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# CSS injecté dynamiquement plus bas (dépend du thème choisi par l'utilisateur)


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG — SECRETS
# ══════════════════════════════════════════════════════════════════════════════
def get_secret(name: str, default: str = "") -> str:
    """Env var (HF Spaces) en priorité, puis st.secrets (local)."""
    val = os.environ.get(name, "")
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(name, default)
    except Exception:
        return default


# ══════════════════════════════════════════════════════════════════════════════
# THÈMES
# ══════════════════════════════════════════════════════════════════════════════
THEMES = {
    "Executive": {
        "bg":"#0e1117","bg2":"#131823","card":"#161c28","border":"#242c3d",
        "text":"#e9edf5","muted":"#97a1b3","accent":"#4f8cff","win":"#2dd4a7",
        "loss":"#f0506e","alt":"#9d7bff","orange":"#f5a524","sidebar":"#10141d",
        "btn_text":"#ffffff",
    },
    "Obsidienne Émeraude": {
        "bg":"#0b0e13","bg2":"#0f131b","card":"#12161f","border":"#212836",
        "text":"#e6e9f0","muted":"#8a93a6","accent":"#10b981","win":"#10b981",
        "loss":"#f43f5e","alt":"#8b5cf6","orange":"#f59e0b","sidebar":"#0d1118",
        "btn_text":"#04110c",
    },
    "Bloomberg Noir": {
        "bg":"#050505","bg2":"#0d0d0d","card":"#131313","border":"#2a2a2a",
        "text":"#f2f2f2","muted":"#9a9a9a","accent":"#ff9900","win":"#00d769",
        "loss":"#ff433d","alt":"#2797ff","orange":"#ffb300","sidebar":"#0a0a0a",
        "btn_text":"#1a1000",
    },
    "Graphite Pro": {
        "bg":"#101014","bg2":"#141419","card":"#17171d","border":"#27272f",
        "text":"#ececf1","muted":"#8e8e9a","accent":"#a78bfa","win":"#34d399",
        "loss":"#fb7185","alt":"#60a5fa","orange":"#fbbf24","sidebar":"#121217",
        "btn_text":"#17102b",
    },
    "Corporate Clair": {
        "light": True,
        "bg":"#f8f9fc","bg2":"#f1f3f8","card":"#ffffff","border":"#e6e9f1",
        "text":"#141a26","muted":"#68738a","accent":"#2563eb","win":"#0f9d6e",
        "loss":"#dc3555","alt":"#7c3aed","orange":"#d97706","sidebar":"#ffffff",
        "btn_text":"#ffffff",
    },
}
THEME_NAMES = list(THEMES.keys())

# Couleurs de domaine — deux jeux selon la luminosité du thème
DOM_COLORS_DARK = {
    "Finance": "#00d4aa", "Trading": "#7c6aff", "Économie": "#ff9f43",
    "Économétrie": "#54a0ff", "Crypto": "#fdcb6e", "Matières Premières": "#ff4d6d",
    "Géopolitique & Marchés": "#00cec9",
}
DOM_COLORS_LIGHT = {
    "Finance": "#0f766e", "Trading": "#6d28d9", "Économie": "#b45309",
    "Économétrie": "#1d4ed8", "Crypto": "#a16207", "Matières Premières": "#b91c1c",
    "Géopolitique & Marchés": "#0e7490",
}


def dom_color(domain):
    t = THEMES.get(st.session_state.get("theme_name", THEME_NAMES[0]),
                   THEMES[THEME_NAMES[0]])
    table = DOM_COLORS_LIGHT if t.get("light") else DOM_COLORS_DARK
    return table.get(domain, t["muted"])


def chart_palette():
    t = THEMES.get(st.session_state.get("theme_name", THEME_NAMES[0]),
                   THEMES[THEME_NAMES[0]])
    if t.get("light"):
        return ["#0f766e","#6d28d9","#b45309","#1d4ed8","#b91c1c",
                "#0e7490","#a16207","#4c1d95","#be185d","#065f46"]
    return ["#00d4aa","#7c6aff","#ff9f43","#54a0ff","#ff4d6d",
            "#00cec9","#fdcb6e","#5f27cd","#fd79a8","#0984e3"]


def get_theme():
    name = st.session_state.get("theme_name", THEME_NAMES[0])
    return THEMES.get(name, THEMES[THEME_NAMES[0]])


def build_css(t):
    """CSS professionnel complet — couvre tous les composants Streamlit/BaseWeb."""
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css');

/* ── Base ─────────────────────────────────────────────────────────────── */
.stApp {{ background: {t['bg']}; font-family:'Inter',sans-serif; }}
header[data-testid="stHeader"] {{ background: {t['bg']}; }}
section[data-testid="stSidebar"] {{ display:none; }}
button[data-testid="stBaseButton-headerNoPadding"] {{ display:none; }}
.block-container {{ padding-top: 2rem; max-width: 1400px; }}

/* ── Typographie ──────────────────────────────────────────────────────── */
h1,h2,h3,h4,h5,h6 {{ color:{t['text']} !important; font-family:'Inter',sans-serif; }}
p, label, .stMarkdown p, .stMarkdown li {{ color:{t['text']}; }}
[data-testid="stCaptionContainer"], small {{ color:{t['muted']} !important; }}
a {{ color:{t['accent']}; }}
hr {{ border-color:{t['border']} !important; }}

/* ── Labels de widgets ────────────────────────────────────────────────── */
.stSelectbox label p,.stTextInput label p,.stMultiSelect label p,
.stSlider label p,.stDateInput label p,.stNumberInput label p,
.stTextArea label p,.stRadio label p {{
    color:{t['muted']} !important; font-size:11px !important;
    text-transform:uppercase; letter-spacing:1px; font-weight:600; }}

/* ── Champs de saisie ─────────────────────────────────────────────────── */
div[data-baseweb="select"] > div,
div[data-baseweb="base-input"],
.stTextInput input, .stNumberInput input, .stTextArea textarea,
.stDateInput input {{
    background:{t['bg2']} !important; border-color:{t['border']} !important;
    color:{t['text']} !important; border-radius:10px; }}
div[data-baseweb="select"] svg {{ fill:{t['muted']}; }}

/* ── Menus déroulants ─────────────────────────────────────────────────── */
div[data-baseweb="popover"] > div,
ul[role="listbox"] {{
    background:{t['card']} !important; border:1px solid {t['border']} !important;
    border-radius:10px; }}
li[role="option"] {{ background:{t['card']} !important; color:{t['text']} !important; }}
li[role="option"]:hover {{ background:{t['accent']}22 !important; }}

/* ── Chips multiselect ────────────────────────────────────────────────── */
span[data-baseweb="tag"] {{
    background:{t['accent']}22 !important; border:1px solid {t['accent']}55 !important;
    border-radius:8px; }}
span[data-baseweb="tag"] span {{ color:{t['accent']} !important; }}
span[data-baseweb="tag"] svg {{ fill:{t['accent']} !important; }}

/* ── Boutons ──────────────────────────────────────────────────────────── */
.stButton > button {{ border-radius:12px; font-weight:700; transition:all .15s;
    box-shadow:0 1px 2px rgba(0,0,0,.08); }}
.stButton > button[kind="primary"] {{
    background:{t['accent']}; color:{t['btn_text']}; border:none; font-weight:800; }}
.stButton > button[kind="primary"]:hover {{ filter:brightness(1.08); }}
.stButton > button[kind="secondary"] {{
    background:{t['card']}; color:{t['text']}; border:1px solid {t['border']}; }}
.stButton > button[kind="secondary"]:hover {{
    border-color:{t['accent']}; color:{t['accent']}; }}
.stDownloadButton > button {{
    background:{t['card']}; color:{t['text']}; border:1px solid {t['border']};
    border-radius:10px; font-weight:700; }}
.stDownloadButton > button:hover {{ border-color:{t['accent']}; color:{t['accent']}; }}
.stFormSubmitButton > button {{
    background:{t['accent']}; color:{t['btn_text']}; border:none;
    border-radius:10px; font-weight:800; }}

/* ── Chat ─────────────────────────────────────────────────────────────── */
div[data-testid="stChatMessage"] {{
    background:{t['card']}; border:1px solid {t['border']}; border-radius:14px; }}
div[data-testid="stBottom"] > div {{ background:{t['bg']}; }}
div[data-testid="stChatInput"] {{
    background:{t['bg2']}; border:1px solid {t['border']}; border-radius:12px; }}
div[data-testid="stChatInput"] textarea {{
    background:transparent !important; color:{t['text']} !important; }}

/* ── Expanders / Forms / Tabs ─────────────────────────────────────────── */
div[data-testid="stExpander"] details {{
    background:{t['card']}; border:1px solid {t['border']} !important;
    border-radius:12px; }}
div[data-testid="stExpander"] summary {{ color:{t['text']} !important; }}
div[data-testid="stExpander"] summary:hover {{ color:{t['accent']} !important; }}
div[data-testid="stForm"] {{
    background:{t['card']}; border:1px solid {t['border']}; border-radius:14px; }}
.stTabs [data-baseweb="tab-list"] {{ gap:6px; }}
.stTabs [data-baseweb="tab"] {{
    background:{t['card']}; border:1px solid {t['border']};
    border-radius:8px; color:{t['muted']}; padding:6px 16px; }}
.stTabs [aria-selected="true"] {{
    color:{t['accent']} !important; border-color:{t['accent']} !important; }}

/* ── Divers ───────────────────────────────────────────────────────────── */
.stProgress > div > div > div {{ background:{t['accent']}; }}
.stRadio div[role="radiogroup"] label p {{ color:{t['text']} !important;
    text-transform:none; font-size:14px !important; letter-spacing:0; }}
.stCheckbox label p {{ color:{t['text']} !important; text-transform:none;
    font-size:14px !important; letter-spacing:0; }}
[data-testid="stMetricValue"] {{ color:{t['text']}; }}
::-webkit-scrollbar {{ width:10px; height:10px; }}
::-webkit-scrollbar-track {{ background:{t['bg']}; }}
::-webkit-scrollbar-thumb {{ background:{t['border']}; border-radius:6px; }}
::-webkit-scrollbar-thumb:hover {{ background:{t['muted']}; }}

/* ── Composants maison ────────────────────────────────────────────────── */
.rfh-card {{ background:{t['card']}; border:1px solid {t['border']};
    border-radius:16px; padding:16px 20px;
    box-shadow:0 1px 3px rgba(0,0,0,.10), 0 4px 14px rgba(0,0,0,.06); }}
.rfh-kpi {{ background:{t['card']}; border:1px solid {t['border']};
    border-radius:16px; padding:16px; min-height:96px;
    display:flex; gap:14px; align-items:flex-start;
    box-shadow:0 1px 3px rgba(0,0,0,.10), 0 4px 14px rgba(0,0,0,.06);
    transition:transform .12s, border-color .12s; }}
.rfh-kpi:hover {{ transform:translateY(-2px); border-color:{t['accent']}66; }}
.rfh-kpi-icon {{ width:42px; height:42px; border-radius:12px; flex-shrink:0;
    display:flex; align-items:center; justify-content:center; font-size:17px; }}
.rfh-kpi-bar {{ display:none; }}
.rfh-badge {{ padding:2px 10px; border-radius:8px; font-size:11px;
    font-weight:700; letter-spacing:.4px; display:inline-block; }}
div[data-testid="stExpander"] details {{ border-radius:14px !important;
    box-shadow:0 1px 3px rgba(0,0,0,.08); }}
</style>
"""


# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════
def _sb():
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_KEY")
    hdr = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    return url, hdr


def _users_ep():
    url, hdr = _sb()
    return f"{url}/rest/v1/rag_users", hdr


def hash_password(password: str, salt: str = None) -> str:
    """PBKDF2-HMAC-SHA256 — pas de dépendance externe."""
    if salt is None:
        salt = pysecrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
        return hash_password(password, salt) == stored
    except Exception:
        return False


def bootstrap_admin():
    """Crée l'admin initial depuis les secrets si la table est vide."""
    ep, hdr = _users_ep()
    try:
        r = requests.get(f"{ep}?select=username&limit=1", headers=hdr, timeout=8)
        if r.status_code == 200 and r.json() == []:
            admin_user = get_secret("ADMIN_USERNAME", "admin")
            admin_pass = get_secret("ADMIN_PASSWORD")
            if admin_pass:
                requests.post(ep, headers={**hdr, "Prefer": "resolution=merge-duplicates"},
                    json={"username": admin_user,
                          "password_hash": hash_password(admin_pass),
                          "role": "admin", "active": True}, timeout=8)
    except Exception:
        pass


def authenticate(username: str, password: str):
    """Retourne (ok, role, message)."""
    ep, hdr = _users_ep()
    debug = {"endpoint": ep, "apikey_len": len(hdr.get("apikey", ""))}
    try:
        r = requests.get(ep, headers=hdr, timeout=8,
                         params={"username": f"eq.{username}", "select": "*"})
        debug["status"] = r.status_code
        debug["body"] = r.text[:300]
        st.session_state["_last_auth_debug"] = debug
        if r.status_code != 200:
            return False, None, f"Erreur serveur ({r.status_code}) — voir détails techniques ci-dessous."
        rows = r.json()
        if not rows:
            return False, None, "Identifiants incorrects."
        u = rows[0]
        if not u.get("active", False):
            return False, None, "Compte désactivé. Contactez l'administrateur."
        if verify_password(password, u.get("password_hash", "")):
            return True, u.get("role", "user"), "OK"
        return False, None, "Identifiants incorrects."
    except Exception as e:
        debug["exception"] = str(e)
        st.session_state["_last_auth_debug"] = debug
        return False, None, f"Erreur connexion : {e}"


def list_users():
    ep, hdr = _users_ep()
    try:
        r = requests.get(f"{ep}?select=username,role,active,created_at&order=created_at",
                         headers=hdr, timeout=8)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def create_user(username: str, password: str, role: str = "user"):
    """Réservé à l'admin. Retourne (ok, message)."""
    if not username or not password:
        return False, "Nom d'utilisateur et mot de passe requis."
    if len(password) < 6:
        return False, "Mot de passe : 6 caractères minimum."
    ep, hdr = _users_ep()
    try:
        r = requests.post(ep, headers=hdr,
            json={"username": username.strip(),
                  "password_hash": hash_password(password),
                  "role": role, "active": True}, timeout=8)
        if r.status_code in (200, 201):
            return True, f"Utilisateur « {username} » créé."
        if r.status_code == 409:
            return False, "Ce nom d'utilisateur existe déjà."
        return False, f"Erreur ({r.status_code}) : {r.text[:120]}"
    except Exception as e:
        return False, str(e)


def set_user_active(username: str, active: bool):
    ep, hdr = _users_ep()
    try:
        r = requests.patch(f"{ep}?username=eq.{username}", headers=hdr,
                           json={"active": active}, timeout=8)
        return r.status_code in (200, 204)
    except Exception:
        return False


def delete_user(username: str):
    ep, hdr = _users_ep()
    try:
        r = requests.delete(f"{ep}?username=eq.{username}", headers=hdr, timeout=8)
        return r.status_code in (200, 204)
    except Exception:
        return False


def reset_password(username: str, new_password: str):
    if len(new_password) < 6:
        return False, "Mot de passe : 6 caractères minimum."
    ep, hdr = _users_ep()
    try:
        r = requests.patch(f"{ep}?username=eq.{username}", headers=hdr,
                           json={"password_hash": hash_password(new_password)}, timeout=8)
        if r.status_code in (200, 204):
            return True, "Mot de passe réinitialisé."
        return False, f"Erreur ({r.status_code})"
    except Exception as e:
        return False, str(e)


def login_gate():
    """Affiche le formulaire de connexion. Retourne True si connecté."""
    if st.session_state.get("auth_user"):
        return True

    bootstrap_admin()

    st.markdown(
        "<div style='text-align:center;padding:30px 0 10px'>"
        "<h1 style='margin-bottom:4px'>RAG Finance Hub</h1>"
        f"<p style='color:{get_theme()['muted']}'>Intelligence financière · Trading · Économie · Économétrie</p>"
        "</div>", unsafe_allow_html=True)

    _, c, _ = st.columns([1, 1.2, 1])
    with c:
        with st.form("login_form"):
            st.markdown("#### Connexion")
            username = st.text_input("Utilisateur", autocomplete="username")
            password = st.text_input("Mot de passe", type="password",
                                     autocomplete="current-password")
            if st.form_submit_button("Se connecter", use_container_width=True):
                ok, role, msg = authenticate(username.strip(), password)
                if ok:
                    st.session_state.auth_user = username.strip()
                    st.session_state.auth_role = role
                    st.rerun()
                else:
                    st.error(msg)
        st.caption("Accès sur invitation uniquement — contactez l'administrateur "
                   "pour obtenir vos identifiants.")

        dbg = st.session_state.get("_last_auth_debug")
        if dbg:
            with st.expander("Détails techniques (diagnostic)"):
                st.markdown(f"**Endpoint appelé** : `{dbg.get('endpoint','')}`")
                st.markdown(f"**Longueur clé API envoyée** : {dbg.get('apikey_len',0)} "
                            f"caractères {'⚠️ (0 = secret manquant)' if not dbg.get('apikey_len') else ''}")
                if "status" in dbg:
                    st.markdown(f"**Code HTTP reçu** : {dbg['status']}")
                    st.code(dbg.get("body",""), language="json")
                if "exception" in dbg:
                    st.markdown(f"**Exception Python** : `{dbg['exception']}`")
                url_val = get_secret("SUPABASE_URL")
                st.markdown(f"**SUPABASE_URL lu** : `{url_val}` "
                            f"({'vide ⚠️' if not url_val else 'OK' if url_val.startswith('https://') else 'format suspect ⚠️'})")
    return False


def logout():
    for k in ("auth_user", "auth_role", "chat_history"):
        st.session_state.pop(k, None)
    st.rerun()


def admin_panel():
    """Panneau d'administration des utilisateurs (admin uniquement)."""
    if st.session_state.get("auth_role") != "admin":
        st.error("Accès réservé à l'administrateur.")
        return

    st.markdown("## Gestion des utilisateurs")
    st.caption("Seul l'admin crée les comptes et distribue les mots de passe. "
               "Aucune auto-inscription possible.")

    # ── Créer un utilisateur ────────────────────────────────────────────────
    with st.expander("Créer un utilisateur", expanded=True):
        cc1, cc2, cc3 = st.columns([2, 2, 1])
        with cc1:
            new_user = st.text_input("Nom d'utilisateur", key="nu_name")
        with cc2:
            new_pass = st.text_input("Mot de passe", key="nu_pass",
                                     help="À transmettre à l'utilisateur de façon sécurisée")
        with cc3:
            new_role = st.selectbox("Rôle", ["user", "admin"], key="nu_role")
        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("Créer le compte", icon=":material/person_add:",
                         use_container_width=True):
                ok, msg = create_user(new_user, new_pass, new_role)
                (st.success if ok else st.error)(msg)
        with col_b:
            if st.button("Générer un mot de passe", icon=":material/key:",
                         use_container_width=True):
                st.code(pysecrets.token_urlsafe(10))

    st.markdown("---")

    # ── Liste + actions ─────────────────────────────────────────────────────
    users = list_users()
    if not users:
        st.info("Aucun utilisateur.")
        return

    me = st.session_state.auth_user
    for u in users:
        uc1, uc2, uc3, uc4, uc5 = st.columns([2, 1, 1, 1.2, 1.2])
        _ta = get_theme()
        status_col = _ta["win"] if u["active"] else _ta["loss"]
        with uc1:
            role_badge = "👑" if u["role"] == "admin" else ""
            st.markdown(
                f"<div style='padding-top:8px'><b>{u['username']}</b> {role_badge} "
                f"<span style='color:{status_col};font-size:12px'>"
                f"{'● actif' if u['active'] else '● désactivé'}</span></div>",
                unsafe_allow_html=True)
        with uc2:
            st.markdown(f"<div style='padding-top:8px;color:{_ta['muted']};font-size:12px'>"
                        f"{u['role']}</div>", unsafe_allow_html=True)
        is_me = u["username"] == me
        with uc3:
            if not is_me:
                lbl = "Désactiver" if u["active"] else "Activer"
                if st.button(lbl, key=f"tog_{u['username']}", use_container_width=True):
                    set_user_active(u["username"], not u["active"])
                    st.rerun()
        with uc4:
            npw = st.text_input("Nouveau mdp", key=f"rp_{u['username']}",
                                label_visibility="collapsed",
                                placeholder="Nouveau mot de passe")
        with uc5:
            rc1, rc2 = st.columns(2)
            with rc1:
                if st.button("↻", key=f"rst_{u['username']}",
                             help="Réinitialiser le mot de passe",
                             use_container_width=True):
                    if npw:
                        ok, msg = reset_password(u["username"], npw)
                        (st.success if ok else st.error)(msg)
                    else:
                        st.warning("Saisissez le nouveau mot de passe.")
            with rc2:
                if not is_me:
                    if st.button("✕", key=f"del_{u['username']}",
                                 help="Supprimer définitivement",
                                 use_container_width=True):
                        st.session_state[f"confirm_del_user"] = u["username"]

    # Confirmation suppression
    target = st.session_state.get("confirm_del_user")
    if target:
        st.error(f"Supprimer définitivement le compte « {target} » ?")
        dc1, dc2, _ = st.columns([1, 1, 4])
        with dc1:
            if st.button("Oui, supprimer", key="cfm_del_yes"):
                delete_user(target)
                st.session_state.pop("confirm_del_user", None)
                st.rerun()
        with dc2:
            if st.button("Annuler", key="cfm_del_no"):
                st.session_state.pop("confirm_del_user", None)
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER
# ══════════════════════════════════════════════════════════════════════════════
FEEDS = {
    "Finance": [
        # Français
        ("Les Échos Marchés",  "https://services.lesechos.fr/rss/les-echos-finance-marches.xml", "FR"),
        ("Investing FR",       "https://fr.investing.com/rss/news.rss", "FR"),
        ("Boursorama",         "https://www.boursorama.com/rss/actualites/dernieres-infos.xml", "FR"),
        ("Capital.fr",         "https://www.capital.fr/rss", "FR"),
        ("Zonebourse",         "https://www.zonebourse.com/rss/actualites.xml", "FR"),
        # Anglais
        ("Yahoo Finance",      "https://finance.yahoo.com/news/rssindex", "EN"),
        ("CNBC Finance",       "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", "EN"),
        ("MarketWatch",        "https://feeds.content.dowjones.io/public/rss/mw_topstories", "EN"),
        ("WSJ Markets",        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "EN"),
        ("Seeking Alpha",      "https://seekingalpha.com/market_currents.xml", "EN"),
        ("Fortune",            "https://fortune.com/feed/", "EN"),
        ("Business Insider",   "https://markets.businessinsider.com/rss/news", "EN"),
    ],
    "Trading": [
        # Français
        ("Investing Techniques FR", "https://fr.investing.com/rss/news_25.rss", "FR"),
        ("Investing Forex FR", "https://fr.investing.com/rss/news_1.rss", "FR"),
        # Anglais
        ("FXStreet",           "https://www.fxstreet.com/rss/news", "EN"),
        ("ForexLive",          "https://www.forexlive.com/feed/news", "EN"),
        ("DailyForex",         "https://www.dailyforex.com/rss/forexnews.xml", "EN"),
        ("Kitco News",         "https://www.kitco.com/rss/KitcoNews.xml", "EN"),
        ("FXEmpire",           "https://www.fxempire.com/api/v1/en/articles/rss/news", "EN"),
        ("Action Forex",       "https://www.actionforex.com/feed/", "EN"),
        ("Babypips",           "https://www.babypips.com/feed.rss", "EN"),
    ],
    "Économie": [
        # Français
        ("Le Monde Économie",  "https://www.lemonde.fr/economie/rss_full.xml", "FR"),
        ("Les Échos Économie", "https://services.lesechos.fr/rss/les-echos-economie.xml", "FR"),
        ("La Tribune",         "https://www.latribune.fr/feed.xml", "FR"),
        ("Challenges",         "https://www.challenges.fr/rss.xml", "FR"),
        ("Alternatives Éco",   "https://www.alternatives-economiques.fr/rss.xml", "FR"),
        # Anglais
        ("VoxEU / CEPR",       "https://cepr.org/rss/voxeu", "EN"),
        ("The Economist",      "https://www.economist.com/finance-and-economics/rss.xml", "EN"),
        ("BBC Business",       "http://feeds.bbci.co.uk/news/business/rss.xml", "EN"),
        ("IMF Blog",           "https://www.imf.org/en/Blogs/rss", "EN"),
        ("World Bank Blogs",   "https://blogs.worldbank.org/rss.xml", "EN"),
        ("Project Syndicate",  "https://www.project-syndicate.org/rss", "EN"),
        ("Federal Reserve",    "https://www.federalreserve.gov/feeds/press_all.xml", "EN"),
        ("BCE — Communiqués",  "https://www.ecb.europa.eu/rss/press.xml", "EN"),
        ("Bank of England",    "https://www.bankofengland.co.uk/rss/news", "EN"),
    ],
    "Économétrie": [
        ("arXiv Econometrics", "https://arxiv.org/rss/econ.EM", "EN"),
        ("arXiv Stat Finance", "https://arxiv.org/rss/q-fin.ST", "EN"),
        ("arXiv Applied Stats","https://arxiv.org/rss/stat.AP", "EN"),
        ("arXiv Risk Mgmt",    "https://arxiv.org/rss/q-fin.RM", "EN"),
        ("arXiv Portfolio",    "https://arxiv.org/rss/q-fin.PM", "EN"),
        ("arXiv Gen Finance",  "https://arxiv.org/rss/q-fin.GN", "EN"),
        ("NBER Working Papers","https://back.nber.org/rss/new.xml", "EN"),
    ],
    "Crypto": [
        # Français
        ("Journal du Coin",    "https://journalducoin.com/feed/", "FR"),
        ("Cryptoast",          "https://cryptoast.fr/feed/", "FR"),
        ("Investing Crypto FR","https://fr.investing.com/rss/news_301.rss", "FR"),
        # Anglais
        ("CoinDesk",           "https://www.coindesk.com/arc/outboundfeeds/rss/", "EN"),
        ("CoinTelegraph",      "https://cointelegraph.com/rss", "EN"),
        ("Decrypt",            "https://decrypt.co/feed", "EN"),
        ("Bitcoin Magazine",   "https://bitcoinmagazine.com/feed", "EN"),
        ("The Block",          "https://www.theblock.co/rss.xml", "EN"),
    ],
    "Matières Premières": [
        ("Investing Énergie FR","https://fr.investing.com/rss/news_11.rss", "FR"),
        ("OilPrice.com",       "https://oilprice.com/rss/main", "EN"),
        ("Kitco Commodities",  "https://www.kitco.com/rss/KitcoCommodities.xml", "EN"),
        ("Mining.com",         "https://www.mining.com/feed/", "EN"),
    ],
    "Géopolitique & Marchés": [
        ("Le Monde International","https://www.lemonde.fr/international/rss_full.xml", "FR"),
        ("Les Échos Monde",    "https://services.lesechos.fr/rss/les-echos-monde.xml", "FR"),
        ("BBC World",          "http://feeds.bbci.co.uk/news/world/rss.xml", "EN"),
        ("Foreign Policy",     "https://foreignpolicy.com/feed/", "EN"),
        ("Al Jazeera",         "https://www.aljazeera.com/xml/rss/all.xml", "EN"),
    ],
}
LANGS = ["FR", "EN"]

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 RAGFinanceHub/1.0"}


def _sb_docs():
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_KEY")
    hdr = {"apikey": key, "Authorization": f"Bearer {key}",
           "Content-Type": "application/json"}
    return f"{url}/rest/v1/rag_documents", hdr


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_article_text(url: str) -> str:
    """Extrait le texte complet d'un article web (lecture sans visiter le site)."""
    try:
        r = requests.get(url, headers=UA, timeout=15)
        soup = BeautifulSoup(r.content, "html.parser")
        for tag in soup(["script","style","nav","header","footer",
                         "aside","form","iframe","noscript"]):
            tag.decompose()
        root = soup.find("article") or soup.body or soup
        parts = []
        for el in root.find_all(["h2","h3","p","li"]):
            txt = el.get_text(" ", strip=True)
            if not txt:
                continue
            if el.name in ("h2","h3"):
                parts.append(f"\n## {txt}\n")
            elif len(txt) > 60:
                parts.append(txt)
        text = "\n\n".join(parts)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text if len(text) > 200 else ""
    except Exception:
        return ""


def clean_html(raw: str) -> str:
    """Supprime les balises HTML et normalise les espaces."""
    if not raw:
        return ""
    try:
        text = BeautifulSoup(raw, "html.parser").get_text(" ")
    except Exception:
        text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", text).strip()


def fetch_feed(source_name: str, feed_url: str, domain: str, lang: str = "FR",
               max_items: int = 25, date_from=None, date_to=None):
    """Parse un flux RSS → liste de documents (filtrés par plage de dates)."""
    docs = []
    try:
        resp = requests.get(feed_url, headers=UA, timeout=12)
        parsed = feedparser.parse(resp.content)
        for entry in parsed.entries[:max_items]:
            title = clean_html(entry.get("title", ""))
            summary = clean_html(entry.get("summary", entry.get("description", "")))
            link = entry.get("link", "")
            try:
                pub_dt = datetime(*entry.published_parsed[:6])
            except Exception:
                try:
                    pub_dt = datetime(*entry.updated_parsed[:6])
                except Exception:
                    pub_dt = datetime.now()
            # Filtre par plage de dates
            if date_from and pub_dt.date() < date_from:
                continue
            if date_to and pub_dt.date() > date_to:
                continue
            if title and link:
                docs.append({
                    "domain": domain,
                    "title": title,
                    "url": link,
                    "content": f"{title}. {summary}"[:4000],
                    "source": source_name,
                    "published": pub_dt.isoformat(),
                    "lang": lang,
                })
    except Exception:
        pass
    return docs


def scrape_domains(domains: list, langs: list = None, date_from=None,
                   date_to=None, progress_cb=None):
    """Scrape les flux des domaines sélectionnés, filtrés par langue et dates."""
    langs = langs or LANGS
    all_docs = []
    tasks = [(d, s, u, lg) for d in domains
             for (s, u, lg) in FEEDS.get(d, []) if lg in langs]
    for i, (domain, sname, surl, lg) in enumerate(tasks):
        if progress_cb:
            progress_cb((i + 1) / max(len(tasks), 1), f"{domain} · {sname} [{lg}]")
        all_docs.extend(fetch_feed(sname, surl, domain, lg,
                                   date_from=date_from, date_to=date_to))
    return all_docs


def save_documents(docs: list):
    """Upsert dans Supabase (dédupliqué par URL). Retourne le nb inséré."""
    if not docs:
        return 0
    ep, hdr = _sb_docs()
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


def load_documents(domains: list = None, limit: int = 800, langs: list = None,
                   sources: list = None, date_from=None, date_to=None,
                   search: str = None):
    """Charge les documents depuis Supabase avec filtres avancés."""
    ep, hdr = _sb_docs()
    params = [("select", "*"), ("order", "published.desc"), ("limit", str(limit))]
    if domains:
        params.append(("domain", "in.(" + ",".join(f'"{d}"' for d in domains) + ")"))
    if langs:
        params.append(("lang", "in.(" + ",".join(f'"{l}"' for l in langs) + ")"))
    if sources:
        params.append(("source", "in.(" + ",".join(f'"{s}"' for s in sources) + ")"))
    if date_from:
        params.append(("published", f"gte.{date_from.isoformat()}"))
    if date_to:
        params.append(("published", f"lte.{date_to.isoformat()}T23:59:59"))
    if search and search.strip():
        params.append(("title", f"ilike.*{search.strip()}*"))
    try:
        r = requests.get(ep, headers=hdr, params=params, timeout=15)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def list_sources():
    """Liste distincte des sources présentes en base."""
    ep, hdr = _sb_docs()
    try:
        r = requests.get(ep, headers=hdr, timeout=10,
                         params=[("select", "source"), ("limit", "2000")])
        if r.status_code == 200:
            return sorted({row.get("source","") for row in r.json() if row.get("source")})
    except Exception:
        pass
    return []


def count_documents():
    ep, hdr = _sb_docs()
    try:
        r = requests.get(f"{ep}?select=id", headers={**hdr, "Prefer": "count=exact"},
                         timeout=10)
        cr = r.headers.get("content-range", "/0")
        return int(cr.split("/")[-1])
    except Exception:
        return 0


def delete_all_documents():
    ep, hdr = _sb_docs()
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

    _t = get_theme()
    n_docs = count_documents()
    st.markdown(
        f"<div style='background:{_t['card']};border:1px solid {_t['border']};border-radius:12px;"
        f"padding:14px 20px;margin-bottom:16px'>"
        f"<span style='color:{_t['muted']}'>Documents en base :</span> "
        f"<b style='color:{_t['accent']};font-size:20px;font-family:monospace'>{n_docs}</b></div>",
        unsafe_allow_html=True)

    sc1, sc2 = st.columns([2.4, 1.2])
    with sc1:
        domains = st.multiselect(
            "Domaines à scraper",
            list(FEEDS.keys()),
            default=list(FEEDS.keys()),
        )
    with sc2:
        langs_sel = st.multiselect("Langues", LANGS, default=LANGS,
                                   key="scrape_langs")

    dc1, dc2, dc3 = st.columns([1.2, 1.2, 2])
    from datetime import timedelta as _td
    with dc1:
        date_from = st.date_input("Publié à partir du",
                                  value=datetime.now().date() - _td(days=7),
                                  key="scrape_from")
    with dc2:
        date_to = st.date_input("Jusqu'au", value=datetime.now().date(),
                                key="scrape_to")
    with dc3:
        st.caption("Les flux RSS n'exposent que les articles récents (~25 derniers "
                   "par source). La plage de dates filtre parmi ces articles ; "
                   "les archives anciennes ne sont pas accessibles via RSS.")

    with st.expander("Sources par domaine"):
        for d in domains:
            st.markdown(f"**{d}**")
            for sname, surl, lg in FEEDS[d]:
                st.markdown(f"- `[{lg}]` {sname} — `{surl}`")

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Lancer la collecte", icon=":material/travel_explore:",
                     use_container_width=True, type="primary"):
            if not domains:
                st.warning("Sélectionnez au moins un domaine.")
            else:
                pbar = st.progress(0.0, text="Initialisation…")
                docs = scrape_domains(
                    domains, langs=langs_sel or LANGS,
                    date_from=date_from, date_to=date_to,
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
            dc = dom_color(doc.get("domain", ""))
            pub = str(doc.get("published", ""))[:16].replace("T", " ")
            _t2 = get_theme()
            st.markdown(
                f"<div style='background:{_t2['card']};border:1px solid {_t2['border']};"
                f"border-radius:10px;padding:10px 16px;margin-bottom:8px'>"
                f"<span style='color:{dc};font-size:11px;font-weight:700;"
                f"text-transform:uppercase'>{doc.get('domain','')}</span> "
                f"<span style='color:{_t2['muted']};font-size:11px'> · {doc.get('source','')} · {pub}</span><br>"
                f"<a href='{doc.get('url','')}' target='_blank' "
                f"style='color:{_t2['text']};text-decoration:none;font-weight:600'>"
                f"{doc.get('title','')}</a></div>",
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# RAG + CHATBOT
# ══════════════════════════════════════════════════════════════════════════════
MODELS = {
    "Claude Sonnet 4.6 (recommandé)": "claude-sonnet-4-6",
    "Claude Haiku 4.5 (rapide/éco)": "claude-haiku-4-5-20251001",
}

STOPWORDS_FR_EN = [
    # FR
    "le","la","les","de","des","du","un","une","et","en","dans","pour","par","sur",
    "avec","au","aux","ce","ces","cette","son","sa","ses","qui","que","quoi","dont",
    "il","elle","ils","elles","nous","vous","je","tu","ne","pas","plus","moins",
    "est","sont","être","avoir","fait","faire","comme","mais","ou","où","si","tout",
    "tous","toute","toutes","leur","leurs","a","à","d","l","s","n","c","y",
    # EN
    "the","a","an","of","in","on","for","to","and","or","is","are","was","were",
    "be","been","with","by","as","at","it","its","this","that","these","those",
    "from","has","have","had","will","would","can","could","not","but","their",
]


@st.cache_resource(show_spinner=False)
def _get_anthropic_client():
    import anthropic
    api_key = get_secret("ANTHROPIC_API_KEY")
    return anthropic.Anthropic(api_key=api_key) if api_key else None


def build_index(domains=None):
    """Construit (docs, vectorizer, matrix) et le met en cache session."""
    cache_key = "_rag_index"
    cached = st.session_state.get(cache_key)
    if cached and cached.get("domains") == (tuple(domains) if domains else None):
        return cached["docs"], cached["vec"], cached["mat"]

    docs = load_documents(domains=domains, limit=800)
    if not docs:
        return [], None, None

    corpus = [f"{d.get('title','')} {d.get('content','')}" for d in docs]
    vec = TfidfVectorizer(stop_words=STOPWORDS_FR_EN, max_features=8000,
                          ngram_range=(1, 2))
    mat = vec.fit_transform(corpus)

    st.session_state[cache_key] = {
        "docs": docs, "vec": vec, "mat": mat,
        "domains": tuple(domains) if domains else None,
    }
    return docs, vec, mat


def retrieve(query: str, domains=None, k: int = 6):
    """Top-k documents les plus pertinents pour la requête."""
    docs, vec, mat = build_index(domains)
    if not docs:
        return []
    try:
        qv = vec.transform([query])
        sims = cosine_similarity(qv, mat).flatten()
        top_idx = sims.argsort()[::-1][:k]
        return [
            {**docs[i], "score": float(sims[i])}
            for i in top_idx if sims[i] > 0.02
        ]
    except Exception:
        return []


def ask_claude(question: str, context_docs: list, model: str,
               history: list = None):
    """Appelle l'API Anthropic avec le contexte récupéré."""
    client = _get_anthropic_client()
    if client is None:
        return ("⚠️ Clé API Anthropic manquante. Ajoutez `ANTHROPIC_API_KEY` "
                "dans les secrets de l'application.")

    context_txt = "\n\n".join(
        f"[Document {i+1}] ({d.get('domain','')} · {d.get('source','')} · "
        f"{str(d.get('published',''))[:10]})\nTitre : {d.get('title','')}\n"
        f"Contenu : {d.get('content','')[:1200]}\nURL : {d.get('url','')}"
        for i, d in enumerate(context_docs)
    ) or "Aucun document pertinent trouvé dans la base."

    system_prompt = (
        "Tu es un analyste expert en finance, trading, économie et économétrie. "
        "Tu réponds en français de manière précise, structurée et pédagogique.\n\n"
        "Tu disposes de documents d'actualité récents collectés automatiquement. "
        "Appuie tes réponses sur ces documents quand ils sont pertinents, en citant "
        "la source entre crochets, ex. [FXStreet]. Si les documents ne couvrent pas "
        "la question, réponds avec tes connaissances générales en le précisant. "
        "Termine par une section « Sources » listant les documents utilisés avec "
        "leur URL.\n\n"
        f"=== DOCUMENTS DISPONIBLES ===\n{context_txt}"
    )

    messages = []
    if history:
        for h in history[-6:]:  # 3 derniers échanges
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": question})

    try:
        resp = client.messages.create(
            model=model,
            max_tokens=1500,
            system=system_prompt,
            messages=messages,
        )
        return "".join(b.text for b in resp.content if hasattr(b, "text"))
    except Exception as e:
        return f"⚠️ Erreur API Anthropic : {e}"


def chatbot_page():
    """Page Streamlit : chatbot RAG."""
    st.markdown("## Chatbot Analyste")
    st.caption("Posez vos questions — les réponses s'appuient sur les documents "
               "collectés (RAG) et l'API Claude d'Anthropic.")

    # Options
    oc1, oc2 = st.columns([2, 2])
    with oc1:
        domains_filter = st.multiselect(
            "Domaines de recherche",
            list(FEEDS.keys()),
            default=list(FEEDS.keys()),
            key="chat_domains")
    with oc2:
        model_label = st.selectbox("Modèle", list(MODELS.keys()), key="chat_model")
    model = MODELS[model_label]

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Historique
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Saisie
    question = st.chat_input("Ex : Quel est l'impact des taux de la Fed sur l'or ?")
    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Recherche documentaire + analyse…"):
                ctx = retrieve(question, domains=domains_filter or None, k=6)
                answer = ask_claude(question, ctx, model,
                                    history=st.session_state.chat_history[:-1])
            st.markdown(answer)
            if ctx:
                with st.expander(f"{len(ctx)} documents utilisés (RAG)"):
                    for d in ctx:
                        st.markdown(
                            f"- **[{d.get('source','')}]** "
                            f"[{d.get('title','')[:90]}]({d.get('url','')}) "
                            f"— score {d.get('score',0):.2f}")
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        # Mémoriser le dernier thème pour le nuage de mots
        st.session_state["last_theme"] = question

    if st.session_state.chat_history:
        if st.button("Effacer la conversation", icon=":material/delete:"):
            st.session_state.chat_history = []
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD — Vue analytique professionnelle
# ══════════════════════════════════════════════════════════════════════════════
def _dash_theme():
    t = get_theme()
    return t["card"], t["border"], t["muted"], t["text"], t["win"], t["loss"], t["alt"], t["orange"]


def _layout(height=280, showlegend=False, **kw):
    bg, grid, muted, *_ = _dash_theme()
    return dict(paper_bgcolor=bg, plot_bgcolor=bg,
                font=dict(color=muted, family="Inter, sans-serif", size=12),
                height=height, margin=dict(l=50, r=20, t=30, b=40),
                showlegend=showlegend, hovermode="x unified", **kw)


def _axes(fig, xprefix="", yprefix=""):
    _, grid, muted, *_ = _dash_theme()
    fig.update_xaxes(gridcolor=grid, linecolor=grid, tickcolor=grid,
                     tickprefix=xprefix, showline=True, zeroline=False)
    fig.update_yaxes(gridcolor=grid, linecolor=grid, tickcolor=grid,
                     tickprefix=yprefix, showline=True, zeroline=False)


def _kpi(icon, label, value, sub, color):
    bg, grid, muted, text, *_ = _dash_theme()
    st.markdown(
        f"<div class='rfh-kpi'>"
        f"<div class='rfh-kpi-icon' style='background:{color}1c;color:{color}'>{icon}</div>"
        f"<div style='min-width:0'>"
        f"<div style='font-size:10px;color:{muted};letter-spacing:1.3px;"
        f"text-transform:uppercase;font-weight:600'>{label}</div>"
        f"<div style='font-size:22px;font-weight:800;font-family:JetBrains Mono,monospace;"
        f"color:{text};margin:3px 0 2px;white-space:nowrap;overflow:hidden;"
        f"text-overflow:ellipsis'>{value}</div>"
        f"<div style='font-size:11px;color:{muted}'>{sub}</div>"
        f"</div></div>",
        unsafe_allow_html=True)


def _section_title(title, subtitle=""):
    _, _, muted, text, *_ = _dash_theme()
    accent = get_theme()["accent"]
    sub_html = f" <span style='font-size:12px;color:{muted};font-weight:400'>{subtitle}</span>" if subtitle else ""
    st.markdown(
        f"<div style='margin:10px 0 10px;display:flex;align-items:center;gap:9px'>"
        f"<span style='width:4px;height:17px;background:{accent};"
        f"border-radius:2px;display:inline-block'></span>"
        f"<span style='font-size:15px;font-weight:700;color:{text}'>{title}</span>"
        f"{sub_html}</div>", unsafe_allow_html=True)


def top_keywords(docs, n=15):
    words = []
    for d in docs:
        text = f"{d.get('title','')} {d.get('content','')}".lower()
        tokens = re.findall(r"[a-zàâäéèêëïîôöùûüç]{4,}", text)
        words.extend(t for t in tokens if t not in STOPWORDS_FR_EN)
    return Counter(words).most_common(n)


def dashboard_page():
    bg, grid, muted, text, win, loss, alt, orange = _dash_theme()

    st.markdown("## Dashboard des informations")
    st.caption("Vue analytique professionnelle de la base documentaire collectée — "
               "volume, sources, domaines, tendances et mots-clés.")

    # ── FILTRES ──────────────────────────────────────────────────────────────
    st.markdown(f"<div class='rfh-card' style='margin-bottom:18px'>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns([2.2, 1.4, 1.4])
    with f1:
        domains_sel = st.multiselect(
            "Filtrer par domaine", list(FEEDS.keys()),
            default=list(FEEDS.keys()), key="dash_domains")
    with f2:
        period = st.selectbox("Période", ["7 jours", "14 jours", "30 jours", "Tout"],
                              index=2, key="dash_period")
    with f3:
        search_kw = st.text_input("Recherche titre", placeholder="Ex : Fed, inflation…",
                                  key="dash_search")
    st.markdown("</div>", unsafe_allow_html=True)

    docs = load_documents(domains=domains_sel or None, limit=1500)
    if not docs:
        st.warning("Aucun document. Lancez d'abord une collecte (page **Collecte**).")
        return

    df = pd.DataFrame(docs)
    df["published"] = pd.to_datetime(df["published"], errors="coerce", utc=True)

    # Les documents sans date de publication exploitable ne peuvent être placés
    # sur aucun axe temporel : on les écarte des analyses (et on le signale).
    _n_invalid = int(df["published"].isna().sum())
    df = df[df["published"].notna()].copy()
    if df.empty:
        st.warning("Aucun document avec une date de publication valide. "
                   "Relancez une collecte.")
        return

    df["day"] = df["published"].dt.date
    df["hour"] = df["published"].dt.hour.astype(int)
    df["weekday"] = df["published"].dt.day_name()

    if period != "Tout":
        n_days = int(period.split()[0])
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=n_days)
        df = df[df["published"] >= cutoff]

    if search_kw.strip():
        mask = df["title"].str.contains(search_kw, case=False, na=False) | \
               df["content"].str.contains(search_kw, case=False, na=False)
        df = df[mask]

    if df.empty:
        st.info("Aucun document ne correspond à ces filtres.")
        return

    if _n_invalid:
        st.caption(f"{_n_invalid} document(s) sans date de publication valide "
                   f"écarté(s) des analyses temporelles.")

    # ── KPIs ────────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    _dmin, _dmax = df["day"].min(), df["day"].max()
    n_days_span = max((_dmax - _dmin).days, 1) if len(df) > 1 else 1
    avg_per_day = len(df) / n_days_span
    top_domain = df["domain"].value_counts().idxmax() if not df.empty else "—"
    top_source = df["source"].value_counts().idxmax() if not df.empty else "—"

    with k1: _kpi('<i class="fa-solid fa-file-lines"></i>', "Documents", str(len(df)),
                  "articles filtrés", win)
    with k2: _kpi('<i class="fa-solid fa-rss"></i>', "Sources", str(df["source"].nunique()),
                  "flux distincts", alt)
    with k3: _kpi('<i class="fa-solid fa-layer-group"></i>', "Domaines", str(df["domain"].nunique()),
                  "champs couverts", orange)
    with k4: _kpi('<i class="fa-solid fa-gauge-high"></i>', "Rythme", f"{avg_per_day:.1f}/j",
                  "articles par jour", alt)
    with k5:
        latest = df["published"].max()
        latest_txt = latest.strftime("%d/%m %H:%M") if pd.notna(latest) else "—"
        _kpi('<i class="fa-solid fa-clock"></i>', "Dernier article", latest_txt,
             "horodatage UTC", loss)
    st.markdown(" ")

    # Bandeau domaine/source dominants
    st.markdown(
        f"<div style='display:flex;gap:24px;padding:10px 16px;background:{bg};"
        f"border:1px solid {grid};border-radius:10px;margin-bottom:18px;font-size:13px'>"
        f"<span style='color:{muted}'>Domaine dominant : "
        f"<b style='color:{dom_color(top_domain)}'>{top_domain}</b></span>"
        f"<span style='color:{muted}'>Source la plus active : "
        f"<b style='color:{text}'>{top_source}</b></span>"
        f"</div>", unsafe_allow_html=True)

    # ── ROW 1 : Évolution temporelle + Répartition domaines ─────────────────
    _section_title("Évolution de la collecte", "Volume d'articles dans le temps")
    r1, r2 = st.columns([3, 2])

    with r1:
        by_day_dom = df.groupby(["day","domain"]).size().reset_index(name="n")
        fig1 = go.Figure()
        for dom in sorted(by_day_dom["domain"].unique()):
            sub = by_day_dom[by_day_dom["domain"]==dom].sort_values("day")
            fig1.add_trace(go.Bar(
                x=sub["day"].astype(str), y=sub["n"], name=dom,
                marker_color=dom_color(dom), marker_opacity=0.85,
                hovertemplate=f"<b>{dom}</b><br>%{{x}}: %{{y}} articles<extra></extra>"))
        fig1.update_layout(**_layout(height=300, showlegend=True, barmode="stack"),
                           legend=dict(orientation="h", y=-0.18, font=dict(color=muted, size=10)))
        _axes(fig1)
        st.plotly_chart(fig1, use_container_width=True)

    with r2:
        by_dom = df["domain"].value_counts()
        fig2 = go.Figure(go.Pie(
            values=by_dom.values.tolist(), labels=by_dom.index.tolist(), hole=0.62,
            marker=dict(colors=[dom_color(d) for d in by_dom.index],
                        line=dict(color=bg, width=3)),
            hovertemplate="<b>%{label}</b>: %{value} (%{percent})<extra></extra>", textinfo="none"))
        fig2.add_annotation(text=f"<b>{len(df)}</b>", x=0.5, y=0.56,
            font=dict(size=24,color=text,family="JetBrains Mono"), showarrow=False)
        fig2.add_annotation(text="articles", x=0.5, y=0.38,
            font=dict(size=11,color=muted), showarrow=False)
        fig2.update_layout(**_layout(height=300, showlegend=True),
                           legend=dict(orientation="h", y=-0.15, font=dict(color=muted, size=10)))
        st.plotly_chart(fig2, use_container_width=True)

    # ── ROW 2 : Heatmap activité + Classement sources ────────────────────────
    _section_title("Intensité de la collecte", "Répartition par domaine et par jour")
    r3, r4 = st.columns([3, 2])

    with r3:
        pivot = df.pivot_table(index="domain", columns="day", values="title",
                               aggfunc="count", fill_value=0)
        if not pivot.empty:
            def _hex2rgba(h, a=1.0):
                h = h.lstrip("#")
                r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
                return f"rgba({r},{g},{b},{a})"
            fig3 = go.Figure(go.Heatmap(
                z=pivot.values, x=[str(c) for c in pivot.columns], y=pivot.index.tolist(),
                colorscale=[[0,_hex2rgba(bg)],[0.5,_hex2rgba(alt,0.55)],[1,_hex2rgba(win)]],
                hovertemplate="<b>%{y} · %{x}</b><br>%{z} articles<extra></extra>",
                showscale=True,
                colorbar=dict(tickfont=dict(color=muted, size=10), bgcolor=bg,
                             bordercolor=grid, thickness=10)))
            fig3.update_layout(**_layout(height=max(240, len(pivot)*42)))
            fig3.update_xaxes(gridcolor=grid, linecolor=grid, tickangle=-30, tickfont=dict(size=9))
            fig3.update_yaxes(gridcolor=grid, linecolor=grid)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Pas assez de données pour la heatmap.")

    with r4:
        by_src = df["source"].value_counts().head(8).sort_values()
        fig4 = go.Figure(go.Bar(
            y=by_src.index.tolist(), x=by_src.values.tolist(), orientation="h",
            marker_color=chart_palette()[:len(by_src)], marker_opacity=0.85,
            text=by_src.values.tolist(), textposition="outside",
            textfont=dict(color=muted, size=11),
            hovertemplate="<b>%{y}</b>: %{x} articles<extra></extra>"))
        fig4.update_layout(**_layout(height=max(240, len(by_src) * 34)))
        _axes(fig4)
        st.plotly_chart(fig4, use_container_width=True)

    # ── ROW 3 : Mots-clés + Répartition horaire ──────────────────────────────
    _section_title("Signaux thématiques", "Mots-clés dominants et rythme de publication")
    r5, r6 = st.columns(2)

    with r5:
        kws = top_keywords(docs, n=12)
        if kws:
            kw_df = pd.DataFrame(kws, columns=["mot", "n"]).sort_values("n")
            fig5 = go.Figure(go.Bar(
                y=kw_df["mot"], x=kw_df["n"], orientation="h",
                marker_color=alt, marker_opacity=0.85,
                hovertemplate="<b>%{y}</b>: %{x} occurrences<extra></extra>"))
            fig5.update_layout(**_layout(height=max(260, len(kw_df) * 30)))
            _axes(fig5)
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("Pas assez de texte pour extraire des mots-clés.")

    with r6:
        by_hour = df.groupby("hour").size().reindex(range(24), fill_value=0)
        fig6 = go.Figure(go.Bar(
            x=[f"{int(h):02d}h" for h in by_hour.index], y=by_hour.values,
            marker_color=orange, marker_opacity=0.8,
            hovertemplate="<b>%{x}</b>: %{y} articles<extra></extra>"))
        fig6.update_layout(**_layout(height=max(260, len(kw_df)*30) if kws else 300))
        _axes(fig6)
        st.plotly_chart(fig6, use_container_width=True)

    # ── Derniers articles ─────────────────────────────────────────────────────
    # ── LECTURE & TÉLÉCHARGEMENT D'ARTICLES ──────────────────────────────────
    _section_title("Lecture d'articles",
                   "Extraire et télécharger le contenu complet — sans visiter le site")

    reader_pool = df.sort_values("published", ascending=False).head(60).reset_index(drop=True)
    opts = [f"{i+1:02d} · {r['title'][:85]} — {r['source']}"
            for i, r in reader_pool.iterrows()]
    rc1, rc2 = st.columns([4, 1.3])
    with rc1:
        sel_label = st.selectbox("Article à extraire", opts, key="reader_sel",
                                 label_visibility="collapsed")
    with rc2:
        do_extract = st.button("Extraire l'article", icon=":material/article:",
                               use_container_width=True, type="primary")

    sel_row = reader_pool.iloc[opts.index(sel_label)]

    if do_extract:
        with st.spinner("Extraction du contenu…"):
            full_txt = fetch_article_text(sel_row["url"])
        st.session_state["reader_text"]  = full_txt
        st.session_state["reader_title"] = sel_row["title"]

    if st.session_state.get("reader_title") == sel_row["title"]:
        full_txt = st.session_state.get("reader_text", "")
        pub_s = sel_row["published"].strftime("%d/%m/%Y %H:%M") if pd.notna(sel_row["published"]) else ""
        if full_txt:
            file_body = (f"{sel_row['title']}\n{sel_row['source']} · {pub_s}\n"
                         f"{sel_row['url']}\n\n{'='*70}\n\n{full_txt}")
            dl1, dl2, _ = st.columns([1.3, 1.3, 3])
            with dl1:
                st.download_button("Télécharger (.txt)", data=file_body,
                    file_name=re.sub(r"[^\w\-]+","_", sel_row["title"][:60]) + ".txt",
                    mime="text/plain", use_container_width=True,
                    icon=":material/download:")
            with dl2:
                st.download_button("Télécharger (.md)", data=f"# {sel_row['title']}\n\n"
                    f"*{sel_row['source']} · {pub_s}*  \n<{sel_row['url']}>\n\n{full_txt}",
                    file_name=re.sub(r"[^\w\-]+","_", sel_row["title"][:60]) + ".md",
                    mime="text/markdown", use_container_width=True,
                    icon=":material/download:")
            with st.expander("Lire l'article ici", expanded=True):
                st.markdown(full_txt[:12000] +
                            ("\n\n*…(tronqué — téléchargez pour le texte complet)*"
                             if len(full_txt) > 12000 else ""))
        else:
            st.warning("Extraction impossible (site protégé ou contenu dynamique). "
                       "Résumé disponible en base :")
            st.markdown(f"<div class='rfh-card'>{sel_row['content']}</div>",
                        unsafe_allow_html=True)
            st.download_button("Télécharger le résumé (.txt)",
                data=f"{sel_row['title']}\n{sel_row['url']}\n\n{sel_row['content']}",
                file_name=re.sub(r"[^\w\-]+","_", sel_row["title"][:60]) + ".txt",
                mime="text/plain", icon=":material/download:")

    st.markdown(" ")

    # ── DERNIERS ARTICLES + EXPORT GLOBAL ────────────────────────────────────
    hd1, hd2 = st.columns([4, 1.4])
    with hd1:
        _section_title("Derniers articles", f"{min(20,len(df))} plus récents")
    with hd2:
        exp_df = df[["domain","source","title","url","published","content"]].copy()
        exp_df["published"] = exp_df["published"].astype(str)
        st.download_button("Exporter tout (CSV)",
            data=exp_df.to_csv(index=False).encode("utf-8"),
            file_name="rag_finance_articles.csv", mime="text/csv",
            use_container_width=True, icon=":material/table_view:")

    show = df.sort_values("published", ascending=False).head(20)
    for _, r in show.iterrows():
        dc = dom_color(r["domain"])
        pub = r["published"].strftime("%d/%m %H:%M") if pd.notna(r["published"]) else ""
        st.markdown(
            f"<div style='background:{bg};border:1px solid {grid};"
            f"border-radius:10px;padding:9px 14px;margin-bottom:6px'>"
            f"<span style='color:{dc};font-size:11px;font-weight:700'>"
            f"{r['domain']}</span> "
            f"<span style='color:{muted};font-size:11px'>· {r['source']} · {pub}</span><br>"
            f"<a href='{r['url']}' target='_blank' style='color:{text};"
            f"text-decoration:none'>{r['title'][:120]}</a></div>",
            unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# BIBLIOTHÈQUE — Tous les éléments scrapés avec résumés
# ══════════════════════════════════════════════════════════════════════════════
def library_page():
    bg, grid, muted, text, win, loss, alt, orange = _dash_theme()
    t = get_theme()

    st.markdown("## Bibliothèque")
    st.caption("Tous les articles collectés — résumés, filtres avancés, lecture "
               "intégrale et téléchargement.")

    # ── FILTRES ──────────────────────────────────────────────────────────────
    with st.container():
        lf1, lf2, lf3 = st.columns([2, 1, 1])
        with lf1:
            lib_domains = st.multiselect("Domaines", list(FEEDS.keys()),
                                         default=[], key="lib_domains",
                                         placeholder="Tous les domaines")
        with lf2:
            lib_langs = st.multiselect("Langues", LANGS, default=[],
                                       key="lib_langs", placeholder="Toutes")
        with lf3:
            lib_search = st.text_input("Recherche titre", key="lib_search",
                                       placeholder="Ex : inflation…")

        lf4, lf5, lf6 = st.columns([1, 1, 2])
        from datetime import timedelta as _td2
        with lf4:
            lib_from = st.date_input("Du", value=None, key="lib_from")
        with lf5:
            lib_to = st.date_input("Au", value=None, key="lib_to")
        with lf6:
            all_sources = list_sources()
            lib_sources = st.multiselect("Sources", all_sources, default=[],
                                         key="lib_sources",
                                         placeholder="Toutes les sources")

    docs = load_documents(
        domains=lib_domains or None,
        langs=lib_langs or None,
        sources=lib_sources or None,
        date_from=lib_from, date_to=lib_to,
        search=lib_search, limit=1000)

    if not docs:
        st.info("Aucun article ne correspond à ces filtres. "
                "Lancez une collecte ou élargissez les critères.")
        return

    df = pd.DataFrame(docs)
    df["published"] = pd.to_datetime(df["published"], errors="coerce", utc=True)
    df = df.sort_values("published", ascending=False).reset_index(drop=True)

    # ── EN-TÊTE : compteur + export ──────────────────────────────────────────
    h1, h2 = st.columns([3, 1.3])
    with h1:
        st.markdown(
            f"<div style='padding:8px 0;font-size:14px;color:{muted}'>"
            f"<b style='color:{t['accent']};font-size:20px;font-family:JetBrains Mono,monospace'>"
            f"{len(df)}</b> articles trouvés</div>", unsafe_allow_html=True)
    with h2:
        exp = df[["domain","lang","source","title","url","published","content"]].copy()
        exp["published"] = exp["published"].astype(str)
        st.download_button("Exporter (CSV)", data=exp.to_csv(index=False).encode("utf-8"),
            file_name="bibliotheque_rag.csv", mime="text/csv",
            use_container_width=True, icon=":material/table_view:")

    # ── PAGINATION ───────────────────────────────────────────────────────────
    PAGE_SIZE = 15
    n_pages = max(1, (len(df) - 1) // PAGE_SIZE + 1)
    if "lib_page" not in st.session_state:
        st.session_state.lib_page = 1
    st.session_state.lib_page = min(st.session_state.lib_page, n_pages)

    pg1, pg2, pg3 = st.columns([1, 2, 1])
    with pg1:
        if st.button("← Précédent", disabled=st.session_state.lib_page <= 1,
                     use_container_width=True, key="lib_prev"):
            st.session_state.lib_page -= 1; st.rerun()
    with pg2:
        st.markdown(f"<div style='text-align:center;padding-top:8px;color:{muted}'>"
                    f"Page <b style='color:{text}'>{st.session_state.lib_page}</b> / {n_pages}</div>",
                    unsafe_allow_html=True)
    with pg3:
        if st.button("Suivant →", disabled=st.session_state.lib_page >= n_pages,
                     use_container_width=True, key="lib_next"):
            st.session_state.lib_page += 1; st.rerun()

    start_i = (st.session_state.lib_page - 1) * PAGE_SIZE
    page_df = df.iloc[start_i:start_i + PAGE_SIZE]

    # ── CARTES ARTICLES ──────────────────────────────────────────────────────
    for i, r in page_df.iterrows():
        dc = dom_color(r["domain"])
        pub = r["published"].strftime("%d/%m/%Y %H:%M") if pd.notna(r["published"]) else "—"
        lang_badge = r.get("lang", "?") or "?"
        summary = (r.get("content") or "")
        # Retirer le titre dupliqué au début du résumé
        if summary.startswith(r["title"]):
            summary = summary[len(r["title"]):].lstrip(". ")
        short = summary[:280] + ("…" if len(summary) > 280 else "")

        st.markdown(
            f"<div style='background:{bg};border:1px solid {grid};border-radius:12px;"
            f"padding:14px 18px;margin-bottom:4px'>"
            f"<span class='rfh-badge' style='background:{dc}22;color:{dc};"
            f"border:1px solid {dc}55'>{r['domain']}</span> "
            f"<span class='rfh-badge' style='background:{alt}22;color:{alt};"
            f"border:1px solid {alt}55'>{lang_badge}</span> "
            f"<span style='color:{muted};font-size:11px'> {r['source']} · {pub}</span>"
            f"<div style='margin-top:8px'><a href='{r['url']}' target='_blank' "
            f"style='color:{text};text-decoration:none;font-weight:700;font-size:15px'>"
            f"{r['title']}</a></div>"
            f"<div style='margin-top:6px;color:{muted};font-size:13px;line-height:1.5'>"
            f"{short}</div></div>",
            unsafe_allow_html=True)

        with st.expander("Résumé complet · Lecture intégrale · Téléchargement"):
            st.markdown(f"**Résumé (base documentaire) :**")
            st.markdown(summary if summary else "*Pas de résumé disponible.*")
            st.markdown("---")
            ext_key = f"lib_ext_{i}"
            if st.button("Extraire le texte intégral", key=f"btn_{ext_key}",
                         icon=":material/article:"):
                with st.spinner("Extraction…"):
                    st.session_state[ext_key] = fetch_article_text(r["url"])
            full = st.session_state.get(ext_key)
            if full is not None:
                if full:
                    st.markdown(full[:10000] +
                                ("\n\n*…(tronqué — téléchargez le fichier complet)*"
                                 if len(full) > 10000 else ""))
                    fname = re.sub(r"[^\w\-]+", "_", r["title"][:60])
                    st.download_button("Télécharger (.txt)",
                        data=f"{r['title']}\n{r['source']} · {pub}\n{r['url']}\n\n"
                             f"{'='*70}\n\n{full}",
                        file_name=fname + ".txt", mime="text/plain",
                        key=f"dl_{ext_key}", icon=":material/download:")
                else:
                    st.warning("Extraction impossible (site protégé). "
                               "Le résumé ci-dessus reste téléchargeable :")
                    fname = re.sub(r"[^\w\-]+", "_", r["title"][:60])
                    st.download_button("Télécharger le résumé (.txt)",
                        data=f"{r['title']}\n{r['url']}\n\n{summary}",
                        file_name=fname + ".txt", mime="text/plain",
                        key=f"dls_{ext_key}", icon=":material/download:")


# ══════════════════════════════════════════════════════════════════════════════
# NUAGE DE MOTS
# ══════════════════════════════════════════════════════════════════════════════
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

    _tw = get_theme()
    _wc_bg = "#ffffff" if _tw.get("light") else _tw["card"]
    _wc_cmap = "Dark2" if _tw.get("light") else "viridis"
    wc = WordCloud(
        width=1100, height=500,
        background_color=_wc_bg,
        colormap=_wc_cmap,
        max_words=max_words,
        prefer_horizontal=0.9,
        min_font_size=10,
    ).generate(" ".join(tokens))

    fig, ax = plt.subplots(figsize=(11, 5), facecolor=_wc_bg)
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
            "Domaines", list(FEEDS.keys()),
            default=list(FEEDS.keys()),
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
            _twc = get_theme()
            st.markdown(
                f"<div style='color:{_twc['muted']};font-size:13px;margin-bottom:8px'>"
                f"Basé sur <b style='color:{_twc['accent']}'>{n_docs}</b> documents "
                f"pertinents</div>", unsafe_allow_html=True)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
# CALENDRIER ÉCONOMIQUE
# ══════════════════════════════════════════════════════════════════════════════
CAL_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# Actif → devises dont les annonces l'impactent
ASSET_CURRENCIES = {
    "GOLD (XAU/USD)":   ["USD"],
    "EUR/USD":          ["EUR", "USD"],
    "GBP/USD":          ["GBP", "USD"],
    "USD/JPY":          ["USD", "JPY"],
    "USD/CHF":          ["USD", "CHF"],
    "AUD/USD":          ["AUD", "USD"],
    "USD/CAD":          ["USD", "CAD"],
    "BTC/USD":          ["USD"],
    "ETH/USD":          ["USD"],
    "NAS100":           ["USD"],
    "SP500":            ["USD"],
    "DOW30":            ["USD"],
    "DAX40":            ["EUR"],
    "CAC40":            ["EUR"],
    "FTSE100":          ["GBP"],
    "NIKKEI":           ["JPY"],
    "OIL (WTI/Brent)":  ["USD"],
    "SILVER (XAG/USD)": ["USD"],
}

def impact_style(impact):
    t = get_theme()
    table = {
        "High":    (t["loss"],   "Fort"),
        "Medium":  (t["orange"], "Moyen"),
        "Low":     (t["alt"],    "Faible"),
        "Holiday": (t["muted"],  "Férié"),
    }
    return table.get(impact, (t["muted"], "?"))


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_calendar():
    """Récupère le calendrier économique de la semaine (cache 30 min)."""
    try:
        r = requests.get(CAL_URL, timeout=12,
                         headers={"User-Agent": "Mozilla/5.0 RAGFinanceHub"})
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []


def calendar_page():
    st.markdown("## Annonces économiques")
    st.caption("Événements macro-économiques de la semaine susceptibles "
               "d'impacter vos actifs (source : ForexFactory).")

    assets = st.multiselect(
        "Vos actifs",
        list(ASSET_CURRENCIES.keys()),
        default=["GOLD (XAU/USD)", "EUR/USD", "BTC/USD"],
        key="cal_assets")

    impacts = st.multiselect(
        "Niveau d'impact",
        ["High", "Medium", "Low"],
        default=["High", "Medium"],
        format_func=lambda x: impact_style(x)[1],
        key="cal_impacts")

    events = fetch_calendar()
    if not events:
        st.error("Impossible de récupérer le calendrier économique. "
                 "Réessayez dans quelques minutes.")
        return

    # Devises pertinentes pour les actifs choisis
    currencies = set()
    for a in assets:
        currencies.update(ASSET_CURRENCIES.get(a, []))

    df = pd.DataFrame(events)
    if df.empty or "country" not in df.columns:
        st.warning("Format de calendrier inattendu.")
        return

    df["date_parsed"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    if currencies:
        df = df[df["country"].isin(currencies)]
    if impacts:
        df = df[df["impact"].isin(impacts)]
    df = df.sort_values("date_parsed")

    if df.empty:
        st.info("Aucune annonce ne correspond à vos filtres cette semaine.")
        return

    # KPIs rapides
    n_high = len(df[df["impact"] == "High"])
    _tc = get_theme()
    def _cal_kpi(label, value, color):
        st.markdown(
            f"<div style='background:{_tc['card']};border:1px solid {_tc['border']};"
            f"border-radius:12px;padding:14px 18px'>"
            f"<span style='color:{_tc['muted']};font-size:11px;text-transform:uppercase'>"
            f"{label}</span><br>"
            f"<b style='font-size:22px;color:{color};font-family:monospace'>"
            f"{value}</b></div>", unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    with k1: _cal_kpi("Annonces filtrées", str(len(df)), _tc["accent"])
    with k2: _cal_kpi("Impact fort", str(n_high), _tc["loss"])
    with k3: _cal_kpi("Devises suivies", ", ".join(sorted(currencies)) or "—", _tc["alt"])
    st.markdown(" ")

    # Liste des événements groupés par jour
    df["day_label"] = df["date_parsed"].dt.strftime("%A %d %B")
    jours_fr = {"Monday": "Lundi", "Tuesday": "Mardi", "Wednesday": "Mercredi",
                "Thursday": "Jeudi", "Friday": "Vendredi",
                "Saturday": "Samedi", "Sunday": "Dimanche"}
    now = pd.Timestamp.now(tz="UTC")

    for day, grp in df.groupby("day_label", sort=False):
        day_fr = day
        for en, fr in jours_fr.items():
            day_fr = day_fr.replace(en, fr)
        st.markdown(f"##### {day_fr}")
        for _, ev in grp.iterrows():
            color, impact_fr = impact_style(ev.get("impact", ""))
            t = ev["date_parsed"]
            heure = t.strftime("%H:%M") if pd.notna(t) else "--:--"
            past = pd.notna(t) and t < now
            opacity = "0.45" if past else "1"
            forecast = ev.get("forecast", "") or "—"
            previous = ev.get("previous", "") or "—"
            st.markdown(
                f"<div style='background:{_tc['card']};border:1px solid {_tc['border']};"
                f"border-left:3px solid {color};border-radius:10px;"
                f"padding:10px 16px;margin-bottom:6px;opacity:{opacity};"
                f"display:flex;gap:18px;align-items:center;flex-wrap:wrap'>"
                f"<span style='color:{_tc['muted']};font-family:monospace;min-width:48px'>"
                f"{heure}</span>"
                f"<span style='background:{color}22;color:{color};padding:2px 10px;"
                f"border-radius:12px;font-size:11px;font-weight:700'>"
                f"{ev.get('country','')}</span>"
                f"<span style='color:{_tc['text']};font-weight:600;flex:1'>"
                f"{ev.get('title','')}</span>"
                f"<span style='color:{color};font-size:11px;font-weight:700'>"
                f"{impact_fr}</span>"
                f"<span style='color:{_tc['muted']};font-size:11px'>"
                f"Prév : {forecast} · Préc : {previous}</span>"
                f"</div>", unsafe_allow_html=True)

    st.caption("Heures UTC. Les annonces passées sont estompées. "
               "Données actualisées toutes les 30 minutes.")


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

# ── Porte d'authentification ──────────────────────────────────────────────────
if "theme_name" not in st.session_state:
    st.session_state.theme_name = "Executive"

st.markdown(build_css(get_theme()), unsafe_allow_html=True)

if not login_gate():
    st.stop()

# ── Navigation ────────────────────────────────────────────────────────────────
if "nav" not in st.session_state:
    st.session_state.nav = "chat"

PAGES = [
    ("chat",      "Chatbot",     ":material/forum:"),
    ("scrape",    "Collecte",    ":material/travel_explore:"),
    ("library",   "Bibliothèque", ":material/local_library:"),
    ("dash",      "Dashboard",   ":material/monitoring:"),
    ("cloud",     "Nuages",       ":material/cloud:"),
    ("calendar",  "Annonces",     ":material/event:"),
]

# ── EN-TÊTE HORIZONTAL ─────────────────────────────────────────────────────────
_th = get_theme()
n_docs_head = count_documents()

hc1, hc2, hc3, hc4 = st.columns([2.6, 1.5, 1.9, 1.1])
with hc1:
    st.markdown(
        f"<div style='font-size:22px;font-weight:800;color:{_th['text']};"
        f"padding-top:4px'>RAG Finance Hub</div>", unsafe_allow_html=True)
with hc2:
    _sel_theme = st.selectbox(
        "Thème", THEME_NAMES,
        index=THEME_NAMES.index(st.session_state.theme_name)
              if st.session_state.theme_name in THEME_NAMES else 0,
        key="theme_selector", label_visibility="collapsed")
    if _sel_theme != st.session_state.theme_name:
        st.session_state.theme_name = _sel_theme
        st.rerun()
with hc3:
    st.markdown(
        f"<div style='display:flex;gap:10px;align-items:center;padding-top:6px;"
        f"justify-content:flex-end'>"
        f"<span style='background:{_th['accent']}18;border:1px solid {_th['accent']}44;"
        f"border-radius:8px;padding:5px 12px;font-size:12px;color:{_th['accent']};"
        f"font-weight:700'>📚 {n_docs_head} docs</span>"
        f"<span style='color:{_th['muted']};font-size:12px'>"
        f"{st.session_state.auth_user} · {st.session_state.auth_role}</span>"
        f"</div>", unsafe_allow_html=True)
with hc4:
    if st.button("Déconnexion", icon=":material/logout:", use_container_width=True,
                 key="btn_logout"):
        logout()

# ── NAVIGATION HORIZONTALE ─────────────────────────────────────────────────────
_nav_items = list(PAGES)
if st.session_state.auth_role == "admin":
    _nav_items.append(("admin", "Utilisateurs", ":material/manage_accounts:"))

_nav_cols = st.columns(len(_nav_items))
for _col, (key, label, icon) in zip(_nav_cols, _nav_items):
    with _col:
        if st.button(label, icon=icon, use_container_width=True,
                     type="primary" if st.session_state.nav == key else "secondary",
                     key=f"nav_{key}"):
            st.session_state.nav = key
            st.rerun()

st.markdown(f"<hr style='margin:4px 0 20px;border-color:{_th['border']}'>",
            unsafe_allow_html=True)

# ── Routage ───────────────────────────────────────────────────────────────────
nav = st.session_state.nav
if nav == "chat":
    chatbot_page()
elif nav == "scrape":
    scraper_page()
elif nav == "library":
    library_page()
elif nav == "dash":
    dashboard_page()
elif nav == "cloud":
    wordcloud_page()
elif nav == "calendar":
    calendar_page()
elif nav == "admin":
    admin_panel()
