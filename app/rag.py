import json
import os
from pathlib import Path

import chromadb
from openai import OpenAI


_collection = None
_client = None
_faq_data = []
_mode = "openai"  # or "groq"


def _get_openai_client() -> OpenAI:
    """Return an OpenAI client configured for the available API key."""
    if _mode == "groq":
        return OpenAI(
            api_key=os.environ["GROQ_API_KEY"],
            base_url="https://api.groq.com/openai/v1",
        )
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def _get_chat_model() -> str:
    return "llama-3.1-8b-instant" if _mode == "groq" else "gpt-4o-mini"


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts using OpenAI embeddings (only in openai mode)."""
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.embeddings.create(
        input=texts,
        model="text-embedding-3-small",
    )
    return [item.embedding for item in response.data]


def init_rag() -> None:
    """Load FAQ data into ChromaDB with embeddings."""
    global _collection, _client, _faq_data, _mode

    # Determine mode based on available API keys
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")

    if openai_key:
        _mode = "openai"
    elif groq_key:
        _mode = "groq"
    else:
        _mode = "local"
        print("INFO: No OPENAI_API_KEY or GROQ_API_KEY set – using local fallback mode")

    # Load FAQ data
    faq_path = Path(__file__).parent / "data" / "faq.json"
    with open(faq_path) as f:
        _faq_data = json.load(f)

    # Initialize ChromaDB
    chroma_path = Path(__file__).parent.parent / "chroma_data"
    _client = chromadb.PersistentClient(path=str(chroma_path))

    # Delete existing collection to refresh data on restart
    try:
        _client.delete_collection("faq")
    except Exception:
        pass

    if _mode == "openai":
        # Use OpenAI embeddings
        documents = [
            f"Q: {item['question']}\nA: {item['answer']}" for item in _faq_data
        ]
        ids = [item["id"] for item in _faq_data]
        metadatas = [
            {"category": item["category"], "question": item["question"]}
            for item in _faq_data
        ]
        embeddings = _embed_texts(documents)

        _collection = _client.create_collection(
            name="faq",
            metadata={"hnsw:space": "cosine"},
        )
        _collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
    else:
        # Groq or local mode: use ChromaDB's default embedding function
        _collection = _client.create_collection(
            name="faq",
            metadata={"hnsw:space": "cosine"},
        )
        documents = [
            f"Q: {item['question']}\nA: {item['answer']}" for item in _faq_data
        ]
        ids = [item["id"] for item in _faq_data]
        metadatas = [
            {"category": item["category"], "question": item["question"]}
            for item in _faq_data
        ]
        _collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        if _mode == "local":
            print(f"INFO: Local mode - loaded {len(_faq_data)} FAQ entries with default embeddings")


def query(question: str) -> dict:
    """Query the RAG pipeline: embed question, retrieve context, generate answer."""
    if _collection is None:
        raise RuntimeError("RAG not initialized. Call init_rag() first.")

    # Retrieve top 3 similar documents
    if _mode == "openai":
        question_embedding = _embed_texts([question])[0]
        results = _collection.query(
            query_embeddings=[question_embedding],
            n_results=3,
        )
    else:
        results = _collection.query(
            query_texts=[question],
            n_results=3,
        )

    # Build context from results
    documents = results["documents"][0] if results["documents"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []

    # Local mode: return FAQ answer directly without LLM
    if _mode == "local":
        if documents:
            top_doc = documents[0]
            answer_part = top_doc.split("\nA: ", 1)[-1] if "\nA: " in top_doc else top_doc
            answer = f"{answer_part}\n\n(Using local keyword matching - for better results, configure an API key)"
        else:
            answer = "I couldn't find a relevant answer. Please try rephrasing your question."

        sources = [
            {"question": meta["question"], "category": meta["category"]}
            for meta in metadatas
        ]
        return {"answer": answer, "sources": sources}

    context = "\n\n".join(documents)

    # Generate answer using LLM
    client = _get_openai_client()
    response = client.chat.completions.create(
        model=_get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful customer support assistant. "
                    "Answer the user's question based on the following context from our FAQ. "
                    "If the context doesn't contain relevant information, say so politely. "
                    "Keep answers concise and helpful.\n\n"
                    f"Context:\n{context}"
                ),
            },
            {"role": "user", "content": question},
        ],
        temperature=0.3,
        max_tokens=500,
    )

    answer = response.choices[0].message.content

    # Build sources list
    sources = [
        {"question": meta["question"], "category": meta["category"]}
        for meta in metadatas
    ]

    return {"answer": answer, "sources": sources}
