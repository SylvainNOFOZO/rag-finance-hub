# ══════════════════════════════════════════════════════════════════════════════
# RAG — Retrieval-Augmented Generation
# Index TF-IDF sur les documents scrapés + chatbot Claude (API Anthropic)
# ══════════════════════════════════════════════════════════════════════════════
import streamlit as st
import os

from modules.config import get_secret
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from modules.scraper import load_documents

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
            ["Finance", "Trading", "Économie", "Économétrie"],
            default=["Finance", "Trading", "Économie", "Économétrie"],
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
