---
title: RAG Finance Hub
emoji: 📊
colorFrom: green
colorTo: indigo
sdk: streamlit
sdk_version: "1.39.0"
app_file: app.py
pinned: false
---

# RAG Finance Hub

Application RAG (Retrieval-Augmented Generation) spécialisée **Finance · Trading · Économie · Économétrie**.

## Fonctionnalités

| Module | Description |
|--------|-------------|
| 🔍 **Collecte** | Scraping automatique de flux RSS spécialisés (Yahoo Finance, FXStreet, Le Monde Éco, arXiv…) |
| 💬 **Chatbot** | Assistant analyste propulsé par l'API Claude (Anthropic) avec récupération contextuelle sur les documents collectés |
| 📊 **Dashboard** | Analyses visuelles de la base documentaire : volume, sources, domaines, mots-clés |
| ☁️ **Nuage de mots** | Visualisation de ce qui se dit autour d'un thème donné |
| 📅 **Annonces éco** | Calendrier économique de la semaine filtré selon vos actifs (or, forex, indices, crypto) |
| 🔐 **Admin** | Authentification sécurisée — seul l'admin crée les comptes et distribue les mots de passe |

## Configuration

### 1. Base Supabase

Exécuter dans le SQL Editor de votre projet Supabase :

```sql
-- Utilisateurs (gérés par l'admin uniquement)
CREATE TABLE rag_users (
    username      TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role          TEXT DEFAULT 'user',
    active        BOOLEAN DEFAULT true,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE rag_users ENABLE ROW LEVEL SECURITY;
CREATE POLICY allow_all_users ON rag_users FOR ALL USING (true) WITH CHECK (true);

-- Documents collectés
CREATE TABLE rag_documents (
    id         BIGSERIAL PRIMARY KEY,
    domain     TEXT,
    title      TEXT,
    url        TEXT UNIQUE,
    content    TEXT,
    source     TEXT,
    published  TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE rag_documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY allow_all_docs ON rag_documents FOR ALL USING (true) WITH CHECK (true);
```

### 2. Secrets

Dans **Hugging Face Space → Settings → Variables and secrets** (ou `.streamlit/secrets.toml` en local) :

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
SUPABASE_URL      = "https://xxxx.supabase.co"
SUPABASE_KEY      = "eyJhbGciOi..."
ADMIN_USERNAME    = "admin"
ADMIN_PASSWORD    = "votre-mot-de-passe-admin"
```

Le compte admin est créé automatiquement au premier lancement si la table est vide.

### 3. Lancement local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Sécurité

- Mots de passe hashés en **PBKDF2-HMAC-SHA256** (100 000 itérations, sel aléatoire)
- Aucune auto-inscription : seul l'admin crée, désactive, supprime les comptes et réinitialise les mots de passe
- Comptes désactivables sans suppression

## Architecture

```
rag-finance-hub/
├── app.py                    # Entrée : auth + navigation
├── modules/
│   ├── auth.py               # Authentification & panneau admin
│   ├── scraper.py            # Collecte RSS multi-domaines
│   ├── rag.py                # Index TF-IDF + chatbot Claude
│   ├── dashboard.py          # Analyses Plotly
│   ├── wordcloud_gen.py      # Nuages de mots
│   └── calendar_eco.py       # Calendrier économique
├── requirements.txt
└── README.md
```
