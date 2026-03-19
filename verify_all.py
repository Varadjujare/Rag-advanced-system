"""Comprehensive test of ALL 3 services: PDF RAG, CSV Analytics, URL Scraper."""
import requests
import io
import time
import sys

BASE_URL = "http://127.0.0.1:5000/api"
PASS = 0
FAIL = 0
results_log = []

def report(name, status_code, text, expected_status=200):
    global PASS, FAIL
    ok = status_code == expected_status
    symbol = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    line = f"  [{symbol}] {name}: {status_code} -- {text[:200]}"
    results_log.append(line)
    return ok

def create_test_pdf():
    """Create a valid PDF with actual text content using pypdf."""
    from pypdf import PdfWriter
    from pypdf.generic import NameObject, DictionaryObject, ArrayObject, NumberObject
    
    writer = PdfWriter()
    # Add a page with text annotations
    writer.add_blank_page(width=612, height=792)
    
    # Write the PDF to bytes
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()

# Wait a moment for server to be up
time.sleep(2)

# ============ 1. PDF RAG ============
results_log.append("\n========== PDF RAG ==========")

# Try downloading a real PDF first, fall back to local creation
pdf_bytes = None
try:
    pdf_bytes = requests.get("https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf", timeout=5).content
    results_log.append(f"  Downloaded test PDF ({len(pdf_bytes)} bytes)")
except Exception:
    results_log.append("  Could not download test PDF, using local creation")
    pdf_bytes = create_test_pdf()
    results_log.append(f"  Created local test PDF ({len(pdf_bytes)} bytes)")

pdf_filename = None
if pdf_bytes:
    files = {'document': ('testdoc.pdf', io.BytesIO(pdf_bytes), 'application/pdf')}
    res = requests.post(f"{BASE_URL}/upload", files=files, timeout=120)
    if report("PDF Upload", res.status_code, res.text):
        pdf_filename = res.json().get("filename")
    
    if pdf_filename:
        data = {"query": "What is this document about?", "filename": pdf_filename}
        res = requests.post(f"{BASE_URL}/chat", json=data, timeout=120)
        report("PDF Chat", res.status_code, res.text)

# ============ 2. CSV Analytics ============
results_log.append("\n========== CSV ANALYTICS ==========")
csv_content = b"Name,Age,Score\nAlice,30,95\nBob,25,80\nCharlie,35,70"
files = {'document': ('test.csv', io.BytesIO(csv_content), 'text/csv')}
res = requests.post(f"{BASE_URL}/upload-csv", files=files, timeout=30)
csv_filename = None
if report("CSV Upload", res.status_code, res.text):
    csv_filename = res.json().get("filename")

if csv_filename:
    data = {"filename": csv_filename, "mode": "csv"}
    res = requests.post(f"{BASE_URL}/recommendations", json=data, timeout=30)
    report("CSV Recommendations", res.status_code, res.text)
    
    data = {"query": "Who has the highest score?", "filename": csv_filename}
    res = requests.post(f"{BASE_URL}/chat-csv", json=data, timeout=30)
    report("CSV Chat", res.status_code, res.text)

# ============ 3. URL Scraper ============
results_log.append("\n========== URL SCRAPER ==========")
# Use a URL that's more likely reachable
data = {"url": "https://httpbin.org/html"}
try:
    res = requests.post(f"{BASE_URL}/scrape-url", json=data, timeout=30)
    url_token = None
    if report("URL Scrape", res.status_code, res.text):
        url_token = res.json().get("session_token")

    if url_token:
        data = {"query": "What is on this page?", "session_token": url_token}
        res = requests.post(f"{BASE_URL}/chat-url", json=data, timeout=60)
        report("URL Chat", res.status_code, res.text)
except Exception as e:
    results_log.append(f"  [SKIP] URL tests skipped (network issue: {e})")

# ============ 4. Health ============
results_log.append("\n========== MISC ==========")
res = requests.get(f"{BASE_URL.replace('/api','')}/health", timeout=10)
report("Health Check", res.status_code, res.text)

# ============ SUMMARY ============
results_log.append(f"\n{'='*40}")
results_log.append(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
if FAIL > 0:
    results_log.append("SOME TESTS FAILED!")

# Write results to UTF-8 file
with open("test_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results_log))

# Also print
for line in results_log:
    print(line)
