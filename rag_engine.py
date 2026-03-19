import os
import time
from dotenv import load_dotenv

os.environ["GOOGLE_API_CORE_SUPPRESS_PYTHON_VERSION_WARNING"] = "1"
load_dotenv()

HF_TOKEN       = os.getenv("HUGGINGFACE_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ENDEE_TOKEN    = os.getenv("ENDEE_API_KEY")
ENDEE_BASE_URL = os.getenv("ENDEE_BASE_URL")
COLLECTION     = os.getenv("ENDEE_COLLECTION", "SmartDOC_PROD_Vault")

MODEL_NAME = "gemini-1.5-flash"
EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIM = 3072

import google.generativeai as genai

_genai_configured = False
def _get_genai():
    global _genai_configured
    if not _genai_configured:
        genai.configure(api_key=GEMINI_API_KEY)
        _genai_configured = True
    return genai

_client = None
def _get_client():
    global _client
    if _client is None:
        from endee import Endee
        from endee.schema import VectorItem
        if not hasattr(VectorItem, "get"):
            VectorItem.get = lambda self, key, default=None: getattr(self, key, default)
        _client = Endee(ENDEE_TOKEN)
        _client.set_base_url(ENDEE_BASE_URL)
    return _client

def get_chat_model():
    genai = _get_genai()
    return genai.GenerativeModel(MODEL_NAME)

def get_embedding(text: str):
    """Gets a single embedding using the native google-generativeai SDK."""
    genai = _get_genai()
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document"
    )
    return result['embedding']

def get_embeddings_batch(texts: list[str]):
    """Gets multiple embeddings in a single batch request to stay under quota."""
    genai = _get_genai()
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=texts,
        task_type="retrieval_document"
    )
    return result['embedding']

def get_query_embedding(text: str):
    """Gets a query embedding using the native google-generativeai SDK."""
    genai = _get_genai()
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_query"
    )
    return result['embedding']


def chunk_text(text: str, chunk_size=1000, overlap=200):
    """Simple chunking function since we removed langchain."""
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks


def _ensure_index():
    """Ensure the Endee index exists with the correct dimension (3072).
    If an old index with wrong dimension exists, delete and recreate it."""
    from endee.exceptions import ConflictException
    from endee import Precision

    client = _get_client()
    try:
        client.create_index(
            name=COLLECTION,
            dimension=EMBEDDING_DIM,
            space_type="cosine",
            precision=Precision.INT8
        )
        print(f"Created new Endee index '{COLLECTION}' with dim={EMBEDDING_DIM}")
    except ConflictException:
        # Index already exists — that's fine
        pass
    except Exception as e:
        # If the error mentions a dimension mismatch or hybrid conflict, delete and recreate
        err_msg = str(e)
        if "Expected shape" in err_msg or "384" in err_msg or "768" in err_msg or "Hybrid index" in err_msg:
            print(f"Index dimension/type mismatch detected. Recreating index...")
            try:
                client.delete_index(name=COLLECTION)
            except Exception:
                pass
            client.create_index(
                name=COLLECTION,
                dimension=EMBEDDING_DIM,
                space_type="cosine",
                precision=Precision.INT8
            )
            print(f"Recreated index '{COLLECTION}' with dim={EMBEDDING_DIM}")
        else:
            raise


def process_pdf(pdf_path: str):
    """Loads a PDF, splits into chunks, and upserts dense vectors to Endee."""
    print(f"Loading '{pdf_path}'...")
    from pypdf import PdfReader
    
    reader = PdfReader(pdf_path)
    chunks_with_metadata = []
    
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            page_chunks = chunk_text(text, chunk_size=1000, overlap=200)
            for chunk in page_chunks:
                if chunk.strip():  # skip empty chunks
                    chunks_with_metadata.append({
                        "text": chunk,
                        "page": page_num + 1
                    })
                
    print(f"Created {len(chunks_with_metadata)} chunks")

    if not chunks_with_metadata:
        print("No text extracted from PDF.")
        return 0

    # Ensure index exists with correct dimensions
    _ensure_index()
    client = _get_client()
    index = client.get_index(name=COLLECTION)

    vectors = []
    
    # Process in batches of 50 to stay safely under Gemini and Endee limits
    batch_size = 50
    for i in range(0, len(chunks_with_metadata), batch_size):
        batch = chunks_with_metadata[i : i + batch_size]
        batch_texts = [c["text"] for c in batch]
        
        print(f"Requesting embeddings for batch {i//batch_size + 1}...")
        
        # Retry logic for the whole batch
        batch_embeddings = None
        for attempt in range(5):
            try:
                batch_embeddings = get_embeddings_batch(batch_texts)
                break
            except Exception as e:
                err_msg = str(e)
                if ("429" in err_msg or "quota" in err_msg.lower()) and attempt < 4:
                    wait_time = (attempt + 1) * 20
                    print(f"Quota exceeded. Sleeping {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

        # Map embeddings back to vector objects
        for j, embedding in enumerate(batch_embeddings):
            chunk_idx = i + j
            chunk_data = chunks_with_metadata[chunk_idx]
            vectors.append({
                "id": f"{os.path.basename(pdf_path)}_{chunk_idx}",
                "vector": embedding,
                "meta": {
                    "text": chunk_data["text"],
                    "page": str(chunk_data["page"]),
                    "file": os.path.basename(pdf_path)
                },
                "filter": {
                    "file": os.path.basename(pdf_path)
                }
            })
            
        # Mandatory brief sleep to stay well under the 15 RPM limit
        time.sleep(2)

    print(f"Upserting {len(vectors)} vectors (dim={len(vectors[0]['vector'])})")
    try:
        index.upsert(vectors)
    except Exception as e:
        err_msg = str(e)
        print(f"Upsert failed: {err_msg}")
        # Dimension/type mismatch — delete old index, recreate, retry
        if "Expected shape" in err_msg or "Hybrid index" in err_msg:
            print("Dimension/type mismatch during upsert. Recreating index...")
            try:
                client.delete_index(name=COLLECTION)
            except Exception:
                pass
            from endee import Precision
            client.create_index(
                name=COLLECTION,
                dimension=EMBEDDING_DIM,
                space_type="cosine",
                precision=Precision.INT8
            )
            index = client.get_index(name=COLLECTION)
            index.upsert(vectors)
        else:
            raise
             
    print(f"{len(chunks_with_metadata)} chunks stored in Endee Cloud!")
    return len(chunks_with_metadata)


def query_pdf(user_query: str, filename: str):
    """Queries the Endee DB and passes context to Gemini for an answer."""
    client = _get_client()
    index = client.get_index(name=COLLECTION)

    # Get query embedding with retry
    for attempt in range(3):
        try:
            query_vector = get_query_embedding(user_query)
            break
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                time.sleep(5)
            else:
                raise

    all_results = index.query(vector=query_vector, top_k=10)

    # FIX: VectorItem doesn't support __getitem__ (bracket access),
    # only .get() is monkey-patched. Use this helper everywhere.
    def get_meta(r):
        meta = r.get('meta', None)
        if meta is None:
            meta = getattr(r, 'meta', {})
        return meta if isinstance(meta, dict) else {}

    results = [r for r in all_results if get_meta(r).get('file', '') == filename][:3]

    context_parts = []
    for r in results:
        meta = get_meta(r)
        text = meta.get('text', '')
        page = meta.get('page', 'N/A')
        context_parts.append(f"Page Content: {text}\nPage Number: {page}")

    context = "\n\n".join(context_parts)

    if not context.strip():
        return "No relevant content found in the document for your query. Please try rephrasing."

    prompt = f"""
You are a helpful and detailed AI assistant answering questions about an uploaded PDF document.
Use the context below to answer accurately. Always state what page numbers your answer is referencing if applicable.

Context from PDF:
{context}

Question:
{user_query}
"""
    chat_model = get_chat_model()
    # Retry on 429 rate-limit
    for attempt in range(3):
        try:
            response = chat_model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                wait = (attempt + 1) * 15
                print(f"[Rate-limit] Retrying in {wait}s…")
                time.sleep(wait)
            else:
                raise