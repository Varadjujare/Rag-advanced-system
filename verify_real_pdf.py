import requests

def test_real_pdf():
    # Download a valid, tiny PDF from the internet
    url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    pdf_content = requests.get(url).content
    
    BASE_URL = "http://127.0.0.1:5000/api"
    files = {'document': ('dummy.pdf', pdf_content, 'application/pdf')}
    res = requests.post(f"{BASE_URL}/upload", files=files)
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.text}")
    
    if res.status_code == 200:
        filename = res.json().get("filename")
        data = {"query": "What is this document about?", "filename": filename}
        res_chat = requests.post(f"{BASE_URL}/chat", json=data)
        print(f"Chat Status: {res_chat.status_code}")
        print(f"Chat: {res_chat.text}")

if __name__ == "__main__":
    test_real_pdf()
