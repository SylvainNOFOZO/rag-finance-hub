# ══════════════════════════════════════════════════════════════════════════════
# ANNONCES ÉCONOMIQUES — Calendrier des événements impactant les actifs choisis
# Source : flux JSON public ForexFactory (faireconomy.media)
# ══════════════════════════════════════════════════════════════════════════════
import streamlit as st
import requests
import pandas as pd
from datetime import datetime

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

IMPACT_STYLE = {
    "High":   ("#ff4d6d", "Fort"),
    "Medium": ("#ff9f43", "Moyen"),
    "Low":    ("#54a0ff", "Faible"),
    "Holiday": ("#6b7894", "Férié"),
}


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
        format_func=lambda x: IMPACT_STYLE[x][1],
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
    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(
            f"<div style='background:#111520;border:1px solid #1e2535;"
            f"border-radius:12px;padding:14px 18px'>"
            f"<span style='color:#6b7894;font-size:11px;text-transform:uppercase'>"
            f"Annonces filtrées</span><br>"
            f"<b style='font-size:22px;color:#00d4aa;font-family:monospace'>"
            f"{len(df)}</b></div>", unsafe_allow_html=True)
    with k2:
        st.markdown(
            f"<div style='background:#111520;border:1px solid #1e2535;"
            f"border-radius:12px;padding:14px 18px'>"
            f"<span style='color:#6b7894;font-size:11px;text-transform:uppercase'>"
            f"Impact fort</span><br>"
            f"<b style='font-size:22px;color:#ff4d6d;font-family:monospace'>"
            f"{n_high}</b></div>", unsafe_allow_html=True)
    with k3:
        st.markdown(
            f"<div style='background:#111520;border:1px solid #1e2535;"
            f"border-radius:12px;padding:14px 18px'>"
            f"<span style='color:#6b7894;font-size:11px;text-transform:uppercase'>"
            f"Devises suivies</span><br>"
            f"<b style='font-size:22px;color:#7c6aff;font-family:monospace'>"
            f"{', '.join(sorted(currencies)) or '—'}</b></div>",
            unsafe_allow_html=True)
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
            color, impact_fr = IMPACT_STYLE.get(ev.get("impact", ""), ("#6b7894", "?"))
            t = ev["date_parsed"]
            heure = t.strftime("%H:%M") if pd.notna(t) else "--:--"
            past = pd.notna(t) and t < now
            opacity = "0.45" if past else "1"
            forecast = ev.get("forecast", "") or "—"
            previous = ev.get("previous", "") or "—"
            st.markdown(
                f"<div style='background:#111520;border:1px solid #1e2535;"
                f"border-left:3px solid {color};border-radius:10px;"
                f"padding:10px 16px;margin-bottom:6px;opacity:{opacity};"
                f"display:flex;gap:18px;align-items:center;flex-wrap:wrap'>"
                f"<span style='color:#8892a4;font-family:monospace;min-width:48px'>"
                f"{heure}</span>"
                f"<span style='background:{color}22;color:{color};padding:2px 10px;"
                f"border-radius:12px;font-size:11px;font-weight:700'>"
                f"{ev.get('country','')}</span>"
                f"<span style='color:#e8ecf4;font-weight:600;flex:1'>"
                f"{ev.get('title','')}</span>"
                f"<span style='color:{color};font-size:11px;font-weight:700'>"
                f"{impact_fr}</span>"
                f"<span style='color:#6b7894;font-size:11px'>"
                f"Prév : {forecast} · Préc : {previous}</span>"
                f"</div>", unsafe_allow_html=True)

    st.caption("Heures UTC. Les annonces passées sont estompées. "
               "Données actualisées toutes les 30 minutes.")
