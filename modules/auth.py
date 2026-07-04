# ══════════════════════════════════════════════════════════════════════════════
# AUTH — Authentification sécurisée gérée par l'admin
# Les utilisateurs sont créés UNIQUEMENT par l'admin (pas d'auto-inscription)
# Stockage : table Supabase rag_users (username, password_hash, role, active)
# ══════════════════════════════════════════════════════════════════════════════
import streamlit as st
import requests
import hashlib
import os
import secrets as pysecrets

from modules.config import get_secret


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
    try:
        r = requests.get(f"{ep}?username=eq.{username}&select=*", headers=hdr, timeout=8)
        if r.status_code != 200:
            return False, None, f"Erreur serveur ({r.status_code})"
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
        "<p style='color:#8892a4'>Intelligence financière · Trading · Économie · Économétrie</p>"
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
        status_col = "#00d4aa" if u["active"] else "#ff4d6d"
        with uc1:
            role_badge = "👑" if u["role"] == "admin" else ""
            st.markdown(
                f"<div style='padding-top:8px'><b>{u['username']}</b> {role_badge} "
                f"<span style='color:{status_col};font-size:12px'>"
                f"{'● actif' if u['active'] else '● désactivé'}</span></div>",
                unsafe_allow_html=True)
        with uc2:
            st.markdown(f"<div style='padding-top:8px;color:#8892a4;font-size:12px'>"
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
