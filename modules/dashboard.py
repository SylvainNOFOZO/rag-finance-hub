# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD — Analyses visuelles sur les informations collectées
# ══════════════════════════════════════════════════════════════════════════════
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from collections import Counter
import re

from modules.scraper import load_documents
from modules.rag import STOPWORDS_FR_EN

_BG, _GRID, _TEXT = "#111520", "#1e2535", "#8892a4"
_COLORS = ["#00d4aa", "#7c6aff", "#ff9f43", "#54a0ff", "#ff4d6d",
           "#00cec9", "#fdcb6e", "#5f27cd"]
DOM_COLORS = {"Finance": "#00d4aa", "Trading": "#7c6aff",
              "Économie": "#ff9f43", "Économétrie": "#54a0ff"}


def _layout(height=280, showlegend=False, **kw):
    return dict(paper_bgcolor=_BG, plot_bgcolor=_BG,
                font=dict(color=_TEXT, size=12), height=height,
                margin=dict(l=50, r=20, t=30, b=40),
                showlegend=showlegend, **kw)


def _axes(fig):
    fig.update_xaxes(gridcolor=_GRID, linecolor=_GRID)
    fig.update_yaxes(gridcolor=_GRID, linecolor=_GRID)


def _kpi(label, value, sub, color):
    st.markdown(
        f"<div style='background:{_BG};border:1px solid {_GRID};border-radius:14px;"
        f"padding:16px 18px;min-height:96px'>"
        f"<div style='font-size:10px;color:#6b7894;letter-spacing:1.5px;"
        f"text-transform:uppercase;font-weight:600'>{label}</div>"
        f"<div style='font-size:24px;font-weight:800;font-family:monospace;"
        f"color:{color};margin:4px 0'>{value}</div>"
        f"<div style='font-size:11px;color:#6b7894'>{sub}</div></div>",
        unsafe_allow_html=True)


def top_keywords(docs, n=15):
    words = []
    for d in docs:
        text = f"{d.get('title','')} {d.get('content','')}".lower()
        tokens = re.findall(r"[a-zàâäéèêëïîôöùûüç]{4,}", text)
        words.extend(t for t in tokens if t not in STOPWORDS_FR_EN)
    return Counter(words).most_common(n)


def dashboard_page():
    st.markdown("## Dashboard des informations")
    st.caption("Vue analytique de la base documentaire collectée.")

    domains_sel = st.multiselect(
        "Filtrer par domaine",
        list(DOM_COLORS.keys()), default=list(DOM_COLORS.keys()),
        key="dash_domains")

    docs = load_documents(domains=domains_sel or None, limit=800)
    if not docs:
        st.warning("Aucun document. Lancez d'abord une collecte "
                   "(page **Collecte**).")
        return

    df = pd.DataFrame(docs)
    df["published"] = pd.to_datetime(df["published"], errors="coerce", utc=True)
    df["day"] = df["published"].dt.date

    # ── KPIs ────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    with k1: _kpi("Documents", str(len(df)), "articles en base", "#00d4aa")
    with k2: _kpi("Sources", str(df["source"].nunique()), "flux distincts", "#7c6aff")
    with k3: _kpi("Domaines", str(df["domain"].nunique()), "champs couverts", "#ff9f43")
    with k4:
        latest = df["published"].max()
        latest_txt = latest.strftime("%d/%m %H:%M") if pd.notna(latest) else "—"
        _kpi("Dernier article", latest_txt, "date de publication", "#54a0ff")
    st.markdown(" ")

    # ── ROW 1 : volume par jour + répartition domaines ──────────────────────
    r1, r2 = st.columns([3, 2])
    with r1:
        st.markdown("#### Volume d'articles par jour")
        by_day = df.groupby("day").size().reset_index(name="n").dropna()
        fig1 = go.Figure(go.Bar(
            x=by_day["day"].astype(str), y=by_day["n"],
            marker_color="#00d4aa", marker_opacity=0.8,
            hovertemplate="<b>%{x}</b><br>%{y} articles<extra></extra>"))
        fig1.update_layout(**_layout(height=260))
        _axes(fig1)
        st.plotly_chart(fig1, use_container_width=True)

    with r2:
        st.markdown("#### Répartition par domaine")
        by_dom = df["domain"].value_counts()
        fig2 = go.Figure(go.Pie(
            values=by_dom.values.tolist(), labels=by_dom.index.tolist(),
            hole=0.6,
            marker=dict(colors=[DOM_COLORS.get(d, "#8892a4") for d in by_dom.index],
                        line=dict(color=_BG, width=3)),
            hovertemplate="<b>%{label}</b>: %{value} (%{percent})<extra></extra>"))
        fig2.update_layout(**_layout(height=260, showlegend=True),
                           legend=dict(orientation="h", y=-0.1,
                                       font=dict(color=_TEXT)))
        st.plotly_chart(fig2, use_container_width=True)

    # ── ROW 2 : sources + mots-clés ─────────────────────────────────────────
    r3, r4 = st.columns(2)
    with r3:
        st.markdown("#### Articles par source")
        by_src = df["source"].value_counts().head(10).sort_values()
        fig3 = go.Figure(go.Bar(
            y=by_src.index.tolist(), x=by_src.values.tolist(),
            orientation="h",
            marker_color=_COLORS[:len(by_src)], marker_opacity=0.85,
            hovertemplate="<b>%{y}</b>: %{x} articles<extra></extra>"))
        fig3.update_layout(**_layout(height=max(260, len(by_src) * 36)))
        _axes(fig3)
        st.plotly_chart(fig3, use_container_width=True)

    with r4:
        st.markdown("#### Mots-clés dominants")
        kws = top_keywords(docs, n=12)
        if kws:
            kw_df = pd.DataFrame(kws, columns=["mot", "n"]).sort_values("n")
            fig4 = go.Figure(go.Bar(
                y=kw_df["mot"], x=kw_df["n"], orientation="h",
                marker_color="#7c6aff", marker_opacity=0.85,
                hovertemplate="<b>%{y}</b>: %{x} occurrences<extra></extra>"))
            fig4.update_layout(**_layout(height=max(260, len(kw_df) * 32)))
            _axes(fig4)
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Pas assez de texte pour extraire des mots-clés.")

    # ── Tableau des derniers articles ───────────────────────────────────────
    st.markdown("#### Derniers articles")
    show = df.sort_values("published", ascending=False).head(20)
    for _, r in show.iterrows():
        dc = DOM_COLORS.get(r["domain"], "#8892a4")
        pub = r["published"].strftime("%d/%m %H:%M") if pd.notna(r["published"]) else ""
        st.markdown(
            f"<div style='background:{_BG};border:1px solid {_GRID};"
            f"border-radius:10px;padding:9px 14px;margin-bottom:6px'>"
            f"<span style='color:{dc};font-size:11px;font-weight:700'>"
            f"{r['domain']}</span> "
            f"<span style='color:#6b7894;font-size:11px'>· {r['source']} · {pub}</span><br>"
            f"<a href='{r['url']}' target='_blank' style='color:#e8ecf4;"
            f"text-decoration:none'>{r['title'][:120]}</a></div>",
            unsafe_allow_html=True)
