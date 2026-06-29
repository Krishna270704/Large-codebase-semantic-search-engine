# 🔍 CodeLens — Semantic Code Search Engine

A production-ready **semantic code search engine** with **RAG-powered Q&A** that indexes local codebases and answers natural-language queries with the most relevant code snippets.

Built with **FastAPI**, **React**, **ChromaDB**, **sentence-transformers**, and **OpenAI**.

---

## ✨ Features

- 🔎 **Semantic Search** — Find code using natural language, not keywords
- 🤖 **RAG Q&A** — Ask questions and get grounded answers with source citations
- 🌊 **Streaming Responses** — Real-time token-by-token answer generation
- 📁 **Repository Ingestion** — Index any local codebase with one API call
- 🎨 **Modern React UI** — Dark-themed, responsive frontend with syntax highlighting
- 🐳 **Docker Ready** — One-command deployment with Docker Compose
- 🔌 **Provider Agnostic** — Works with OpenAI, Azure, Ollama, OpenRouter

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                           │
│               (Vite + Tailwind CSS + Nginx)                     │
│                    Port 3000 / Vercel                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTP / SSE
┌──────────────────────────▼──────────────────────────────────────┐
│                      FastAPI Backend                             │
│                                                                  │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐   │
│  │ /search │  │ /ingest  │  │  /ask    │  │    /health     │   │
│  └────┬────┘  └────┬─────┘  └────┬─────┘  └────────────────┘   │
│       │            │             │                                │
│  ┌────▼────────────▼─────────────▼────────────────────────┐     │
│  │              Service Layer                              │     │
│  │  CodeEmbedder │ VectorStore │ IngestionService │ RAG   │     │
│  └──────┬────────────┬────────────────────────────┬───────┘     │
│         │            │                            │              │
│  ┌──────▼──────┐ ┌───▼────────┐           ┌──────▼──────┐      │
│  │ sentence-   │ │  ChromaDB  │           │  OpenAI API │      │
│  │ transformers│ │ (Persistent│           │  (or compat)│      │
│  └─────────────┘ └────────────┘           └─────────────┘      │
│                    Port 8000 / Render                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
semantic-search-engine/
├── app/                          # FastAPI backend
│   ├── main.py                   # App entry point & lifespan
│   ├── config.py                 # Settings (SSE_ env prefix)
│   ├── models.py                 # Pydantic schemas
│   ├── chunker.py                # Token-aware code chunking
│   ├── embedder.py               # sentence-transformers wrapper
│   ├── vectordb.py               # ChromaDB wrapper
│   ├── routers/
│   │   ├── ingest.py             # POST /api/v1/ingest
│   │   ├── search.py             # GET  /api/v1/search
│   │   └── ask.py                # POST /api/v1/ask (RAG)
│   └── services/
│       ├── ingestion.py          # Ingestion pipeline
│       └── rag.py                # RAG pipeline (retrieve → prompt → stream)
│
├── frontend/                     # React frontend
│   ├── src/
│   │   ├── components/           # SearchBar, ResultCard, etc.
│   │   ├── pages/Home.jsx        # Main page
│   │   └── services/api.js       # Axios API layer
│   ├── Dockerfile                # Multi-stage: Node build → Nginx
│   ├── nginx.conf                # SPA routing + gzip
│   └── vercel.json               # Vercel deployment config
│
├── Dockerfile                    # Backend: multi-stage Python slim
├── docker-compose.yml            # Full-stack orchestration
├── render.yaml                   # Render.com blueprint
├── .github/workflows/ci.yml     # CI/CD pipeline
├── .env.example                  # Environment template
├── .gitignore
├── .dockerignore
└── requirements.txt
```

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-username/semantic-search-engine.git
cd semantic-search-engine

# 2. Configure environment
cp .env.example .env
# Edit .env → set SSE_OPENAI_API_KEY=sk-your-key

# 3. Launch everything
docker-compose up --build
```

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### Option 2: Manual Setup

#### Backend

```bash
cd semantic-search-engine

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env → set SSE_OPENAI_API_KEY

# Start server
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## ⚙️ Configuration

All backend settings use the `SSE_` environment prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `SSE_OPENAI_API_KEY` | *(required for RAG)* | OpenAI or compatible API key |
| `SSE_OPENAI_BASE_URL` | `None` | Custom LLM endpoint (Ollama, Azure, etc.) |
| `SSE_LLM_MODEL` | `gpt-4o-mini` | LLM model identifier |
| `SSE_LLM_TEMPERATURE` | `0.1` | Sampling temperature |
| `SSE_LLM_MAX_TOKENS` | `1024` | Max response tokens |
| `SSE_RAG_TOP_K` | `5` | Context chunks per question |
| `SSE_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Embedding model |
| `SSE_CHROMA_PERSIST_DIR` | `./chroma_store` | ChromaDB storage path |
| `SSE_CORS_ORIGINS` | `["*"]` | Allowed CORS origins |

Frontend uses `VITE_API_URL` (set in `frontend/.env` or as Docker build arg).

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check + stats |
| `POST` | `/api/v1/ingest` | Index files from a directory |
| `GET` | `/api/v1/search?q=...&k=5` | Semantic code search |
| `POST` | `/api/v1/ask` | RAG Q&A (streaming or JSON) |

### Example: Search

```bash
curl "http://localhost:8000/api/v1/search?q=database+connection&k=3"
```

### Example: Ingest

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"directory": "./data", "reset": true}'
```

### Example: RAG Q&A (Streaming)

```bash
curl -N -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How does authentication work?", "stream": true}'
```

---

## 🌍 Deployment

### Backend → Render

1. Push repo to GitHub
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Build:** `pip install -r requirements.txt`
   - **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Starter (with disk for ChromaDB)
5. Add env vars: `SSE_OPENAI_API_KEY`, `SSE_CORS_ORIGINS`

Or use the included `render.yaml` blueprint for auto-configuration.

### Frontend → Vercel

1. Go to [vercel.com](https://vercel.com) → **Import Project**
2. Set root directory to `frontend`
3. Framework: **Vite**
4. Add env var: `VITE_API_URL=https://your-render-backend.onrender.com`
5. Deploy!

### CI/CD (GitHub Actions)

The pipeline at `.github/workflows/ci.yml` automatically:
1. ✅ Lints backend with Ruff
2. ✅ Validates FastAPI imports
3. ✅ Builds frontend production bundle
4. ✅ Builds Docker images (with Buildx cache)
5. 🚀 Deploys to Render + Vercel on merge to `main`

**Required GitHub Secrets:**
| Secret | Purpose |
|--------|---------|
| `RENDER_DEPLOY_HOOK` | Render deploy webhook URL |
| `VERCEL_TOKEN` | Vercel API token |
| `VERCEL_ORG_ID` | Vercel organization ID |
| `VERCEL_PROJECT_ID` | Vercel project ID |

---

## 🧱 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, Python 3.10+, Uvicorn |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) |
| **Vector DB** | ChromaDB (persistent, cosine similarity) |
| **LLM / RAG** | OpenAI API (or any compatible provider) |
| **Frontend** | React 18, Vite, Tailwind CSS |
| **Containers** | Docker, Docker Compose, Nginx |
| **CI/CD** | GitHub Actions |
| **Hosting** | Render (backend), Vercel (frontend) |

---

## 🧪 Testing

```bash
# Run the full stack
docker-compose up --build

# Verify health
curl http://localhost:8000/health

# Ingest sample data
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"directory": "./data", "reset": true}'

# Search
curl "http://localhost:8000/api/v1/search?q=authentication"

# RAG Q&A
curl -N -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How does authentication work?"}'

# Open frontend
# http://localhost:3000
```

---

## 📄 License

MIT
