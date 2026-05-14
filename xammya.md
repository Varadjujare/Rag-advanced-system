# SmartDOC: Multi-Modal AI Assistant

## 1. Project Overview
SmartDOC is an advanced, multi-modal Artificial Intelligence assistant designed to interact with diverse data formats. The platform bridges the gap between static files/web pages and interactive querying by utilizing Large Language Models (LLMs) and advanced search methodologies. It supports querying PDF documents through a true Retrieval-Augmented Generation (RAG) pipeline, analyzing tabular data (CSV/Excel) via direct context windows, and interacting directly with scraped web content.

## 2. Technical Architecture & Tech Stack
The system follows a modular architectural pattern with a clear separation of concerns across multiple processing engines.

### 2.1. Core Technologies
*   **Backend Framework:** Flask (Python 3.9+)
*   **Large Language Model (LLM):** Google Gemini (`gemini-2.5-flash`)
*   **Embedding Model:** Google Gemini (`models/gemini-embedding-001` with 768 dimensionality via Matryoshka truncation)
*   **Vector Database:** Endee Cloud
*   **Data Processing:** `pandas` (for CSV/Excel), `pypdf` (for PDF text extraction)
*   **Web Scraping:** `requests`, `BeautifulSoup4`
*   **Frontend:** HTML5, Vanilla JavaScript, CSS (rendered via Flask templates)

## 3. Key Modules and Functionalities

### 3.1. True RAG PDF Engine (`rag_engine.py`)
This module implements a complete Retrieval-Augmented Generation pipeline for unstructured document querying.
*   **Ingestion & Chunking:** Extracts text from uploaded PDFs using `pypdf`. The text is split into semantic chunks of 1000 characters with a 200-character overlap to preserve context boundaries.
*   **Vectorization & Storage:** Embeddings are generated for each chunk using Gemini's embedding model and upserted into the Endee Cloud Vector Database. Operations are batched to respect API rate limits.
*   **Retrieval & Generation:** User queries are embedded and compared against the Endee Cloud index using Cosine Similarity. The top matching chunks are retrieved and injected into the Gemini context window to generate an accurate, citation-backed response.

### 3.2. Structured Data Interrogator (`csv_engine.py`)
Unlike the PDF engine, tabular data relies on direct context ingestion rather than semantic vector search, preserving the integrity of structured datasets for analytical queries.
*   **Parsing:** Reads `.csv` and `.xlsx` files into memory using Pandas DataFrames.
*   **Context Window Injection:** The DataFrame (capped at the first 500 rows to respect context limits) is converted into a Markdown table and fed directly into the Gemini prompt. 
*   **Smart Recommendations:** Analyzes the dataset schema (columns) and a subset of the data to dynamically recommend 3 analytical questions to the user.

### 3.3. Web Scraper & Chat Engine (`url_engine.py`)
Allows real-time conversational interaction with live websites.
*   **Extraction:** Fetches raw HTML via HTTP requests and uses BeautifulSoup to strip out noise (scripts, styles, navigation bars), isolating the main content.
*   **Direct Context Querying:** The cleaned text (truncated at approximately 12,000 words to fit safely within context windows) is sent directly to Gemini alongside user queries, acting as an instant Q&A mechanism for online articles and documentation.

## 4. System Resilience and Optimization
*   **Lazy Loading:** To minimize server startup time (crucial for cloud deployments), large ML dependencies and API clients are initialized lazily upon the first request.
*   **Rate-Limit Handling:** Built-in automatic retry logic (exponential backoff) prevents crashes when hitting Google Gemini or Endee Cloud API quotas.
*   **Dimension Mismatch Recovery:** The RAG engine actively monitors the Vector DB for dimension conflicts and can automatically recreate the index to maintain system stability.

## 5. Conclusion
The SmartDOC project effectively demonstrates the integration of state-of-the-art LLMs with modern database paradigms. By intelligently routing unstructured data through a Vector DB (RAG) and feeding structured data directly into large context windows, the platform provides a robust, scalable solution for enterprise-grade document and data interrogation.
