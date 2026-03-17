
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from endee import Endee, Precision
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings

# ── Load environment variables ───────────────────────────────────────────────
load_dotenv()

HF_TOKEN       = os.getenv("HUGGINGFACE_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ENDEE_TOKEN    = os.getenv("ENDEE_API_KEY")
ENDEE_BASE_URL = os.getenv("ENDEE_BASE_URL")
COLLECTION     = os.getenv("ENDEE_COLLECTION", "RAG_system")

# ── Setup clients ────────────────────────────────────────────────────────────
from endee.schema import VectorItem
# Monkey-patch VectorItem to fix a Python 3.14 Pydantic V1 bug inside Endee's upsert
if not hasattr(VectorItem, "get"):
    VectorItem.get = lambda self, key, default=None: getattr(self, key, default)

# Use local embeddings instead of Inference API to avoid 403 errors
embeddings_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

client = Endee(ENDEE_TOKEN)
client.set_base_url(ENDEE_BASE_URL)


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 — INDEX (only runs if index doesn't exist yet)
# ─────────────────────────────────────────────────────────────────────────────
def index_pdf():
    print("\n Indexing PDF into Endee Cloud...")

    pdf_path = Path(__file__).parent / "PDF-Guide-Node-Andrew-Mead-v3.pdf"
    loader = PyPDFLoader(str(pdf_path))
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    print(f" Created {len(chunks)} chunks")

    from endee.exceptions import ConflictException
    try:
        client.create_index(name=COLLECTION, dimension=384, space_type="cosine", precision=Precision.INT8)
    except ConflictException:
        print(f" Index '{COLLECTION}' already exists, proceeding to retrieve it...")

    index = client.get_index(name=COLLECTION)

    vectors = []
    for i, chunk in enumerate(chunks):
        embedding = embeddings_model.embed_query(chunk.page_content)
        vectors.append({
            "id": str(i),
            "vector": embedding,
            "meta": {
                "text": chunk.page_content,
                "page": str(chunk.metadata.get("page", "N/A"))
            }
        })

    index.upsert(vectors)
    print(f" {len(chunks)} chunks stored in Endee Cloud!\n")


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2 — RETRIEVAL CHAT LOOP
# ─────────────────────────────────────────────────────────────────────────────
def chat():
    index = client.get_index(name=COLLECTION)
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0.3
    )

    print("\n" + "="*50)
    print("   NODE.JS RAG Assistant — ready!")
    print("   Type 'exit' to quit")
    print("="*50 + "\n")

    while True:
        user_query = input("Ask: ").strip()
        if user_query.lower() in ("exit", "quit", "q"):
            print("Goodbye!")
            break
        if not user_query:
            continue

        query_vector = embeddings_model.embed_query(user_query)
        results = index.query(vector=query_vector, top_k=3)

        context = "\n\n".join(
            f"Page Content: {r['meta'].get('text', '')}\nPage Number: {r['meta'].get('page', 'N/A')}"
            for r in results
        )

        prompt = f"""
You are a helpful AI Assistant who answers user queries based on the available
context retrieved from a PDF file along with page_contents and page number.
Only answer based on the context below and tell the user which page to read.

Context:
{context}

Question:
{user_query}
"""
        response = model.invoke(prompt)
        print(f"\n Answer:\n{response.content}\n")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN — checks if index exists, indexes if needed, then starts chat
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Check if index already exists
    existing = client.list_indexes()

    if COLLECTION not in existing:
        print(f" Index '{COLLECTION}' not found. Running indexing first...")
        index_pdf()
    else:
        print(f" Index '{COLLECTION}' already exists. Skipping indexing.")

    chat()
