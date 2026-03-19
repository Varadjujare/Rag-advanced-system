import os
import time
from dotenv import load_dotenv
import google.generativeai as genai
from endee import Endee, Precision

load_dotenv()

HF_TOKEN       = os.getenv("HUGGINGFACE_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ENDEE_TOKEN    = os.getenv("ENDEE_API_KEY")
ENDEE_BASE_URL = os.getenv("ENDEE_BASE_URL")
COLLECTION     = os.getenv("ENDEE_COLLECTION", "SmartDOC_PROD_Vault")

MODEL_NAME = "gemini-2.5-flash-lite"
EMBEDDING_MODEL = "models/gemini-embedding-001"

genai.configure(api_key=GEMINI_API_KEY)

# Monkey-patch VectorItem for Python 3.14 bug
from endee.schema import VectorItem
if not hasattr(VectorItem, "get"):
    VectorItem.get = lambda self, key, default=None: getattr(self, key, default)

client = Endee(ENDEE_TOKEN)
client.set_base_url(ENDEE_BASE_URL)

def get_chat_model():
    return genai.GenerativeModel(MODEL_NAME)

def get_embedding(text: str):
    """Gets a single embedding using the native google-generativeai SDK."""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document"
    )
    return result['embedding']

def get_query_embedding(text: str):
    """Gets a query embedding using the native google-generativeai SDK."""
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

def process_pdf(pdf_path: str):
    """Loads a PDF, splits into chunks, and upserts dense vectors to Endee."""
    print(f"Loading '{pdf_path}'...")
    from pypdf import PdfReader
    
    reader = PdfReader(pdf_path)
    chunks_with_metadata = []
    
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            page_chunks = chunk_text(text, chunk_size=1000, overlap=200)
            for chunk in page_chunks:
                chunks_with_metadata.append({
                    "text": chunk,
                    "page": page_num + 1
                })
                
    print(f"Created {len(chunks_with_metadata)} chunks")

    # Ensure index exists with correct dimensions
    from endee.exceptions import ConflictException
    try:
        index_info = client.get_index(name=COLLECTION)
        # Endee doesn't expose dimension directly on the object sometimes, 
        # so we can just rely on the API. But the safest way is to try creating,
        # and if it exists but is wrong during upsert, we handle it later.
        # However, we can proactively delete it if we know we changed models.
        # Let's check info:
        if hasattr(index_info, 'dimension') and index_info.dimension == 384:
             print("Old index format found. Deleting and recreating...")
             client.delete_index(name=COLLECTION)
             client.create_index(name=COLLECTION, dimension=3072, space_type="cosine", precision=Precision.INT8)
    except Exception:
        pass # Index probably doesn't exist yet

    try:
        client.create_index(name=COLLECTION, dimension=3072, space_type="cosine", precision=Precision.INT8)
    except ConflictException:
        pass # Already exists

    index = client.get_index(name=COLLECTION)

    vectors = []
    # Batch embeddings to avoid rate limits if possible, but genai library 
    # handles them sequentially per call easily. Let's do it sequentially with backoff 
    # if rate limit hits (since 2.5-flash-lite quota is very high).
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
            }
        })

    try:
        index.upsert(vectors)
    except Exception as e:
        if "Expected shape" in str(e) or "384" in str(e):
             print("Dimension mismatch detected during upsert. Recreating index...")
             client.delete_index(name=COLLECTION)
             client.create_index(name=COLLECTION, dimension=3072, space_type="cosine", precision=Precision.INT8)
             index = client.get_index(name=COLLECTION)
             index.upsert(vectors)
        else:
             raise
             
    print(f"{len(chunks_with_metadata)} chunks stored in Endee Cloud!")
    return len(chunks_with_metadata)

def query_pdf(user_query: str, filename: str):
    """Queries the Endee DB and passes context to Gemini for an answer."""
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

    results = index.query(vector=query_vector, top_k=3, filter={"file": filename})

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
