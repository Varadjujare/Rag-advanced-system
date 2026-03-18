# SmartDOC — Multi-Modal AI Assistant

SmartDOC is a powerful Retrieval-Augmented Generation (RAG) platform. It allows users to upload PDFs, analyze structured data (CSV/Excel), and scrape web pages to instantly extract insights, perform complex calculations, and summarize contents. It leverages **Google Gemini 2.5 Flash** for intelligence and **Endee Cloud Vector Database** for lightning-fast retrieval.

## ✨ Key Features
- **PDF Document RAG**: Semantic search, smart chunking, and vector indexing using Endee Cloud for deep document interrogation. Includes citations and page numbers.
- **Data Interrogator (CSV/xlsx)**: Analytical processing for CSV/Excel files. Automatically suggests smart analytical questions and leverages Gemini to perform complex data analysis on tabular data.
- **Web Scraping & Chat** *(New!)*: Instantly scrape any public URL, clean the HTML noise, and chat directly with the webpage content using an intelligent LLM context window.
- **Modern Architecture**: Flask backend with modular engines (`rag_engine`, `csv_engine`, `url_engine`) ensuring clean separation of concerns.

---

## 🏗️ Technical Architecture
- **Backend Framework**: Flask (Python 3.9+)
- **Large Language Model**: Google Gemini (`gemini-2.5-flash` via `langchain-google-genai`)
- **Vector Database**: Endee Cloud (`endee`)
- **Embeddings**: HuggingFace (`sentence-transformers/all-MiniLM-L6-v2`)
- **Web Scraping**: `requests`, `BeautifulSoup4`
- **Data Handling**: `pandas`
- **Frontend**: HTML5, Vanilla JS, Modern CSS (UI available via `templates/` and `static/`)

---

## 🚀 Quick Start

### 1. Install Dependencies
Ensure you have Python installed.
```bash
pip install -r requirement.txt
```

### 2. Configure Environment (`.env`)
Create a `.env` file in the root directory:
```ini
# --- HuggingFace (Local Embeddings, token optional for open models)
HUGGINGFACE_API_TOKEN=your_hf_token

# --- Google Gemini
GEMINI_API_KEY=your_gemini_key

# --- Endee Cloud (Vector Database)
ENDEE_API_KEY=project_id:secret:region
ENDEE_BASE_URL=https://dev.endee.io/api/v1
ENDEE_COLLECTION=SmartDOC_Storage
```

### 3. Launch the Application
Start the Flask web server:
```bash
python app.py
```
Access the dashboard at **[http://localhost:5000](http://localhost:5000)**.

*(Note: You can also execute `python main.py` for a standalone CLI-based PDF chat experience tailored for testing the Endee integration.)*

---

## 📁 Repository Structure
- `app.py`: Main Flask application handling routing and API endpoints.
- `rag_engine.py`: Logic for PDF ingestion, chunking, and RAG querying.
- `csv_engine.py`: Logic for parsing CSV/Excel data and generating insights.
- `url_engine.py`: Pipeline for scraping web content and chatting with it.
- `main.py`: A CLI script for indexing and retrieval testing outside the Flask environment.
- `templates/` / `static/`: Frontend visual layout and JavaScript logic.

---

## 🛠️ System Limits & Performance
- **Upload Size**: Supports files up to 50MB.
- **Scraping Limits**: Web text is automatically truncated at ~12,000 words to respect Gemini context limits.
- **Data Previews**: Tabular data queries are limited to the first 500 rows to ensure efficient LLM interactions without exceeding context caps.
- **Lazy Initialization**: AI models (Embeddings and Chat Models) inside engines are instantiated lazily on the first request to minimize server startup times.