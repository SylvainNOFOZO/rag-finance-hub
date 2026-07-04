# ══════════════════════════════════════════════════════════════════════════════
# CONFIG — Lecture des secrets compatible Hugging Face (variables d'env)
# et local (.streamlit/secrets.toml)
# ══════════════════════════════════════════════════════════════════════════════
import os


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
