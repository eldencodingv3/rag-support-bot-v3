# RAG Customer Support Bot

A customer support chatbot powered by Retrieval-Augmented Generation (RAG). It uses ChromaDB for vector storage and OpenAI (or Groq) for embeddings and response generation, with a clean chat UI served by FastAPI.

## How It Works

1. On startup, the FAQ dataset is loaded into ChromaDB as vector embeddings.
2. When a user asks a question, the system finds the 3 most relevant FAQ entries using semantic search.
3. The matched entries are sent as context to the LLM, which generates a natural-language answer.

## Setup

### Prerequisites

- Python 3.11+
- An OpenAI API key **or** a Groq API key

### Installation

```bash
git clone https://github.com/eldencodingv3/rag-support-bot-v3.git
cd rag-support-bot-v3
pip install -r requirements.txt
```

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes* | — | OpenAI API key for embeddings and chat |
| `GROQ_API_KEY` | Fallback* | — | Groq API key (used if OPENAI_API_KEY is not set) |
| `PORT` | No | `8000` | Port for the server |

*One of `OPENAI_API_KEY` or `GROQ_API_KEY` must be set. If only `GROQ_API_KEY` is provided, the app uses Groq's OpenAI-compatible endpoint with `llama-3.1-8b-instant` and ChromaDB's default embeddings.

### Run

```bash
export OPENAI_API_KEY=sk-...
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000 in your browser.

### Docker

```bash
docker build -t rag-support-bot .
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... rag-support-bot
```

## API Endpoints

### `GET /api/health`

Health check endpoint.

**Response:**
```json
{"status": "ok"}
```

### `POST /api/chat`

Send a question to the support bot.

**Request:**
```json
{"question": "How do I reset my password?"}
```

**Response:**
```json
{
  "answer": "To reset your password, go to Settings > Account > Reset Password...",
  "sources": [
    {"question": "How do I reset my password?", "category": "account"}
  ]
}
```

### `GET /`

Serves the chat UI.

## Updating the FAQ Dataset

Edit `app/data/faq.json` and restart the server. Each entry should follow this format:

```json
{
  "id": "unique-id",
  "question": "The question text",
  "answer": "The answer text",
  "category": "account|billing|shipping|returns|product|technical"
}
```

The ChromaDB collection is rebuilt from scratch on every startup, so changes take effect immediately after a restart.
