import traceback
import rag_engine
import os

pdf_path = "test.pdf"
with open(pdf_path, "wb") as f:
    f.write(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n")

try:
    rag_engine.process_pdf(pdf_path)
except Exception as e:
    print(f"Caught exception: {e}")
    traceback.print_exc()

# Let's see if os.remove fails while reader is active!
from pypdf import PdfReader
reader = PdfReader(pdf_path)
try:
    os.remove(pdf_path)
    print("os.remove succeeded despite open file (Linux behavior).")
except Exception as e:
    print(f"os.remove failed! {e}")
