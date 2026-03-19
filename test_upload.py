import requests
import io
import time

url = 'http://localhost:5000/api/upload-pdf'

# Dummy PDF content (PyPDF will probably fail, but it will hit process_pdf)
dummy_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n"

# wait for server to be fully up
time.sleep(1)

files = {'document': ('dummy.pdf', io.BytesIO(dummy_pdf), 'application/pdf')}
response = requests.post(url, files=files)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
