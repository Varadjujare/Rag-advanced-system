# RAG System — Project Guide

## Project Structure

```
RAG_part/
├── .env                               ← API keys (fill this in!)
├── .gitignore                         ← .env & venv excluded from git
├── requirement.txt                    ← Python dependencies
├── index.py                           ← Run ONCE: indexes PDF into ChromaDB
├── retrieval.py                       ← Run every time: chat with the PDF
├── PDF-Guide-Node-Andrew-Mead-v3.pdf  ← Source knowledge (Node.js book)
└── chroma_db/                         ← Auto-created by ChromaDB on first run
```

---

## .env Setup (fill in your actual keys)

```env
HUGGINGFACE_API_TOKEN=your_huggingface_token_here
GEMINI_API_KEY=your_gemini_api_key_here
CHROMA_PERSIST_DIR=./chroma_db
```

> **NEVER commit `.env` to git** — already in `.gitignore` ✅

### Where to get your keys

| Key | Link |
|---|---|
| `HUGGINGFACE_API_TOKEN` | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) → New token (read) |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) → Get API Key |

---

## Tech Stack

| Component | Technology |
|---|---|
| Embedding Model | HuggingFace `all-MiniLM-L6-v2` (cloud API, 384 dims) |
| Vector Database | **ChromaDB** (local, persists to `./chroma_db/`) |
| LLM / AI Answer | Google Gemini 2.5 Flash |
| PDF Loader | LangChain `PyPDFLoader` |
| Text Chunking | `RecursiveCharacterTextSplitter` (1000 chars, 200 overlap) |

---

## Setup & Run

### Step 1 — Install dependencies
```bash
pip install -r requirement.txt
```

### Step 2 — Fill in `.env`
Add your HuggingFace token and Gemini API key.

### Step 3 — Index the PDF (run ONCE)
```bash
python index.py
```
This creates a `chroma_db/` folder with all vectors saved to disk.

### Step 4 — Start chatting (run every time)
```bash
python retrieval.py
```

---

## Architecture

```
PDF ──► index.py
           ├── Split into 1000-char chunks
           ├── HuggingFace API → 384-dim vectors
           └── Chroma.from_documents() → saved to ./chroma_db/

User Query ──► retrieval.py
                   ├── HuggingFace API → embed query
                   ├── Chroma.similarity_search() → top 3 chunks
                   └── Gemini 2.5 Flash → answer + page references
```

---

## Why ChromaDB?

- ✅ No Docker needed
- ✅ No cloud account
- ✅ No API key
- ✅ Works on Windows
- ✅ Data persists to disk automatically
- ✅ Native LangChain support
