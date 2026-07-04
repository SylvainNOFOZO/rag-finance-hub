-- ══════════════════════════════════════════════════════════════════════════
-- RAG FINANCE HUB — Setup Supabase
-- À exécuter dans : https://supabase.com/dashboard/project/VOTRE_PROJET/sql/new
-- ══════════════════════════════════════════════════════════════════════════

-- 1. Utilisateurs (gérés par l'admin uniquement)
CREATE TABLE IF NOT EXISTS rag_users (
    username      TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role          TEXT DEFAULT 'user',
    active        BOOLEAN DEFAULT true,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE rag_users ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS allow_all_users ON rag_users;
CREATE POLICY allow_all_users ON rag_users FOR ALL USING (true) WITH CHECK (true);

-- 2. Documents collectés par le scraper
CREATE TABLE IF NOT EXISTS rag_documents (
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
DROP POLICY IF EXISTS allow_all_docs ON rag_documents;
CREATE POLICY allow_all_docs ON rag_documents FOR ALL USING (true) WITH CHECK (true);

-- Index pour accélérer les requêtes
CREATE INDEX IF NOT EXISTS idx_rag_docs_domain    ON rag_documents(domain);
CREATE INDEX IF NOT EXISTS idx_rag_docs_published ON rag_documents(published DESC);
