import os
import time
from dotenv import load_dotenv

# Deferred imports to bypass Render's 30-sec port scan timeout
# import google.generativeai as genai
# from endee import Endee, Precision

load_dotenv()

HF_TOKEN       = os.getenv("HUGGINGFACE_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ENDEE_TOKEN    = os.getenv("ENDEE_API_KEY")
ENDEE_BASE_URL = os.getenv("ENDEE_BASE_URL")
COLLECTION     = os.getenv("ENDEE_COLLECTION", "SmartDOC_PROD_Vault")

MODEL_NAME = "gemini-2.5-flash-lite"
EMBEDDING_MODEL = "models/gemini-embedding-001"
# gemini-embedding-001 produces 3072-dimensional vectors
EMBEDDING_DIM = 3072

_client = None
def get_endee_client():
    """Lazy-loads and returns the Endee Client."""
    global _client
    if _client is None:
        from endee import Endee
        # Monkey-patch VectorItem for Python 3.14 bug
        from endee.schema import VectorItem
        if not hasattr(VectorItem, "get"):
            VectorItem.get = lambda self, key, default=None: getattr(self, key, default)
            
        _client = Endee(ENDEE_TOKEN)
        _client.set_base_url(ENDEE_BASE_URL)
    return _client

_genai_configured = False
def get_genai():
    """Lazy-loads and returns configured google generativeai module."""
    global _genai_configured
    import google.generativeai as genai
    if not _genai_configured:
        genai.configure(api_key=GEMINI_API_KEY)
        _genai_configured = True
    return genai

def get_chat_model():
    genai = get_genai()
    return genai.GenerativeModel(MODEL_NAME)

def get_embedding(text: str):
    """Gets a single embedding using the native google-generativeai SDK."""
    genai = get_genai()
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document"
    )
    return result['embedding']

def get_query_embedding(text: str):
    """Gets a query embedding using the native google-generativeai SDK."""
    genai = get_genai()
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
    client = get_endee_client()

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
            from endee import Precision
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
    client = get_endee_client()
    index = client.get_index(name=COLLECTION)

    vectors = []
    for i, chunk_data in enumerate(chunks_with_metadata):
        # Retry logic for embeddings
        for attempt in range(3):
            try:
                embedding = get_embedding(chunk_data["text"])
                break
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    time.sleep(5)
                else:
                    raise

        vectors.append({
            "id": f"{os.path.basename(pdf_path)}_{i}",
            "vector": embedding,
            "meta": {
                "text": chunk_data["text"],
                "page": str(chunk_data["page"]),
                "file": os.path.basename(pdf_path)
            },
            "sparse_indices": None,
            "sparse_values": None
        })

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
    client = get_endee_client()
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

    # Query without server-side filter (more compatible across Endee versions)
    # Then filter by filename in Python
    all_results = index.query(vector=query_vector, top_k=10)
    results = [r for r in all_results if r.get('meta', {}).get('file', '') == filename][:3]

    context = "\n\n".join(
        f"Page Content: {r['meta'].get('text', '')}\nPage Number: {r['meta'].get('page', 'N/A')}"
        for r in results
    )

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
