import os
from dotenv import load_dotenv
from endee import Endee, Precision

load_dotenv()

HF_TOKEN       = os.getenv("HUGGINGFACE_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ENDEE_TOKEN    = os.getenv("ENDEE_API_KEY")
ENDEE_BASE_URL = os.getenv("ENDEE_BASE_URL")
COLLECTION     = os.getenv("ENDEE_COLLECTION", "RAG_system")

# Global cache for models
_embeddings_model = None
_chat_model = None

# Monkey-patch VectorItem for Python 3.14 bug
from endee.schema import VectorItem
if not hasattr(VectorItem, "get"):
    VectorItem.get = lambda self, key, default=None: getattr(self, key, default)

client = Endee(ENDEE_TOKEN)
client.set_base_url(ENDEE_BASE_URL)

def get_embeddings_model():
    global _embeddings_model
    if _embeddings_model is None:
        print("Loading HuggingFace Embeddings (first time)...")
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _embeddings_model

def get_chat_model():
    global _chat_model
    if _chat_model is None:
        print("Loading Gemini Chat Model (first time)...")
        from langchain_google_genai import ChatGoogleGenerativeAI
        _chat_model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=GEMINI_API_KEY,
            temperature=0.3
        )
    return _chat_model

def process_pdf(pdf_path: str):
    """Loads a PDF, splits into chunks, and upserts dense vectors to Endee."""
    print(f"Loading '{pdf_path}'...")
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    print(f"Created {len(chunks)} chunks")

    # Ensure index exists
    from endee.exceptions import ConflictException
    try:
        client.create_index(name=COLLECTION, dimension=384, space_type="cosine", precision=Precision.INT8)
    except ConflictException:
        pass # Already exists

    index = client.get_index(name=COLLECTION)

    embeddings_model = get_embeddings_model()
    vectors = []
    for i, chunk in enumerate(chunks):
        embedding = embeddings_model.embed_query(chunk.page_content)
        vectors.append({
            "id": f"{os.path.basename(pdf_path)}_{i}",
            "vector": embedding,
            "meta": {
                "text": chunk.page_content,
                "page": str(chunk.metadata.get("page", "N/A"))
            }
        })

    index.upsert(vectors)
    print(f"{len(chunks)} chunks stored in Endee Cloud!")
    return len(chunks)

def query_pdf(user_query: str):
    """Queries the Endee DB and passes context to Gemini for an answer."""
    index = client.get_index(name=COLLECTION)
    
    embeddings_model = get_embeddings_model()
    query_vector = embeddings_model.embed_query(user_query)
    results = index.query(vector=query_vector, top_k=3)

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
    response = chat_model.invoke(prompt)
    return response.content
