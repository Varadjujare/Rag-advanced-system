
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from endee import Endee, Precision

# ── Load environment variables ───────────────────────────────────────────────
load_dotenv()

HF_TOKEN       = os.getenv("HUGGINGFACE_API_TOKEN")
ENDEE_TOKEN    = os.getenv("ENDEE_API_KEY")        # from dapp.endee.io project
ENDEE_BASE_URL = os.getenv("ENDEE_BASE_URL")        # from dapp.endee.io project
COLLECTION     = os.getenv("ENDEE_COLLECTION", "RAG_system")

# ── 1. Load PDF ──────────────────────────────────────────────────────────────
pdf_path = Path(__file__).parent / "PDF-Guide-Node-Andrew-Mead-v3.pdf"
loader = PyPDFLoader(str(pdf_path))
docs = loader.load()

# ── 2. Split into chunks ─────────────────────────────────────────────────────
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)
chunks = text_splitter.split_documents(docs)
print(f" Created {len(chunks)} chunks")

# ── 3. HuggingFace Embeddings (cloud API) ───────────────────────────────────
embeddings_model = HuggingFaceInferenceAPIEmbeddings(
    api_key=HF_TOKEN,
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# ── 4. Connect to Endee Cloud ────────────────────────────────────────────────
client = Endee(ENDEE_TOKEN)
client.set_base_url(ENDEE_BASE_URL)   # points to your dapp.endee.io project

# Create index (384 = all-MiniLM-L6-v2 output dimension)
client.create_index(
    name=COLLECTION,
    dimension=384,
    space_type="cosine",
    precision=Precision.INT8
)
print(f" Index '{COLLECTION}' created in Endee Cloud.")

# Get index reference
index = client.get_index(name=COLLECTION)

# ── 5. Embed + upsert all chunks ─────────────────────────────────────────────
vectors = []
for i, chunk in enumerate(chunks):
    embedding = embeddings_model.embed_query(chunk.page_content)
    vectors.append({
        "id": str(i),
        "vector": embedding,
        "meta": {
            "text": chunk.page_content,
            "page": chunk.metadata.get("page_label", str(chunk.metadata.get("page", "N/A")))
        }
    })

index.upsert(vectors)

print(f" Successfully stored {len(chunks)} chunks in Endee Cloud!")
print(" Indexing done. Run retrieval.py to chat with Gemini.")
