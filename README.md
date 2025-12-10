<div align="center">

# 🔬 Research Assistant

**AI-powered research paper analysis with RAG-based Q&A**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61dafb.svg)](https://reactjs.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Upload research papers, get AI-generated structured summaries, and chat with your documents using semantic search powered by Qdrant and sentence-transformers.

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [API](#-api-endpoints) • [Development](#-development)

</div>

---

## ✨ Features

- 📄 **PDF Upload & Parsing** – Extract text from research papers with OCR fallback
- 🤖 **AI Summarization** – Generate structured summaries with key findings
- 💬 **RAG-based Chat** – Ask questions and get contextual answers from your papers
- 🔍 **Semantic Search** – Qdrant vector store with sentence-transformers embeddings
- ⚡ **Fast Startup** – Models preloaded on container boot, HF cache persisted
- 🐳 **Docker Ready** – Full stack deployment with Docker Compose

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Frontend  │ ───> │   Backend    │ ───> │   Qdrant    │
│  (React +   │ HTTP │  (FastAPI)   │      │ Vector DB   │
│   Vite)     │ <─── │              │ <─── │             │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │ Hugging Face │
                     │  Embeddings  │
                     └──────────────┘
```

**Tech Stack:**
- **Backend:** FastAPI, Python 3.12, SentenceTransformers, PyMuPDF, PDFPlumber
- **Vector Store:** Qdrant
- **Frontend:** React 18, TypeScript, Vite, TailwindCSS
- **AI:** OpenAI GPT (summarization), sentence-transformers/all-MiniLM-L6-v2 (embeddings)

## 🚀 Quick Start

### Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/hasithdd/research-assistant.git
cd research-assistant

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Launch all services
docker compose up -d --build

# Access the application
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
# API Docs: http://localhost:8000/docs
```

The backend container mounts `~/.cache/huggingface` to persist downloaded models across restarts.

### Health Check

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

## ⚙️ Configuration

Create a `.env` file in the project root:

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional
HF_TOKEN=hf_...                                          # Speeds up model downloads
QDRANT_URL=http://qdrant:6333                           # Vector store endpoint
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/upload/pdf` | Upload PDF, returns `paper_id` and summary |
| `POST` | `/chat/` | Chat with a paper (requires `paper_id` and `query`) |
| `GET` | `/summary/{paper_id}` | Retrieve cached summary |

**Interactive API Documentation:** http://localhost:8000/docs

### Example: Upload & Chat

```bash
# Upload a paper
curl -X POST http://localhost:8000/upload/pdf \
  -F "file=@paper.pdf"
# Response: {"paper_id": "abc-123", "summary": {...}}

# Chat with the paper
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"paper_id": "abc-123", "query": "What is the main contribution?"}'
```

## 💻 Development

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose (for containerized setup)
- System packages: `tesseract-ocr`, `poppler-utils` (if running backend locally)

### Local Backend Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Start Qdrant (if not using Docker)
docker run -d -p 6333:6333 qdrant/qdrant:latest

# Run backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Local Frontend Setup

```bash
cd frontend
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run dev
# Dev server: http://localhost:5173
```

### Running Tests

```bash
# Backend tests
pytest

# Frontend tests (if configured)
cd frontend && npm test
```

### Code Quality

```bash
# Linting & formatting (backend)
ruff check backend/ --fix
ruff format backend/

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## 🐛 Troubleshooting

### NumPy/PyTorch compatibility error
```
A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x
```
**Solution:** `numpy<2` is pinned in `requirements.txt`. Rebuild Docker images:
```bash
docker compose build --no-cache backend
```

### Slow first request
The embedding model downloads on startup. With Docker, the HF cache volume (`~/.cache/huggingface`) prevents re-downloads on container restarts.

### Port conflicts
If ports 8000, 5173, or 6333 are in use:
```bash
# Edit docker-compose.yml to change port mappings
ports:
  - "8001:8000"  # Map to different host port
```

## 📦 Project Structure

```
research-assistant/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routes
│   │   ├── services/      # Business logic (RAG, PDF parsing, vectorstore)
│   │   ├── models/        # Pydantic schemas
│   │   └── core/          # Config, settings
│   ├── tests/             # Pytest test suite
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page layouts
│   │   └── api/           # API client
│   └── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Qdrant](https://qdrant.tech/) - Vector similarity search engine
- [Sentence Transformers](https://www.sbert.net/) - State-of-the-art embeddings
- [OpenAI](https://openai.com/) - GPT-based summarization

---

<div align="center">
Made with ❤️ by <a href="https://github.com/hasithdd">hasithdd</a>
</div>
