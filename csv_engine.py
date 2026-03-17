import os
import pandas as pd
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Global cache for chat model
_chat_model = None

def get_chat_model():
    global _chat_model
    if _chat_model is None:
        print("Loading Gemini Chat Model for CSV Engine (first time)...")
        _chat_model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=GEMINI_API_KEY,
            temperature=0.3
        )
    return _chat_model

def process_csv(filepath: str) -> dict:
    """Loads a CSV or Excel file, returning basic info so the UI knows it's ready."""
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
    try:
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)
            
        # Convert the DataFrame to a Markdown table
        # If the dataset is huge, we might want to sample it or use df.head(100) 
        # But for standard files, Gemini flash handles huge contexts well.
        # Let's limit to top 500 rows to be safe with typical token limits.
        
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
        chat_model = get_chat_model()
        response = chat_model.invoke(prompt)
        return response.content
        
    except Exception as e:
        raise Exception(f"Failed to query CSV: {str(e)}")

def get_csv_recommendations(filepath: str):
    """Generates analytical questions based on CSV columns and sample data."""
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
        chat_model = get_chat_model()
        response = chat_model.invoke(prompt)
        text = response.content.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except:
        return ["Show some basic statistics", "What are the top 5 rows?", "Give me a summary of results"]
