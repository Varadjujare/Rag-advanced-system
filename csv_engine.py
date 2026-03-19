import os
import time
from dotenv import load_dotenv

# Heavy imports deferred to function scope to bypass Render's 30s boot timeout
# import pandas as pd
# import google.generativeai as genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# genai.configure(api_key=GEMINI_API_KEY) # This line will be moved into get_chat_model

# ── Model name (single source of truth) ──────────────────────────────────────
MODEL_NAME = "gemini-1.5-flash"

def get_chat_model():
    """Returns a direct Gemini model instance."""
    import google.generativeai as genai # Deferred import
    genai.configure(api_key=GEMINI_API_KEY) # Configure here
    return genai.GenerativeModel(MODEL_NAME)

def _generate_with_retry(model, prompt, max_retries=3):
    """Calls model.generate_content with automatic retry on 429 rate-limit."""
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response
        except Exception as e:
            err_str = str(e)
            # Retry only on 429 quota / rate-limit errors
            if "429" in err_str and attempt < max_retries - 1:
                wait = (attempt + 1) * 15          # 15s, 30s, 45s
                print(f"[Rate-limit] Retrying in {wait}s (attempt {attempt+1}/{max_retries})…")
                time.sleep(wait)
            else:
                raise

def process_csv(filepath: str) -> dict:
    """Loads a CSV or Excel file, returning basic info so the UI knows it's ready."""
    import pandas as pd # Deferred import
    print(f"Loading '{filepath}'...")
    
    try:
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)
            
        return {
            "rows": len(df),
            "columns": len(df.columns),
            "columns_list": list(df.columns)
        }
    except Exception as e:
        raise Exception(f"Failed to process structured file: {str(e)}")

def query_csv(user_query: str, filepath: str) -> str:
    """Reads the dataset and passes it directly to Gemini along with the user's query."""
    import pandas as pd # Deferred import
    try:
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)
            
        max_rows = 500
        truncated = False
        if len(df) > max_rows:
            df_subset = df.head(max_rows)
            truncated = True
        else:
            df_subset = df
            
        dataset_md = df_subset.to_markdown(index=False)
        
        truncation_note = f"\n[NOTE: The dataset is very large. Only the first {max_rows} rows are shown below for context.]" if truncated else ""

        prompt = f"""
You are an expert Data Analyst and Assistant.

I am providing you with a dataset formatted as a Markdown table.
Analyze the data carefully and answer the user's question accurately.
Provide your answer in a clean, professional tone using Markdown (bolding, lists, etc.) for readability.
{truncation_note}

DATASET:
{dataset_md}

USER QUESTION:
{user_query}
"""
        model = get_chat_model()
        response = _generate_with_retry(model, prompt)
        return response.text
        
    except Exception as e:
        raise Exception(f"Failed to query CSV: {str(e)}")

def get_csv_recommendations(filepath: str):
    """Generates analytical questions based on CSV columns and sample data."""
    import pandas as pd # Deferred import
    try:
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)
            
        cols = list(df.columns)
        sample = df.head(5).to_string()
        
        prompt = f"""
You are a Data Analyst. Here is a snapshot of a dataset:
Columns: {cols}
Sample Data:
{sample}

Based on this, suggest 3 smart analytical questions the user should ask (e.g., about trends, sums, or correlations).
Keep them concise and professional.
Format: Return ONLY the questions as a JSON list of strings.
"""
        import json
        model = get_chat_model()
        response = _generate_with_retry(model, prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except:
        return ["Show some basic statistics", "What are the top 5 rows?", "Give me a summary of results"]
