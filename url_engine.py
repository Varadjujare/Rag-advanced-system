import os
import re
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def get_chat_model():
    """Returns a direct Gemini model instance."""
    return genai.GenerativeModel("gemini-1.5-flash")


def scrape_url(url: str) -> dict:
    """Fetches a public URL, strips HTML, and returns clean text + metadata."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise ValueError("The request timed out. The website may be unavailable or too slow.")
    except requests.exceptions.HTTPError as e:
        raise ValueError(f"HTTP error {e.response.status_code}: Could not fetch the page.")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Connection error: {str(e)}")

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove noise tags
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "noscript", "iframe", "svg"]):
        tag.decompose()

    # Extract title
    title = soup.title.string.strip() if soup.title and soup.title.string else url

    # Extract visible text
    raw_text = soup.get_text(separator="\n", strip=True)

    # Collapse excessive blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", raw_text).strip()

    # Limit to ~12,000 words to avoid Gemini context overflow
    words = cleaned.split()
    if len(words) > 12000:
        cleaned = " ".join(words[:12000]) + "\n\n[Content truncated at 12,000 words]"

    word_count = len(words)

    return {
        "title": title,
        "text": cleaned,
        "word_count": word_count,
        "url": url
    }


def query_url(user_query: str, page_text: str, page_title: str, page_url: str) -> str:
    """Passes scraped page content + query to Gemini for an answer."""
    prompt = f"""You are a precise AI assistant helping a user understand the content of a webpage.
The user has provided you with the full text of the page. Answer their question strictly based on this content.
If the answer is not found in the text, say so clearly.

Page Title : {page_title}
Page URL   : {page_url}

--- PAGE CONTENT START ---
{page_text}
--- PAGE CONTENT END ---

User Question: {user_query}

Provide a clear, well-formatted answer using markdown where helpful (bullet points, bold, etc.)."""

    model = get_chat_model()
    response = model.generate_content(prompt)
    return response.text
