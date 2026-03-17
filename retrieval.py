
import os
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from endee import Endee
import google.generativeai as genai

# ── Load environment variables ───────────────────────────────────────────────
load_dotenv()

HF_TOKEN       = os.getenv("HUGGINGFACE_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ENDEE_TOKEN    = os.getenv("ENDEE_API_KEY")
ENDEE_BASE_URL = os.getenv("ENDEE_BASE_URL")
COLLECTION     = os.getenv("ENDEE_COLLECTION", "RAG_system")

# ── 1. Configure Gemini ──────────────────────────────────────────────────────
genai.configure(api_key=GEMINI_API_KEY)

# ── 2. HuggingFace Embeddings ────────────────────────────────────────────────
embeddings_model = HuggingFaceInferenceAPIEmbeddings(
    api_key=HF_TOKEN,
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# ── 3. Connect to Endee Cloud ────────────────────────────────────────────────
client = Endee(ENDEE_TOKEN)
client.set_base_url(ENDEE_BASE_URL)
index = client.get_index(name=COLLECTION)

# ── 4. Get user question ─────────────────────────────────────────────────────
user_query = input("Ask me anything related to NODE.JS: ")

# ── 5. Embed query & search ──────────────────────────────────────────────────
query_vector = embeddings_model.embed_query(user_query)
results = index.query(vector=query_vector, top_k=3)

# ── 6. Build context ─────────────────────────────────────────────────────────
context = "\n\n".join(
    f"Page Content: {r['meta']['text']}\nPage Number: {r['meta'].get('page', 'N/A')}"
    for r in results
)

# ── 7. Ask Gemini ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""
You are a helpful AI Assistant who answers user queries based on the available
context retrieved from a PDF file along with page_contents and page number.

You should only answer the user based on the following context and navigate the
user to open the right page number to know more.

Context:
{context}

Question:
{user_query}
"""

model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content(SYSTEM_PROMPT)

print("\n RAG Response:\n", response.text)
